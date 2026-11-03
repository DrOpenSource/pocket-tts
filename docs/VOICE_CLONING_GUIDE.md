# Advanced Voice Cloning Optimization Guide

> **Maximizing Cloning Fidelity, Timbre Consistency, and Prosodic Naturalness at Zero Added Hardware or Compute Cost.**

---

## 1. Architectural Foundations of Voice Cloning in Pocket TTS

Pocket TTS utilizes a **streaming Flow Matching architecture** combined with Kyutai's **Mimi neural audio codec**:
- **Acoustic Tokenization**: Mimi compresses audio into continuous latent representations at **12.5 Hz** (each acoustic frame represents 80 ms of audio at 24 kHz).
- **Speaker Conditioning via AdaLN**: When reference audio is supplied, it is encoded by Mimi into latent representations that condition the **FlowLM Transformer** using Adaptive Layer Normalization (AdaLN) and KV-cache prepending.
- **Lagrangian Self Distillation (LSD)**: The FlowLM model predicts the target acoustic latents via flow-matching velocity fields in 1 to 4 distillation steps.

### Why Traditional Multi-Sample Concatenation Fails
In many speech models (e.g. autoregressive multi-speaker TTS), concatenating multiple audio clips from the same speaker improves cloning. **In Pocket TTS, concatenating clips degrades output quality.**
1. **Hard Prompt Truncation**: Pocket TTS enforces a compact prompt window (`truncate=True`, optimized between 5 and 8 seconds). Feeding longer clips means the latter portion is silently discarded.
2. **Phase & Acoustic Discontinuity**: Concatenating different clips introduces abrupt room tone shifts, phase resets, and spectral jumps. Mimi encodes these jumps into the latent conditioning prompt, causing the FlowLM model to exhibit fluctuating pitch, sudden timbre shifts, or trailing murmur.
3. **KV Cache Clutter**: Overly long reference audio fills the KV attention cache with redundant silent or repetitive frames, diluting attention on phonetically salient speech frames.

---

## 2. Zero-Cost Enhancement Matrix

| Optimization Vector | Action | Impact on Voice Similarity | Impact on Latency / Compute | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Input Audio Cleaning** | Offline Noise Reduction & Denoising | 🟢 Massive (Removes muffled timbre) | None (0% inference cost) | **$0** |
| **Silence Stripping** | Trim internal pauses $> 300\text{ ms}$ | 🟢 High (Eliminates breath hallucinations) | None (0% inference cost) | **$0** |
| **Duration Tuning** | Optimal 4.0 – 6.0 second reference | 🟢 High (Peak acoustic SNR) | Improves time-to-first-frame | **$0** |
| **Peak Normalization** | Normalize reference to $-0.5\text{ dBFS}$ | 🟢 Moderate (Prevents quantizer clipping) | None (0% inference cost) | **$0** |
| **LSD Decode Steps** | Set `--sampler-decode-steps 3` (or `4`) | 🟢 High (Crisper sibilants & harmonics) | $< 5\%$ CPU inference overhead | **$0** |
| **Teacher Forcing** | `--teacher-force-previous-chunk` | 🟢 High (Eliminates sentence resets) | None (0% inference cost) | **$0** |
| **Persona Caching** | Save & reuse `.safetensors` state | 🟢 Zero prompt encoding overhead | Eliminates Mimi encoder pass | **$0** |

---

## 3. Reference Audio Preprocessing Pipeline

To achieve studio-quality zero-shot cloning, raw voice recordings should be conditioned through an automated 4-step pipeline before inference:

### Step 1: Background Noise & Room Reverberation Suppression
Mimi captures everything in the reference recording—including computer fan noise, AC hum, and room echo. If the reference audio contains room reverb, the cloned voice will sound hollow and distant.
- **Recommended Free Tool**: `noisereduce` or `deepfilternet`:
  ```bash
  pip install noisereduce soundfile
  ```
- **Code Snippet**:
  ```python
  import soundfile as sf
  import noisereduce as nr

  audio, rate = sf.read("my_raw_voice.wav")
  # Perform stationary noise reduction
  reduced_noise = nr.reduce_noise(y=audio, sr=rate, prop_decrease=0.85)
  sf.write("my_voice_clean.wav", reduced_noise, rate)
  ```

### Step 2: Internal Pause & Silence Stripping
If the speaker pauses for breath or hesitates during the prompt clip, Mimi encodes those silent frames into the prompt state. FlowLM will then replicate those unnatural hesitations throughout synthesized speech.
- **Rule of Thumb**: Strip any silence longer than 300 ms. Keep speech natural, continuous, and clear.

### Step 3: Peak & Loudness Normalization
Overly quiet audio results in small latent vectors that lie outside the optimal dynamic range of Mimi’s quantizer; clipped audio creates harmonic distortion.
- Pocket TTS automatically applies peak normalization to $-0.5\text{ dBFS}$ ($0.95$ max amplitude) in `get_state_for_audio_prompt`:
  ```python
  peak = audio.abs().max()
  if peak > 1e-4:
      audio = audio / peak * 0.95
  ```

### Step 4: The 4–6 Second Sweet Spot
Select a continuous sentence spoken in the exact style and emotion desired:
- **Phonetically Rich**: Choose a sentence containing varied vowels, consonants, and natural vocal inflections (e.g. *"The quick brown fox jumps over the lazy dog and laughs out loud."* or *"नमस्ते, आज का मौसम बहुत ही सुहावना और शांत है।"*).
- **Avoid Flat Monotones**: If the speaker sounds bored in the reference audio, all generated speech will sound flat and robotic.

---

## 4. Inference Hyperparameter Tuning

Pocket TTS exposes several hyperparameters that elevate speech naturalness on standard CPUs without demanding extra RAM or GPU compute.

### 1. Lagrangian Self Distillation (LSD) Decode Steps
- **CLI Flag**: `--sampler-decode-steps 3` (Default: `1`)
- **Web UI / Server**: Pass `--sampler-decode-steps 3` when running `pocket-tts serve`.
- **Why It Works**: At 1 step, FlowLM performs an Euler prediction step to estimate acoustic codes from noise. While fast, 1-step decoding can produce slight metallic or robotic undertones on sibilants ('s', 'sh', 'ch'). Increasing decode steps to 3 or 4 computes a multi-step trajectory, refining high-frequency harmonics and smoothing voice timbre.
- **Performance Impact**: Because Mimi decoder execution dominates CPU time rather than FlowLM forward passes, increasing decode steps from 1 to 3 increases generation latency by less than 5%.

### 2. Teacher Forcing Between Chunks
- **CLI Flag**: `--teacher-force-previous-chunk`
- **Why It Works**: When synthesizing long paragraphs, Pocket TTS splits text into multiple sentence chunks. Without teacher forcing, each chunk starts with an empty acoustic context, occasionally resulting in subtle pitch resets or cadential dips between sentences. Enabling `--teacher-force-previous-chunk` conditions the beginning of chunk $N+1$ on the trailing latent state of chunk $N$.

### 3. Sampling Temperature & Noise Clamping
- **Recommended Temperature**: `0.3` (default). Increasing beyond `0.5` causes slurring and slurred consonants; decreasing below `0.2` can cause monotone pitch.
- **Noise Clamp**: Set to `1.5` or `None` to prevent numerical outliers in noise diffusion.

---

## 5. Reusable Voice Personas (`.safetensors`)

Encoding reference audio on every synthesis request wastes CPU cycles and adds up to 1–2 seconds of initial latency. Pocket TTS provides first-class support for exporting precomputed voice states as lightweight `.safetensors` files.

### Advantages:
1. **Zero Prompt Latency**: Speech synthesis begins immediately without waiting for Mimi encoder passes.
2. **Deterministic Output**: The voice state is locked in; no variance from audio file decoding or format differences across operating systems.
3. **Portability**: Each persona file is only a few megabytes and can be shared, stored, or committed.

### Usage:

#### 1. Via the Web Interface:
1. Open `http://localhost:8000`.
2. Upload your clean reference WAV or select an existing preset.
3. Click **"Save / Download Persona (.safetensors)"**.
4. To reuse it in the future, simply drag and drop the `.safetensors` file into the voice upload area or select it from your file manager.

#### 2. Via CLI:
```bash
# Export reference audio to persona state
pocket-tts export-voice path/to/my_voice.wav -o personas/speaker_alice.safetensors

# Generate speech directly using the persona
pocket-tts generate --voice personas/speaker_alice.safetensors --text "Hello world!"
```

#### 3. Via Python API:
```python
from pocket_tts import TTSModel
from pocket_tts.models.model_state import export_model_state

# Load model
model = TTSModel.load_model(language="multilingual")

# Encode once and export
voice_state = model.get_state_for_audio_prompt("reference_voice.wav", truncate=True)
export_model_state(voice_state, "speaker_alice.safetensors")

# Load and synthesize in zero time
fast_state = model.get_state_for_audio_prompt("speaker_alice.safetensors")
audio = model.generate_audio(
    model_state=fast_state,
    text="This voice was loaded instantly from precomputed latents."
)
```

---

## 6. Text Normalization & Script Optimization

The speech synthesizer relies on SentencePiece tokenization. If unnormalized digits, non-standard punctuation, or abbreviations are fed into the model, the tokenizer splits them into arbitrary character subwords, resulting in garbled or missed words.

### Normalization Best Practices:
1. **Always expand digits**:
   - English: `10` $\to$ `ten`, `1st` $\to$ `first`, `$50` $\to$ `50 dollars`
   - Hindi / Hinglish: `10` $\to$ `दस`, `3 बजे` $\to$ `तीन बजे`, `50%` $\to$ `पचास प्रतिशत`
2. **Punctuation & Cadence**:
   - Use commas (`,`) to force micro-pauses for natural breath intake.
   - Use Hindi danda (`।`, `॥`) or English period (`.`) to mark complete sentences.
   - Avoid consecutive special characters (e.g. `???`, `!!!`, `...--...`) which confuse sentence chunking.
3. **Interactive Normalization in Web UI**:
   - Use the built-in **"Preview Normalization"** button in the web interface to review and confirm all text substitutions before triggering audio generation.


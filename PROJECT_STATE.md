# Project State & Handoff (DrOpenSource Pocket TTS)

_Last Updated: November 5, 2026_

---

## 1. Quick Context for Incoming Agents

- **User**: DrOpenSource (`imkashyaps@gmail.com`)
- **Primary Upstream**: [`kyutai-labs/pocket-tts`](https://github.com/kyutai-labs/pocket-tts)
- **User Fork**: [`DrOpenSource/pocket-tts`](https://github.com/DrOpenSource/pocket-tts)
- **Active Pull Request**: **[PR #412](https://github.com/kyutai-labs/pocket-tts/pull/412)**
  - _Title_: `Add Indic punctuation (danda) sentence chunking and text normalization`
  - _Status_: **OPEN & 100% GREEN CI** (pytest on Python 3.14, rust, ty 3.10, ty 3.14 all passing).
  - _Action_: **DO NOT CLOSE.** Awaiting Kyutai maintainer review/merge.
- **Production Deployment**: **`https://clone.taqnik.in`** (Running on Hostinger VPS via Dokploy / Docker)

---

## 2. Git Branch Structure & Remote Configuration

```
origin   -> https://github.com/DrOpenSource/pocket-tts.git  (User's Fork)
upstream -> https://github.com/kyutai-labs/pocket-tts.git  (Official Kyutai Repository)
xdev     -> https://github.com/Xdev200/pocket-tts          (Old clone reference)
```

### Branches:

1. **`personal-dev`** _(DEFAULT LOCAL BRANCH & DOKPLOY TARGET)_:
   - Contains all production features, default multilingual engine (`DEFAULT_LANGUAGE = "multilingual"`), 7 Indian voice presets (Pooja, Priya, Neha, Kabir, Rohan, Aarav, Dev), `.safetensors` persona caching, text normalizer, and Docker configurations.
   - Pushed and backed up on GitHub at `DrOpenSource/pocket-tts:personal-dev`.
2. **`pr/indic-punctuation-and-normalizer`**:
   - Clean, minimal 4-file branch backing upstream PR #412.
3. **`main`**:
   - Clean mirror tracking `upstream/main`.

---

## 3. Features Implemented & Working

| Feature                               | Location                                   | Status                                                                                                        |
| :------------------------------------ | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| **Creator Studio (Material 3)**       | `pocket_tts/static/index.html` + `main.py` | Google Material 3 UI, in-browser 16-bit PCM mic recorder, preset auditioning, and IndexedDB local persistence |
| **Clean Header & Navigation**         | `pocket_tts/static/index.html`             | "Clone Voice Studio" branding, clean subtitle, removed clutter badges, 3-step progress bar                   |
| **Dynamic Preset Filtering**          | `pocket_tts/static/index.html`             | Filter chips for 🇮🇳 Indian Voices (7), 🇬🇧 English (9), and All Voices (16) with real-time search            |
| **Multilingual Model Default**        | `pocket_tts/default_parameters.py`         | Sets `multilingual` (`Thanushttk/pocket-tts-multilingual`) as default language                                |
| **Algorithmic G2P & Hinglish Engine** | `pocket_tts/models/text_chunking.py`       | 100+ curated loanwords + algorithmic G2P phonemizer fallback for unlisted English words + Romanized Hindi     |
| **Indic Danda Sentence Chunking**     | `pocket_tts/models/text_chunking.py`       | Recognizes `।` and `॥` as terminal punctuation                                                                |
| **Text Normalization Engine**         | `pocket_tts/models/text_chunking.py`       | Expands digits (`10` $\to$ `दस`), time (`3:30`), currency (`₹`, `$`), ordinals                                |
| **7 Indian Voice Presets**            | `pocket_tts/utils/utils.py`                | Pooja, Priya, Neha, Kabir, Rohan, Aarav, Dev with instant sample auditioning                                  |
| **Precomputed Voice Personas**        | `pocket_tts/main.py` + Web UI              | Instant `.safetensors` persona export & drag-and-drop                                                         |
| **Hindi Model Configs**               | `pocket_tts/config/hindi*.yaml`            | Native configs for Lite (6L) and Base (12L) models                                                            |
| **Voice Cloning Guide**               | `docs/VOICE_CLONING_GUIDE.md`              | Zero-cost audio preprocessing & hyperparameter tuning guide                                                   |

---

## 4. Immediate Next Tasks for Future Sessions

### Task 1: Monitor PR #412

- Check if Kyutai maintainers have requested any minor adjustments.
- If edits are requested, apply them on `pr/indic-punctuation-and-normalizer` and push.

### Task 2: Host on Server (`clone.taqnik.in`)

- **Dokploy Deployment Command**:
  ```bash
  sh -c "cd /app && ([ -d .git ] && (git fetch origin personal-dev && git reset --hard origin/personal-dev) || git clone -b personal-dev https://github.com/DrOpenSource/pocket-tts.git .) ; uv run pocket-tts serve --language multilingual --host 0.0.0.0 --port 8000"
  ```
- **Docker Compose**: `docker compose up -d --build` (runs `--language multilingual` on port 8000)
- **Cloudflare DNS**:
  - `A` record: `clone` -> `[VPS IP]` (Proxied / Orange Cloud)
  - Cloudflare Origin Rule: Rewrite destination port to `8000` for `clone.taqnik.in`
  - SSL/TLS: Flexible

### Task 3: PR 2 Preparation (Precomputed Persona `.safetensors` Export)

- Once PR #412 is merged, branch off upstream `main` into `pr/safetensors-persona-caching` to propose the `.safetensors` persona export feature upstream.

---

## 5. Verification Commands

```powershell
# Run all unit tests (44 tests)
uv run pytest -n 3 -v tests/test_split_sentences.py tests/test_python_api.py

# Static type check
uv run ty check pocket_tts tests

# Start local web app
uv run pocket-tts serve --language multilingual
```

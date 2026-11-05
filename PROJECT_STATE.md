# Project State & Handoff (DrOpenSource Pocket TTS)

_Last Updated: November 6, 2026_

---

## 1. Quick Context for Incoming Agents

- **User**: DrOpenSource (`imkashyaps@gmail.com`)
- **Original Project**: [`kyutai-labs/pocket-tts`](https://github.com/kyutai-labs/pocket-tts) (**no longer synced**, see Section 4)
- **User Fork**: [`DrOpenSource/pocket-tts`](https://github.com/DrOpenSource/pocket-tts) (public, maintained independently)
- **Open Pull Request**: **[PR #412](https://github.com/kyutai-labs/pocket-tts/pull/412)**
  - _Title_: `Add Indic punctuation (danda) sentence chunking and text normalization`
  - _Status_: **OPEN, MERGEABLE, ALL CI PASSING** at `64de5c9` (Nov 5, 2026). Reworked by the maintainer in `f6bf603`; no formal review yet.
  - _Action_: **DO NOT CLOSE.** Nothing further is needed unless the maintainer asks. `personal-dev` does not depend on it.
- **Production Deployment**: **`https://clone.taqnik.in`** (Running on Hostinger VPS via Dokploy / Docker)

---

## 2. Git Branch Structure & Remote Configuration

```
origin   -> https://github.com/DrOpenSource/pocket-tts.git  (User's Fork)
upstream -> https://github.com/kyutai-labs/pocket-tts.git  (Original project: PR #412 and reading only)
xdev     -> https://github.com/Xdev200/pocket-tts          (Old clone reference)
```

### Branches:

1. **`personal-dev`** _(DEFAULT LOCAL BRANCH & DOKPLOY TARGET)_:
   - Contains all production features, default multilingual engine (`DEFAULT_LANGUAGE = "multilingual"`), 7 Indian voice presets (Pooja, Priya, Neha, Kabir, Rohan, Aarav, Dev), `.safetensors` persona caching, text normalizer, and Docker configurations.
   - Pushed and backed up on GitHub at `DrOpenSource/pocket-tts:personal-dev`.
2. **`pr/indic-punctuation-and-normalizer`**:
   - Branch backing upstream PR #412. Contains a maintainer commit: update it with merges, never force-push.
3. **`main`**:
   - Old upstream mirror, no longer updated. Do not commit to it or branch from it.

---

## 3. Features Implemented & Working

| Feature                               | Location                                   | Status                                                                                                        |
| :------------------------------------ | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| **Creator Studio (Material 3)**       | `pocket_tts/static/index.html` + `main.py` | Google Material 3 UI, in-browser 16-bit PCM mic recorder, preset auditioning, and IndexedDB local persistence |
| **Clean Header & Navigation**         | `pocket_tts/static/index.html`             | "Clone Voice Studio" branding, clean subtitle, removed clutter badges, 3-step progress bar                   |
| **Dynamic Preset Filtering**          | `pocket_tts/static/index.html`             | Filter chips for 🇮🇳 Indian Voices (7), 🇬🇧 English (9), and All Voices (16) with real-time search            |
| **Multilingual Model Default**        | `pocket_tts/default_parameters.py`         | Sets `multilingual` (`Thanushttk/pocket-tts-multilingual`) as default language                                |
| **Algorithmic G2P & Hinglish Engine** | `pocket_tts/indic_normalizer.py`           | 100+ curated loanwords + algorithmic G2P phonemizer fallback for unlisted English words + Romanized Hindi     |
| **Indic Danda Sentence Chunking**     | `pocket_tts/models/text_chunking.py`       | Recognizes `।` and `॥` as terminal punctuation                                                                |
| **Text Normalization Engine**         | `pocket_tts/indic_normalizer.py`           | Expands digits (`10` $\to$ `दस`), time, currency, ordinals, Indian grouping (`₹1,25,000`), spoken decimals      |
| **7 Indian Voice Presets**            | `pocket_tts/utils/utils.py`                | Pooja, Priya, Neha, Kabir, Rohan, Aarav, Dev with instant sample auditioning                                  |
| **Precomputed Voice Personas**        | `pocket_tts/main.py` + Web UI              | Instant `.safetensors` persona export & drag-and-drop                                                         |
| **Hindi Model Configs**               | `pocket_tts/config/hindi*.yaml`            | Native configs for Lite (6L) and Base (12L) models                                                            |
| **Voice Cloning Guide**               | `docs/VOICE_CLONING_GUIDE.md`              | Zero-cost audio preprocessing & hyperparameter tuning guide                                                   |

---

## 4. Immediate Next Tasks for Future Sessions

### Independent Fork (decided November 6, 2026)

- This fork no longer syncs with `kyutai-labs/pocket-tts`, and it stays public. Conflicts only come from taking in upstream changes.
- Never merge, rebase or pull `upstream/main` into `personal-dev`, and do not use GitHub's "Sync fork" button on it.
- To take a single upstream fix, use `git cherry-pick -x <commit>` on a `fix/*` branch, only when the user asks.
- The fork takes on its own bug fixes and dependency updates, including PyTorch and security patches.
- `AGENTS.md` has a local, uncommitted workflow section. Do not commit it, and stage files by name.

### Code Differences to Keep

- Upstream normalizes numbers per model config. This fork uses `pocket_tts/indic_normalizer.py` for its per-request `auto` mode, `changes` list, abbreviations and transliterator.
- Keep the vocabulary scan in `get_punctuation_tokens`. Upstream's `tokenizer(".!...?")` probe misses the plain `.` on the multilingual tokenizer, which merges sentences into one chunk.

### Task 1: PR #412

- Update it only if the maintainer asks. Use a separate worktree and `git merge upstream/main`, and never force-push: the branch holds a maintainer commit.

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

### Task 3: Upstream Persona PR (dropped)

- Dropped because the fork is now independent. Upstream already has a CLI `export-voice` command; the `/api/export-persona` endpoint and web UI stay in this fork.

---

## 5. Verification Commands

```powershell
# Run the text and API tests
uv run pytest -n 3 -v tests/test_split_sentences.py tests/test_indic_normalizer.py tests/test_python_api.py

# Static type check
uv run ty check pocket_tts tests

# Start local web app
uv run pocket-tts serve --language multilingual
```

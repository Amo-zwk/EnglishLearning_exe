# EnglishLearning

[中文说明](README.zh-CN.md)

Turn Gemini-generated English phrase explanations into manually reviewed Anki cards.

EnglishLearning is a local workspace for generating, reviewing, editing, and submitting useful phrase cards without losing the full AI context.

## GitHub Quick Intro

- Personal tool, not a public SaaS product
- The bundled prompt file is required for the intended output contract
- Generate phrase explanations with Gemini from one or more input words
- Review the full AI output before choosing what actually goes into Anki
- Edit extracted `Front` and `Back` pairs, handle duplicate `Front` values, and submit only the good cards

Short repo description:

```text
Personal English phrase card workspace with Gemini generation, manual review, and Anki submission.
```

## Documentation

- English docs index: [`docs/README.md`](docs/README.md)
- Chinese docs index: [`docs/README.zh-CN.md`](docs/README.zh-CN.md)
- English scenario index: [`docs/scenario/README.md`](docs/scenario/README.md)
- Chinese scenario index: [`docs/scenario/README.zh-CN.md`](docs/scenario/README.zh-CN.md)
- English contribution guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Chinese contribution guide: [`CONTRIBUTING.zh-CN.md`](CONTRIBUTING.zh-CN.md)

## 3-Minute Quick Start

1. Install `Python 3.12+` and `uv`.
2. Clone the repo and run `uv sync`.
3. Put your Gemini key in `key`, or set `GEMINI_API_KEY`.
4. Keep `英语二的备考prompt.txt` in the project root.
5. If you want Anki submission, open Anki with AnkiConnect enabled.
6. If your local AnkiConnect uses a custom host or port, put that JSON config into the project-root `AnkiConnect` file, or set `COPY_FORMAT_ANKI_CONNECT_URL` directly.
7. Start the app:

```bash
uv run python -m src.web_entrypoint
```

8. Open:

```text
http://127.0.0.1:8031
```

If you only need the most important setup locations, jump to [`Where To Change URL And API Key`](#where-to-change-url-and-api-key).

If `uv` does not work on your machine yet, read [`Install Python And uv By OS`](#install-python-and-uv-by-os) first.

## Quick View

- Multiple input blocks for one batch
- Full AI response and extracted pairs shown together
- Editable `Front` and `Back` before submission
- Sticky overview plus card-based final preview
- Duplicate `Front` handling with manual lock priority
- Clearer feedback for submitted, skipped, and failed cards
- Local deck selection through AnkiConnect

## Screenshot

![Review workspace screenshot](docs/images/review-workspace.png)

## What It Does

- Generates full AI explanations for one or more input words
- Extracts phrase pairs from the special copy format output
- Lets you review, edit, select, and lock duplicate `Front` values before submission
- Keeps the current review counts visible during larger batches
- Shows the exact final Anki submission set with a card-based preview
- Shows clearer post-submit feedback with grouped submitted, skipped, and failed results
- Submits selected phrase pairs to Anki through AnkiConnect

## Workflow

1. Enter one or more English words in the local web page.
2. Click the generate button to request AI output.
3. Review the full response and the extracted phrase pairs.
4. Edit `Front` and `Back` values when needed.
5. Optionally uncheck low-value pairs or lock a duplicate `Front` to keep a preferred version.
6. Preview the final submission cards.
7. Select a target deck and submit to Anki.
8. Review grouped submission feedback for added, skipped, and failed items.

## Example Session

Input words:

```text
take
bring
```

What you review on the page:

- The full Gemini response for each input word
- Extracted phrase pairs from the copy-only format
- Checkboxes for whether each pair should be submitted
- Lock controls for choosing the preferred item when duplicate `Front` values appear
- A sticky review overview that keeps batch counts visible
- A card-based preview of the exact notes that will be sent to Anki
- Submission feedback grouped by submitted, skipped, and failed results

This keeps the AI output visible while still letting you manually curate the final study cards.

## Interface Highlights

The review page is organized around a small set of practical panels:

- input blocks for one or more words
- a sticky review overview for batch progress
- the full Gemini response for each word
- extracted phrase pairs with editable `Front` and `Back`
- selection and lock controls for duplicate handling
- a card-based submission preview before sending notes to Anki
- clearer submission feedback cards after sending notes to Anki

This layout is meant to preserve context from the AI output while keeping the final Anki submission set easy to inspect.

## Roadmap

- GitHub roadmap issue: [#1 Track next workflow improvements](https://github.com/Amo-zwk/EnglishLearning/issues/1)
- Done: [#2 Improve review layout for larger batches](https://github.com/Amo-zwk/EnglishLearning/issues/2)
- Done: [#4 Add clearer Anki submission feedback](https://github.com/Amo-zwk/EnglishLearning/issues/4)
- Planned polish includes a README screenshot or GIF once browser capture tooling is available in this environment.
- Future items stay focused on practical workflow improvements rather than turning the project into a public SaaS product.

## Key Rules

- The bundled prompt file `英语二的备考prompt.txt` is a required project file.
- This workflow is tied to that prompt and does not support replacing it with a different prompt while expecting the same extraction contract.
- Only content extracted from the copy-only format is used for Anki submission.
- Low-value phrase pairs should be skipped instead of added.
- Notes use the built-in `Basic` note type.
- `Front` is the English phrase.
- `Back` is the Chinese explanation.
- Duplicate checks are based on `Front`.
- If duplicate `Front` values exist, a locked item wins; otherwise the first selected item wins.

## Tech Stack

- Python 3.12+
- `uv` for environment and command execution
- Standard library WSGI server for the local site
- Gemini REST integration for generation
- AnkiConnect for deck listing and note submission

## Project Structure

- `src/web_entrypoint.py`: local web entrypoint and browser-side UI script
- `src/review_workspace.py`: review state, export logic, preview logic, submission flow
- `src/gemini_generation_adapter.py`: Gemini adapter and local config loading
- `src/anki_submission_gateway.py`: AnkiConnect integration and duplicate handling
- `src/ai_generation_orchestrator.py`: multi-input generation orchestration and timing
- `tests/`: unit and integration-style coverage for the workflow

## Installation

If you just want the shortest path to a working local setup:

1. Install Python 3.12 or newer.
2. Install `uv`.
3. Install Git, or download the source code as a ZIP file.
4. Run `uv sync` in the project root.
5. Put your Gemini key into the local `key` file, or set `GEMINI_API_KEY`.
6. Make sure `英语二的备考prompt.txt` stays in the project root.
7. If you want Anki submission, open Anki with AnkiConnect enabled.
8. Start the site with `uv run python -m src.web_entrypoint`.

### Install Git Or Download The Source Code

Some users cannot run `git clone` simply because Git is not installed yet. If that is your case, either install Git first or download the repository ZIP from GitHub and extract it locally.

#### Windows

- Install Git from `https://git-scm.com/download/win`.
- After installation, open a new PowerShell window and check:

```powershell
git --version
```

- If you do not want to install Git yet, download this ZIP instead and extract it:
  - `https://github.com/Amo-zwk/EnglishLearning/archive/refs/heads/main.zip`

#### macOS

- Install Git by running `git --version` in Terminal and accepting the system prompt, or install it with Homebrew.
- Confirm installation:

```bash
git --version
```

- If you do not want to install Git yet, download this ZIP instead and extract it:
  - `https://github.com/Amo-zwk/EnglishLearning/archive/refs/heads/main.zip`

#### Ubuntu Or Debian

- Install Git:

```bash
sudo apt update
sudo apt install -y git
```

- Confirm installation:

```bash
git --version
```

- If you do not want to install Git yet, download the repository ZIP from:
  - `https://github.com/Amo-zwk/EnglishLearning/archive/refs/heads/main.zip`

#### Fedora

- Install Git:

```bash
sudo dnf install -y git
```

- Confirm installation:

```bash
git --version
```

- If you do not want to install Git yet, download the repository ZIP from:
  - `https://github.com/Amo-zwk/EnglishLearning/archive/refs/heads/main.zip`

### Install Python And uv By OS

If `uv sync` or `uv run` fails immediately, the usual reason is that Python or `uv` was never installed correctly, or the shell has not reloaded after installation.

#### Windows

1. Install Python 3.12+ from `https://www.python.org/downloads/windows/`.
2. During installation, enable `Add python.exe to PATH`.
3. Open PowerShell and install `uv`:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

4. Close PowerShell and open it again.
5. Confirm installation:

```powershell
python --version
uv --version
```

If `python` is still missing, try `py --version`.

#### macOS

1. Install Python 3.12+ from `https://www.python.org/downloads/macos/`, or install it with Homebrew.
2. Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Reload your shell:

```bash
source ~/.zshrc
```

4. Confirm installation:

```bash
python3 --version
uv --version
```

If you use a shell other than `zsh`, reload the matching shell config file instead.

#### Ubuntu Or Debian

1. Install Python and common setup tools:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
```

2. Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Reload your shell:

```bash
source ~/.bashrc
```

4. Confirm installation:

```bash
python3 --version
uv --version
```

#### Fedora

1. Install Python and curl:

```bash
sudo dnf install -y python3 python3-pip curl
```

2. Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Reload your shell and confirm:

```bash
source ~/.bashrc
python3 --version
uv --version
```

### If uv Still Does Not Work

- Open a new terminal window and run `uv --version` again.
- If the shell says `uv: command not found`, the install succeeded but `PATH` was not reloaded.
- On macOS or Linux, try `source ~/.zshrc` or `source ~/.bashrc`, then re-run `uv --version`.
- On Windows, fully close PowerShell or CMD and open a new one.
- If Python is missing, install Python first and then repeat the `uv` installation.
- If `uv sync` fails inside the repo, run `uv python list` to confirm that `uv` can see Python.

### Example Install Commands By OS

Use the example that matches your terminal. If Git is not installed yet, skip the `git clone` step and extract the ZIP file first, then open the extracted `EnglishLearning-main` folder in your terminal.

#### Windows PowerShell

With Git installed:

```powershell
git clone git@github.com:Amo-zwk/EnglishLearning.git
cd EnglishLearning
uv sync
uv run python -m src.web_entrypoint
```

Without Git, after extracting the ZIP:

```powershell
cd EnglishLearning-main
uv sync
uv run python -m src.web_entrypoint
```

If `python` is not available in PowerShell but `py` is, use:

```powershell
uv run py -m src.web_entrypoint
```

#### macOS Terminal

With Git installed:

```bash
git clone git@github.com:Amo-zwk/EnglishLearning.git
cd EnglishLearning
uv sync
uv run python -m src.web_entrypoint
```

Without Git, after extracting the ZIP:

```bash
cd EnglishLearning-main
uv sync
uv run python -m src.web_entrypoint
```

If your machine exposes Python as `python3`, use:

```bash
uv run python3 -m src.web_entrypoint
```

#### Ubuntu Or Debian Terminal

With Git installed:

```bash
git clone git@github.com:Amo-zwk/EnglishLearning.git
cd EnglishLearning
uv sync
uv run python -m src.web_entrypoint
```

Without Git, after extracting the ZIP:

```bash
cd EnglishLearning-main
uv sync
uv run python -m src.web_entrypoint
```

If the system only exposes `python3`, use:

```bash
uv run python3 -m src.web_entrypoint
```

#### Fedora Terminal

With Git installed:

```bash
git clone git@github.com:Amo-zwk/EnglishLearning.git
cd EnglishLearning
uv sync
uv run python -m src.web_entrypoint
```

Without Git, after extracting the ZIP:

```bash
cd EnglishLearning-main
uv sync
uv run python -m src.web_entrypoint
```

If the system only exposes `python3`, use:

```bash
uv run python3 -m src.web_entrypoint
```

After startup, open `http://127.0.0.1:8031` in your browser.

## Run Locally

### Windows PowerShell

1. Open PowerShell in the project root.
2. Install dependencies:

```powershell
uv sync
```

3. Start the local site:

```powershell
uv run python -m src.web_entrypoint
```

If `python` is unavailable but `py` works, use:

```powershell
uv run py -m src.web_entrypoint
```

4. Open the local page:

```text
http://127.0.0.1:8031
```

### macOS Terminal

1. Open Terminal in the project root.
2. Install dependencies:

```bash
uv sync
```

3. Start the local site:

```bash
uv run python -m src.web_entrypoint
```

If your machine uses `python3`, run:

```bash
uv run python3 -m src.web_entrypoint
```

4. Open the local page:

```text
http://127.0.0.1:8031
```

### Ubuntu Or Debian Terminal

1. Open a terminal in the project root.
2. Install dependencies:

```bash
uv sync
```

3. Start the local site:

```bash
uv run python -m src.web_entrypoint
```

If your system only exposes `python3`, run:

```bash
uv run python3 -m src.web_entrypoint
```

4. Open the local page:

```text
http://127.0.0.1:8031
```

### Fedora Terminal

1. Open a terminal in the project root.
2. Install dependencies:

```bash
uv sync
```

3. Start the local site:

```bash
uv run python -m src.web_entrypoint
```

If your system only exposes `python3`, run:

```bash
uv run python3 -m src.web_entrypoint
```

4. Open the local page:

```text
http://127.0.0.1:8031
```

If the page does not open, check whether you changed the port through `COPY_FORMAT_WEB_PORT`.

## Where To Change URL And API Key

If you are trying to adapt this project in another place, these are the settings people usually spend too long trying to find:

- Gemini API key source:
  - default local file: `key`
  - environment override: `GEMINI_API_KEY`
  - alternate key file path: `COPY_FORMAT_GEMINI_KEY_FILE`
- Gemini request URL:
  - defined in `src/gemini_generation_adapter.py:12`
  - default endpoint template: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Prompt file path:
  - default file: `英语二的备考prompt.txt`
  - relocation override: `COPY_FORMAT_PROMPT_FILE`
- Local web page URL:
  - default address: `http://127.0.0.1:8031`
  - port override: `COPY_FORMAT_WEB_PORT`
- AnkiConnect URL:
  - resolved in `src/anki_submission_gateway.py`
  - explicit override: `COPY_FORMAT_ANKI_CONNECT_URL`
  - config file override: project-root `AnkiConnect` or `COPY_FORMAT_ANKI_CONNECT_CONFIG_FILE`
  - fallback default: `http://127.0.0.1:8765`

Most users only need to touch `key`, `GEMINI_API_KEY`, `COPY_FORMAT_WEB_PORT`, or the local `AnkiConnect` file.

## Optional Configuration

- `COPY_FORMAT_WEB_PORT`: override the local HTTP port
- `COPY_FORMAT_GENERATION_CALLABLE`: use a custom local generation adapter with `<file-path>:<callable-name>`
- `COPY_FORMAT_GENERATION_API_BASE_URL`: base URL for an OpenAI-compatible Chat Completions gateway, for example `https://api.apifast.tech/v1`
- `COPY_FORMAT_GENERATION_CONFIG_FILE`: override the local generation config JSON path, defaulting to the project-root `GenerationConfig`
- `GEMINI_API_KEY`: use a Gemini key from the environment instead of a local file
- `COPY_FORMAT_GEMINI_KEY_FILE`: override the local key file path
- `COPY_FORMAT_PROMPT_FILE`: override the prompt file path only if you are relocating the same required project prompt
- `COPY_FORMAT_GEMINI_MODEL`: override the Gemini model name, default is `gemini-2.5-pro`
- `COPY_FORMAT_ANKI_CONNECT_URL`: override the full AnkiConnect URL directly
- `COPY_FORMAT_ANKI_CONNECT_CONFIG_FILE`: override the path to the local `AnkiConnect` JSON config file

Example:

```bash
COPY_FORMAT_WEB_PORT=8042 \
COPY_FORMAT_GENERATION_CALLABLE=/absolute/path/to/local_generation_adapter.py:generate_word \
uv run python -m src.web_entrypoint
```

If you do not want to pass environment variables every time, create a local `GenerationConfig` in the project root:

```json
{
    "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
    "COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-pro"
}
```

This file is machine-local configuration and is ignored by Git by default.

## AnkiConnect Setup

The deck dropdown is loaded through AnkiConnect. If Anki is open but the deck list is still empty, check these items in order:

1. Make sure Anki itself is running.
2. Make sure the AnkiConnect add-on is installed and enabled inside Anki.
3. If you keep an AnkiConnect config JSON, place it in the project root as `AnkiConnect`.
4. If you prefer another location, set `COPY_FORMAT_ANKI_CONNECT_CONFIG_FILE` to that file path.
5. If you already know the exact URL, set `COPY_FORMAT_ANKI_CONNECT_URL` instead.

Important: this project can read your local AnkiConnect settings, but it cannot guess them for every user. If your Anki setup uses another host or port, you must update the local `AnkiConnect` file or set the matching environment variable yourself.

Example `AnkiConnect` file:

```json
{
    "apiKey": null,
    "apiLogPath": null,
    "ignoreOriginList": [],
    "webBindAddress": "127.0.0.1",
    "webBindPort": 8765,
    "webCorsOriginList": [
        "http://localhost"
    ]
}
```

This file is intentionally ignored by Git because it is local machine configuration.

## Required Project Files

These files are part of the intended project setup:

- `英语二的备考prompt.txt`

The prompt file is versioned because the generation contract depends on it.

Why this prompt must stay fixed:

- The extractor depends on the copy-only output pattern produced by this prompt.
- Review, duplicate handling, preview, and Anki submission all assume that stable output contract.
- Replacing the prompt is likely to break extraction quality or the `Front` and `Back` mapping, even if generation still returns fluent text.

## Local Files Kept Out Of Git

These files are intentionally ignored:

- `key`
- `AnkiConnect`

This keeps personal credentials out of version control while preserving the required project prompt.

## Verification

Run the test suite:

```bash
uv run python -m unittest discover -s tests
```

Compile-check key modules:

```bash
uv run python -m py_compile "src/web_entrypoint.py" "src/review_workspace.py"
```

## Notes

- This repository is designed for a personal workflow rather than a public SaaS product.
- The bundled prompt file is part of the product behavior, not an optional example.
- If local Gemini configuration is unavailable, the app falls back to the built-in demo generation adapter.
- If you previously exposed a real Gemini key, rotate it before continued use.

## FAQ

- Why does the `uv` command not work?
  - Make sure both Python and `uv` are installed first.
  - Use the OS-specific steps in [`Install Python And uv By OS`](#install-python-and-uv-by-os).
  - After installing `uv`, open a new terminal or reload your shell config.
  - Check `uv --version` before running `uv sync`.
  - If `uv` exists but cannot find Python, install Python 3.12+ and run `uv python list`.
- Why is generation not working?
  - Check whether `key` exists or `GEMINI_API_KEY` is set.
  - Check whether `英语二的备考prompt.txt` is still in the project root.
  - Check whether the local page is running at `http://127.0.0.1:8031` or your overridden port.
- Why is Anki submission not working?
  - Make sure Anki is open.
  - Make sure AnkiConnect is installed and reachable at the URL resolved from `COPY_FORMAT_ANKI_CONNECT_URL`, your local `AnkiConnect` file, or the fallback `http://127.0.0.1:8765`.
  - If your deck list is empty, verify the project-root `AnkiConnect` file points to the same host and port AnkiConnect is actually using.
  - Make sure you selected a target deck before submission.
- Why can I not swap in another prompt?
  - This workflow depends on the copy-only extraction contract produced by the bundled prompt.
  - Replacing the prompt may still generate text, but it can break extraction and `Front` or `Back` mapping.

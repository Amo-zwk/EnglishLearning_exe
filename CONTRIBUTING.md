# Contributing

[中文说明](CONTRIBUTING.zh-CN.md)

This repository is mainly a personal tool, but clear contribution rules still make later maintenance easier.

## Scope

- Keep the project focused on a personal English phrase card workflow.
- Prefer practical workflow improvements over platform-style expansion.
- Treat `英语二的备考prompt.txt` as a required product file, not a replaceable sample.
- Preserve the rule that only copy-only extracted pairs are eligible for Anki submission.

## Before You Change Anything

- Read [`README.md`](README.md) for the product goal and workflow.
- Read [`docs/README.md`](docs/README.md) and [`docs/scenario/README.md`](docs/scenario/README.md) for implementation context.
- Follow the current architecture instead of introducing a separate framework layer without a strong reason.

## Local Setup Notes

- Make sure Python 3.12+ is installed before trying to run `uv` commands for this repo.
- If `uv` is missing, install it with the OS-specific steps in [`README.md`](README.md#install-python-and-uv-by-os).
- If `uv` was just installed but the shell still says `command not found`, reload the shell config or open a new terminal window.
- If `uv` runs but cannot find Python, verify Python first and then run `uv python list`.
- If contributors report setup trouble, keep the troubleshooting notes in [`README.md`](README.md#faq) aligned with the actual onboarding flow.

## Implementation Expectations

- Keep UI text user-facing in Chinese unless the surrounding area is already English.
- Keep code comments and documentation prose in English unless the file is a Chinese-facing document.
- Use the built-in `Basic` note type for Anki submission.
- Keep duplicate handling based on `Front`.
- Avoid adding low-value phrase pairs just because the model produced them.

## Verification

Run these commands before opening a PR or merging local work:

```bash
uv run python -m unittest discover -s tests
uv run python -m py_compile "src/web_entrypoint.py" "src/review_workspace.py"
```

## Pull Request Notes

- Explain the workflow problem being solved, not just the files changed.
- Mention any affected scenario docs in `docs/scenario/`.
- Include screenshots when UI structure changes in a meaningful way.
- Keep PRs small when possible so the review flow stays easy to follow.

## Documentation

- Update both [`README.md`](README.md) and [`README.zh-CN.md`](README.zh-CN.md) when user-visible behavior changes.
- Add or update doc indexes when new documentation folders or major scenario groups appear.

## Security And Privacy

- Never commit local secrets such as `key`.
- Keep the required project prompt in git, but keep personal secrets and unrelated local tuning files out of git.
- Rotate any exposed credentials before continued use.

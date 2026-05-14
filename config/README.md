# Configuration

This directory separates portable project files from machine-specific settings.

- `templates/` keeps safe example configuration files.
- `local/` is created by `configure_environment` and is ignored by git.
- Existing root-level files such as `key`, `GenerationConfig`, and `AnkiConnect` still work as legacy fallbacks.

Recommended portable flow:

1. Run `install_environment.bat` or `install_environment.sh`.
2. Run `configure_environment.bat` or `configure_environment.sh`.
3. Run `launch_app.bat` or `launch_app.sh`.

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.portable_common import (
    DEFAULT_WEB_PORT,
    PortableSetupError,
    apply_runtime_env,
    load_runtime_env,
    print_header,
    print_key_values,
    runtime_paths,
)


def ensure_project_import_path() -> None:
    root_text = str(runtime_paths().root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def parse_port() -> int:
    value = os.environ.get("COPY_FORMAT_WEB_PORT", str(DEFAULT_WEB_PORT)).strip()
    try:
        port = int(value)
    except ValueError as error:
        raise PortableSetupError("COPY_FORMAT_WEB_PORT must be a number.") from error
    if port <= 0 or port > 65535:
        raise PortableSetupError("COPY_FORMAT_WEB_PORT must be between 1 and 65535.")
    return port


def open_browser_later(url: str) -> None:
    def _open() -> None:
        time.sleep(0.8)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def should_open_browser() -> bool:
    value = os.environ.get("COPY_FORMAT_OPEN_BROWSER", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def main() -> int:
    print_header("EnglishLearning portable launcher")
    runtime_env = load_runtime_env()
    if not runtime_env:
        print(
            "[warn] No local runtime.env was found. Run configure_environment first for real generation settings."
        )
    apply_runtime_env(runtime_env)
    ensure_project_import_path()

    try:
        port = parse_port()
    except PortableSetupError as error:
        print(f"[error] {error}")
        return 1

    from src.web_entrypoint import DEFAULT_HOST, run_local_server

    url = f"http://{DEFAULT_HOST}:{port}"
    print_key_values(
        [
            ("Project root", runtime_paths().root),
            ("Runtime env", runtime_paths().runtime_env),
            ("URL", url),
        ]
    )
    if should_open_browser():
        open_browser_later(url)
    run_local_server(host=DEFAULT_HOST, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

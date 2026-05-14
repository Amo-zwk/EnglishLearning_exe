from __future__ import annotations

import argparse
import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.portable_common import (
    CONFIG_LOCAL_DIR,
    DEFAULT_ANKI_CONNECT_URL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_COMPATIBLE_MODEL,
    DEFAULT_PROMPT_FILE,
    DEFAULT_WEB_PORT,
    PortableSetupError,
    ensure_portable_directories,
    format_path,
    parse_anki_connect_url,
    print_header,
    print_key_values,
    read_json_file,
    runtime_paths,
    write_json_file,
    write_runtime_env,
)


GENERATION_CONFIG_FILE = CONFIG_LOCAL_DIR / "GenerationConfig"
ANKI_CONNECT_CONFIG_FILE = CONFIG_LOCAL_DIR / "AnkiConnect"
KEY_FILE = CONFIG_LOCAL_DIR / "key"


def prompt_text(label: str, default: str = "", use_default: bool = False) -> str:
    if use_default:
        print(f"{label}: {default}")
        return default
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_secret(
    label: str,
    existing_value: str = "",
    use_default: bool = False,
) -> str:
    if use_default:
        print(f"{label}: {'existing value kept' if existing_value else 'skipped'}")
        return existing_value
    hint = " [press Enter to keep existing]" if existing_value else " [press Enter to skip]"
    value = getpass.getpass(f"{label}{hint}: ").strip()
    return value or existing_value


def read_existing_key() -> str:
    for key_path in (KEY_FILE, runtime_paths().root / "key"):
        if key_path.exists():
            return key_path.read_text(encoding="utf-8").strip()
    return ""


def resolve_default_generation_values() -> tuple[str, str]:
    existing_config = read_json_file(GENERATION_CONFIG_FILE)
    legacy_config = read_json_file(runtime_paths().root / "GenerationConfig")
    combined = {**legacy_config, **existing_config}
    base_url = str(combined.get("COPY_FORMAT_GENERATION_API_BASE_URL", "") or "")
    model = str(combined.get("COPY_FORMAT_GEMINI_MODEL", "") or "")
    if not model:
        model = DEFAULT_OPENAI_COMPATIBLE_MODEL if base_url else DEFAULT_GEMINI_MODEL
    return base_url.strip(), model.strip()


def resolve_default_anki_url() -> str:
    existing_config = read_json_file(ANKI_CONNECT_CONFIG_FILE)
    legacy_config = read_json_file(runtime_paths().root / "AnkiConnect")
    combined = {**legacy_config, **existing_config}
    bind_address = combined.get("webBindAddress")
    bind_port = combined.get("webBindPort")
    if isinstance(bind_address, str) and isinstance(bind_port, int):
        return f"http://{bind_address}:{bind_port}"
    return DEFAULT_ANKI_CONNECT_URL


def configure_key(
    api_key_argument: str | None = None,
    skip_key: bool = False,
    use_defaults: bool = False,
) -> None:
    if skip_key:
        print("[skip] API key unchanged.")
        return
    existing_key = read_existing_key()
    api_key = (
        api_key_argument.strip()
        if api_key_argument is not None
        else prompt_secret(
            "Gemini or OpenAI-compatible API key",
            existing_key,
            use_default=use_defaults,
        )
    )
    if api_key:
        KEY_FILE.write_text(api_key.strip() + "\n", encoding="utf-8")
        print(f"[ok] API key saved to {KEY_FILE}")
        return
    print("[warn] No API key saved. The app can open, but generation will use demo mode until a key is configured.")


def configure_generation(use_defaults: bool = False) -> None:
    default_base_url, default_model = resolve_default_generation_values()
    base_url = prompt_text(
        "OpenAI-compatible base URL (leave empty for official Gemini)",
        default_base_url,
        use_default=use_defaults,
    ).rstrip("/")
    suggested_model = default_model or (
        DEFAULT_OPENAI_COMPATIBLE_MODEL if base_url else DEFAULT_GEMINI_MODEL
    )
    model = prompt_text("Model name", suggested_model, use_default=use_defaults)

    payload: dict[str, object] = {}
    if base_url:
        payload["COPY_FORMAT_GENERATION_API_BASE_URL"] = base_url
    if model:
        payload["COPY_FORMAT_GEMINI_MODEL"] = model
    write_json_file(GENERATION_CONFIG_FILE, payload)
    print(f"[ok] Generation config saved to {GENERATION_CONFIG_FILE}")


def configure_anki_connect(use_defaults: bool = False) -> None:
    while True:
        url = prompt_text(
            "AnkiConnect URL",
            resolve_default_anki_url(),
            use_default=use_defaults,
        )
        try:
            host, port = parse_anki_connect_url(url)
            break
        except PortableSetupError as error:
            print(f"[warn] {error}")
            if use_defaults:
                raise

    write_json_file(
        ANKI_CONNECT_CONFIG_FILE,
        {
            "webBindAddress": host,
            "webBindPort": port,
        },
    )
    print(f"[ok] AnkiConnect config saved to {ANKI_CONNECT_CONFIG_FILE}")


def configure_runtime_env(
    port_argument: int | None = None,
    use_defaults: bool = False,
) -> None:
    port_text = (
        str(port_argument)
        if port_argument is not None
        else prompt_text("Web app port", str(DEFAULT_WEB_PORT), use_default=use_defaults)
    )
    try:
        port = int(port_text)
    except ValueError as error:
        raise PortableSetupError("Web app port must be a number.") from error
    if port <= 0 or port > 65535:
        raise PortableSetupError("Web app port must be between 1 and 65535.")

    if not DEFAULT_PROMPT_FILE.exists():
        raise PortableSetupError(f"Prompt file was not found: {DEFAULT_PROMPT_FILE}")

    write_runtime_env(
        {
            "COPY_FORMAT_GEMINI_KEY_FILE": format_path(KEY_FILE),
            "COPY_FORMAT_GENERATION_CONFIG_FILE": format_path(GENERATION_CONFIG_FILE),
            "COPY_FORMAT_ANKI_CONNECT_CONFIG_FILE": format_path(
                ANKI_CONNECT_CONFIG_FILE
            ),
            "COPY_FORMAT_PROMPT_FILE": format_path(DEFAULT_PROMPT_FILE),
            "COPY_FORMAT_WEB_PORT": str(port),
        }
    )
    print(f"[ok] Runtime env saved to {runtime_paths().runtime_env}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure the portable EnglishLearning runtime."
    )
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="Use default answers for non-secret prompts.",
    )
    parser.add_argument(
        "--skip-key",
        action="store_true",
        help="Leave API key files unchanged.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Write an API key without prompting. Prefer the interactive prompt for personal use.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Set the local web app port without prompting.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print_header("EnglishLearning portable environment configurator")
    try:
        ensure_portable_directories()
        configure_key(
            api_key_argument=args.api_key,
            skip_key=args.skip_key,
            use_defaults=args.defaults,
        )
        configure_generation(use_defaults=args.defaults)
        configure_anki_connect(use_defaults=args.defaults)
        configure_runtime_env(port_argument=args.port, use_defaults=args.defaults)
    except PortableSetupError as error:
        print(f"[error] {error}")
        return 1

    print_header("Configuration complete")
    print_key_values(
        [
            ("Local config", runtime_paths().config_local),
            ("Runtime env", runtime_paths().runtime_env),
            ("Next step", "run launch_app.bat or launch_app.sh"),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

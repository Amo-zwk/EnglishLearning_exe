from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

from src.anki_submission_gateway import ANKI_CONNECT_URL
from src.gemini_generation_adapter import (
    BASE_URL_ENV,
    DEFAULT_MODEL,
    DEFAULT_OPENAI_COMPATIBLE_MODEL,
    MODEL_ENV,
)


APP_NAME = "EnglishLearning"
DESKTOP_CONFIG_DIR_ENV = "ENGLISHLEARNING_CONFIG_DIR"
DESKTOP_MODE_ENV = "COPY_FORMAT_DESKTOP_MODE"
KEY_FILE_ENV = "COPY_FORMAT_GEMINI_KEY_FILE"
GENERATION_CONFIG_ENV = "COPY_FORMAT_GENERATION_CONFIG_FILE"
ANKI_CONNECT_CONFIG_ENV = "COPY_FORMAT_ANKI_CONNECT_CONFIG_FILE"
PROMPT_FILE_ENV = "COPY_FORMAT_PROMPT_FILE"
WEB_PORT_ENV = "COPY_FORMAT_WEB_PORT"
KEY_FILE_NAME = "key"
GENERATION_CONFIG_FILE_NAME = "GenerationConfig"
ANKI_CONNECT_CONFIG_FILE_NAME = "AnkiConnect"
PROMPT_FILE_NAME = "英语二的备考prompt.txt"


@dataclass(frozen=True)
class DesktopConfigPaths:
    config_dir: Path
    key_file: Path
    generation_config_file: Path
    anki_connect_config_file: Path
    prompt_file: Path


@dataclass(frozen=True)
class DesktopSettings:
    paths: DesktopConfigPaths
    has_api_key: bool
    base_url: str
    model_name: str
    anki_connect_url: str


def bundled_resource_path(relative_path: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return bundle_root / relative_path


def desktop_config_dir(environ: dict[str, str] | None = None) -> Path:
    environment = environ if environ is not None else os.environ
    override = environment.get(DESKTOP_CONFIG_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        appdata = environment.get("APPDATA", "").strip()
        base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        xdg_config_home = environment.get("XDG_CONFIG_HOME", "").strip()
        base_dir = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base_dir / APP_NAME


def desktop_config_paths(config_dir: Path | None = None) -> DesktopConfigPaths:
    resolved_config_dir = config_dir or desktop_config_dir()
    return DesktopConfigPaths(
        config_dir=resolved_config_dir,
        key_file=resolved_config_dir / KEY_FILE_NAME,
        generation_config_file=resolved_config_dir / GENERATION_CONFIG_FILE_NAME,
        anki_connect_config_file=resolved_config_dir / ANKI_CONNECT_CONFIG_FILE_NAME,
        prompt_file=bundled_resource_path(PROMPT_FILE_NAME),
    )


def load_desktop_settings(config_dir: Path | None = None) -> DesktopSettings:
    paths = desktop_config_paths(config_dir)
    generation_config = _read_json_object(paths.generation_config_file)
    base_url = _clean_text(generation_config.get(BASE_URL_ENV, ""))
    model_name = _clean_text(generation_config.get(MODEL_ENV, ""))
    if not model_name:
        model_name = DEFAULT_OPENAI_COMPATIBLE_MODEL if base_url else DEFAULT_MODEL

    return DesktopSettings(
        paths=paths,
        has_api_key=_has_api_key(paths.key_file),
        base_url=base_url,
        model_name=model_name,
        anki_connect_url=_load_anki_connect_url(paths.anki_connect_config_file),
    )


def save_desktop_settings(
    form_values: dict[str, str],
    config_dir: Path | None = None,
) -> DesktopSettings:
    paths = desktop_config_paths(config_dir)
    paths.config_dir.mkdir(parents=True, exist_ok=True)

    api_key = form_values.get("api_key", "").strip()
    if api_key:
        paths.key_file.write_text(api_key + "\n", encoding="utf-8")

    base_url = form_values.get("base_url", "").strip().rstrip("/")
    model_name = form_values.get("model_name", "").strip()
    if not model_name:
        model_name = DEFAULT_OPENAI_COMPATIBLE_MODEL if base_url else DEFAULT_MODEL

    generation_config: dict[str, str] = {}
    if base_url:
        generation_config[BASE_URL_ENV] = base_url
    generation_config[MODEL_ENV] = model_name
    _write_json_object(paths.generation_config_file, generation_config)

    anki_connect_url = form_values.get("anki_connect_url", ANKI_CONNECT_URL).strip()
    bind_address, bind_port = parse_anki_connect_url(anki_connect_url)
    _write_json_object(
        paths.anki_connect_config_file,
        {
            "webBindAddress": bind_address,
            "webBindPort": bind_port,
        },
    )

    return load_desktop_settings(paths.config_dir)


def apply_desktop_environment(
    config_dir: Path | None = None,
    port: int | None = None,
) -> DesktopSettings:
    settings = load_desktop_settings(config_dir)
    settings.paths.config_dir.mkdir(parents=True, exist_ok=True)

    os.environ[DESKTOP_MODE_ENV] = "1"
    os.environ[KEY_FILE_ENV] = str(settings.paths.key_file)
    os.environ[GENERATION_CONFIG_ENV] = str(settings.paths.generation_config_file)
    os.environ[ANKI_CONNECT_CONFIG_ENV] = str(settings.paths.anki_connect_config_file)
    os.environ[PROMPT_FILE_ENV] = str(settings.paths.prompt_file)
    if port is not None:
        os.environ[WEB_PORT_ENV] = str(port)
    return settings


def is_first_run(settings: DesktopSettings) -> bool:
    return not settings.has_api_key or not settings.paths.generation_config_file.exists()


def parse_anki_connect_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("AnkiConnect 地址必须以 http:// 或 https:// 开头。")
    if not parsed.hostname:
        raise ValueError("AnkiConnect 地址缺少主机名。")
    if parsed.port is None:
        raise ValueError("AnkiConnect 地址需要端口，默认通常是 8765。")
    return parsed.hostname, int(parsed.port)


def _load_anki_connect_url(path: Path) -> str:
    payload = _read_json_object(path)
    bind_address = payload.get("webBindAddress")
    bind_port = payload.get("webBindPort")
    if isinstance(bind_address, str) and isinstance(bind_port, int):
        return f"http://{bind_address}:{bind_port}"
    return ANKI_CONNECT_URL


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_object(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _has_api_key(path: Path) -> bool:
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""

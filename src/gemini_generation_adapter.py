from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib import request


DEFAULT_MODEL = "gemini-2.5-pro"
DEFAULT_OPENAI_COMPATIBLE_MODEL = "gemini-2.5-flash"
GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
OPENAI_COMPATIBLE_CHAT_COMPLETIONS_PATH = "/chat/completions"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_CONFIG_DIR = PROJECT_ROOT / "config" / "local"
DEFAULT_LOCAL_KEY_FILE = DEFAULT_LOCAL_CONFIG_DIR / "key"
DEFAULT_LOCAL_GENERATION_CONFIG_FILE = DEFAULT_LOCAL_CONFIG_DIR / "GenerationConfig"
DEFAULT_KEY_FILE = PROJECT_ROOT / "key"
DEFAULT_PROMPT_FILE = PROJECT_ROOT / "英语二的备考prompt.txt"
DEFAULT_GENERATION_CONFIG_FILE = PROJECT_ROOT / "GenerationConfig"
KEY_ENV = "GEMINI_API_KEY"
KEY_FILE_ENV = "COPY_FORMAT_GEMINI_KEY_FILE"
MODEL_ENV = "COPY_FORMAT_GEMINI_MODEL"
PROMPT_FILE_ENV = "COPY_FORMAT_PROMPT_FILE"
BASE_URL_ENV = "COPY_FORMAT_GENERATION_API_BASE_URL"
GENERATION_CONFIG_ENV = "COPY_FORMAT_GENERATION_CONFIG_FILE"

API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
OPENAI_API_KEY_PATTERN = re.compile(r"sk-[0-9A-Za-z_-]{20,}")
DEFAULT_GEMINI_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0


class MissingGeminiConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiAdapterConfig:
    api_key: str
    prompt_text: str
    model_name: str = DEFAULT_MODEL
    base_url: str | None = None


def extract_api_key(raw_text: str) -> str:
    normalized_text = raw_text.strip()
    if not normalized_text:
        raise MissingGeminiConfigurationError(
            "No Gemini API key was found in the configured key source."
        )

    match = API_KEY_PATTERN.search(raw_text)
    if match is not None:
        return match.group(0)

    if OPENAI_API_KEY_PATTERN.fullmatch(normalized_text):
        return normalized_text

    raise MissingGeminiConfigurationError(
        "No Gemini API key was found in the configured key source."
    )


def load_api_key(
    environ: dict[str, str] | None = None,
    key_file: Path | None = None,
) -> str:
    environment = environ if environ is not None else dict(__import__("os").environ)
    env_value = environment.get(KEY_ENV, "").strip()
    if env_value:
        return env_value

    resolved_key_file = _resolve_preferred_file(
        explicit_path_text=environment.get(KEY_FILE_ENV),
        requested_path=key_file,
        default_paths=(DEFAULT_LOCAL_KEY_FILE, DEFAULT_KEY_FILE),
    )
    if not resolved_key_file.exists():
        raise MissingGeminiConfigurationError(
            f"Gemini key file was not found at {resolved_key_file}."
        )

    return extract_api_key(resolved_key_file.read_text(encoding="utf-8"))


def load_prompt_text(
    environ: dict[str, str] | None = None,
    prompt_file: Path | None = None,
) -> str:
    environment = environ if environ is not None else dict(__import__("os").environ)
    resolved_prompt_file = Path(
        environment.get(PROMPT_FILE_ENV, str(prompt_file or DEFAULT_PROMPT_FILE))
    )
    if not resolved_prompt_file.exists():
        raise MissingGeminiConfigurationError(
            f"Prompt file was not found at {resolved_prompt_file}."
        )

    prompt_text = resolved_prompt_file.read_text(encoding="utf-8").strip()
    if not prompt_text:
        raise MissingGeminiConfigurationError("Prompt file is empty.")
    return prompt_text


def load_generation_config(
    environ: dict[str, str] | None = None,
    config_file: Path | None = None,
) -> dict[str, str]:
    environment = environ if environ is not None else dict(__import__("os").environ)
    resolved_config_file = _resolve_preferred_file(
        explicit_path_text=environment.get(GENERATION_CONFIG_ENV),
        requested_path=config_file,
        default_paths=(
            DEFAULT_LOCAL_GENERATION_CONFIG_FILE,
            DEFAULT_GENERATION_CONFIG_FILE,
        ),
    )
    if not resolved_config_file.exists():
        return {}

    try:
        payload = json.loads(resolved_config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MissingGeminiConfigurationError(
            f"Generation config file is invalid: {resolved_config_file}."
        ) from error

    if not isinstance(payload, dict):
        raise MissingGeminiConfigurationError(
            f"Generation config file must contain a JSON object: {resolved_config_file}."
        )

    normalized_config: dict[str, str] = {}
    for key in (BASE_URL_ENV, MODEL_ENV):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            normalized_config[key] = value.strip()
    return normalized_config


def _resolve_preferred_file(
    explicit_path_text: str | None,
    requested_path: Path | None,
    default_paths: tuple[Path, ...],
) -> Path:
    if explicit_path_text and explicit_path_text.strip():
        return Path(explicit_path_text.strip()).expanduser()
    if requested_path is not None:
        return Path(requested_path).expanduser()
    for candidate_path in default_paths:
        if candidate_path.exists():
            return candidate_path
    return default_paths[-1]


def build_generation_prompt(prompt_text: str, input_word: str) -> str:
    return (
        f"{prompt_text}\n\n"
        "现在只执行任务一：单词解析。"
        "请严格按照既有规则回答，并保留复制专用格式。"
        "如果没有值得记忆的搭配，就直接说明没有高价值搭配，不要虚构。"
        f"\n\n待解析单词：{input_word.strip()}\n"
    )


def resolve_model_name(environment: dict[str, str]) -> str:
    configured_model_name = environment.get(MODEL_ENV, "").strip()
    if configured_model_name:
        return configured_model_name
    if environment.get(BASE_URL_ENV, "").strip():
        return DEFAULT_OPENAI_COMPATIBLE_MODEL
    return DEFAULT_MODEL


def _normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized_base_url = base_url.strip().rstrip("/")
    return normalized_base_url or None


def build_generation_request_url(config: GeminiAdapterConfig) -> str:
    if config.base_url:
        return f"{config.base_url}{OPENAI_COMPATIBLE_CHAT_COMPLETIONS_PATH}"
    return GEMINI_API_URL_TEMPLATE.format(model=config.model_name)


def build_generation_request_payload(
    config: GeminiAdapterConfig,
    prompt: str,
) -> dict[str, Any]:
    if config.base_url:
        return {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.9,
            "responseMimeType": "text/plain",
        },
    }


def build_generation_request_headers(config: GeminiAdapterConfig) -> dict[str, str]:
    if config.base_url:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": config.api_key,
    }


class GeminiGenerationAdapter:
    def __init__(
        self,
        config: GeminiAdapterConfig,
        timeout_seconds: float = DEFAULT_GEMINI_TIMEOUT_SECONDS,
        post_json: Callable[
            [str, dict[str, Any], dict[str, str], float], dict[str, Any]
        ]
        | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._post_json = post_json or self._default_post_json
        self._sleep = sleep or time.sleep

    @classmethod
    def from_local_files(
        cls,
        environ: dict[str, str] | None = None,
        timeout_seconds: float = DEFAULT_GEMINI_TIMEOUT_SECONDS,
        post_json: Callable[
            [str, dict[str, Any], dict[str, str], float], dict[str, Any]
        ]
        | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> "GeminiGenerationAdapter":
        runtime_environment = (
            environ if environ is not None else dict(__import__("os").environ)
        )
        file_config = load_generation_config(runtime_environment)
        environment = {**file_config, **runtime_environment}
        config = GeminiAdapterConfig(
            api_key=load_api_key(environment),
            prompt_text=load_prompt_text(environment),
            model_name=resolve_model_name(environment),
            base_url=_normalize_base_url(environment.get(BASE_URL_ENV)),
        )
        return cls(
            config=config,
            timeout_seconds=timeout_seconds,
            post_json=post_json,
            sleep=sleep,
        )

    def generate_word(self, input_word: str) -> dict[str, str]:
        prompt = build_generation_prompt(self._config.prompt_text, input_word)
        url = build_generation_request_url(self._config)
        payload = build_generation_request_payload(self._config, prompt)
        headers = build_generation_request_headers(self._config)
        response = self._post_with_retry(url, payload, headers)
        return {"content": extract_response_text(response)}

    def _post_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt_index in range(DEFAULT_MAX_RETRY_ATTEMPTS):
            try:
                return self._post_json(url, payload, headers, self._timeout_seconds)
            except TimeoutError as error:
                last_error = error
                if not self._should_retry_attempt(attempt_index):
                    raise RuntimeError(
                        "Gemini request timed out after retries. Please retry this word later."
                    ) from error
            except HTTPError as error:
                last_error = error
                if not _is_retryable_http_status(error.code):
                    raise RuntimeError(
                        f"Gemini request failed with HTTP {error.code}. Please check the request configuration."
                    ) from error
                if not self._should_retry_attempt(attempt_index):
                    raise RuntimeError(
                        f"Gemini request failed with HTTP {error.code} after retries. Please retry this word later."
                    ) from error
            except URLError as error:
                last_error = error
                reason = getattr(error, "reason", None)
                if isinstance(reason, TimeoutError):
                    if not self._should_retry_attempt(attempt_index):
                        raise RuntimeError(
                            "Gemini request timed out after retries. Please retry this word later."
                        ) from error
                else:
                    if not self._should_retry_attempt(attempt_index):
                        raise RuntimeError(
                            "Gemini request failed after retries. Please check your network connection and retry."
                        ) from error
            if self._should_retry_attempt(attempt_index):
                self._sleep(DEFAULT_RETRY_BACKOFF_SECONDS * (2**attempt_index))
        raise RuntimeError(
            "Gemini request failed after retries. Please check your network connection and retry."
        ) from last_error

    @staticmethod
    def _should_retry_attempt(attempt_index: int) -> bool:
        return attempt_index + 1 < DEFAULT_MAX_RETRY_ATTEMPTS

    @staticmethod
    def _default_post_json(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request_body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=request_body,
            headers=headers,
            method="POST",
        )
        with request.urlopen(http_request, timeout=timeout_seconds) as http_response:
            response_body = http_response.read().decode("utf-8")
        return json.loads(response_body)


def extract_response_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates")
    if isinstance(candidates, list) and candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if not isinstance(parts, list):
            raise RuntimeError("Gemini response parts are missing.")

        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "\n".join(
            chunk for chunk in text_chunks if isinstance(chunk, str)
        ).strip()
        if text:
            return text
        raise RuntimeError("Gemini response did not contain text content.")

    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(
            "Generation response did not contain Gemini candidates or OpenAI choices."
        )

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError("Generation response choice payload is invalid.")
    message = first_choice.get("message", {})
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    text = first_choice.get("text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()
    raise RuntimeError("OpenAI-compatible response did not contain text content.")


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600


def can_build_local_adapter(
    environ: dict[str, str] | None = None,
) -> bool:
    try:
        load_api_key(environ)
        load_prompt_text(environ)
    except MissingGeminiConfigurationError:
        return False
    return True

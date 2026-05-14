import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.gemini_generation_adapter import (
    GeminiGenerationAdapter,
    MissingGeminiConfigurationError,
    build_generation_prompt,
    build_generation_request_headers,
    build_generation_request_payload,
    build_generation_request_url,
    extract_api_key,
    extract_response_text,
    GeminiAdapterConfig,
    load_generation_config,
    load_api_key,
)


class GeminiGenerationAdapterTests(unittest.TestCase):
    @staticmethod
    def _missing_generation_config_path() -> str:
        return "/tmp/opencode-missing-generation-config.json"

    @staticmethod
    def _existing_prompt_path() -> str:
        return str(Path(__file__).resolve().parent.parent / "英语二的备考prompt.txt")

    def test_extracts_api_key_from_metadata_text(self) -> None:
        raw_text = (
            "API 密钥详细信息\n"
            "API 密钥\n"
            "AIzaSyExampleKey1234567890abcd\n"
            "名称\nGemini API Key\n"
        )

        self.assertEqual(
            extract_api_key(raw_text),
            "AIzaSyExampleKey1234567890abcd",
        )

    def test_raises_when_api_key_text_is_missing(self) -> None:
        with self.assertRaises(MissingGeminiConfigurationError):
            extract_api_key("这里只是普通文本")

    def test_accepts_plain_openai_style_api_key_text(self) -> None:
        self.assertEqual(
            extract_api_key("sk-test-openai-compatible-key"),
            "sk-test-openai-compatible-key",
        )

    def test_prefers_environment_key_over_file_content(self) -> None:
        api_key = load_api_key(environ={"GEMINI_API_KEY": "AIzaSyEnvKey1234567890abcd"})

        self.assertEqual(api_key, "AIzaSyEnvKey1234567890abcd")

    def test_loads_generation_config_from_local_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "GenerationConfig"
            config_path.write_text(
                json.dumps(
                    {
                        "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
                        "COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-pro",
                    }
                ),
                encoding="utf-8",
            )

            config = load_generation_config(
                environ={"COPY_FORMAT_GENERATION_CONFIG_FILE": str(config_path)}
            )

        self.assertEqual(
            config["COPY_FORMAT_GENERATION_API_BASE_URL"],
            "https://api.apifast.tech/v1",
        )
        self.assertEqual(config["COPY_FORMAT_GEMINI_MODEL"], "gemini-2.5-pro")

    def test_loads_key_from_portable_local_config_before_legacy_root_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            local_key_path = Path(temp_dir) / "config" / "local" / "key"
            local_key_path.parent.mkdir(parents=True)
            local_key_path.write_text("AIzaSyPortableKey1234567890abcd", encoding="utf-8")
            legacy_key_path = Path(temp_dir) / "key"
            legacy_key_path.write_text("AIzaSyLegacyKey1234567890abcd", encoding="utf-8")

            with (
                patch(
                    "src.gemini_generation_adapter.DEFAULT_LOCAL_KEY_FILE",
                    local_key_path,
                ),
                patch("src.gemini_generation_adapter.DEFAULT_KEY_FILE", legacy_key_path),
            ):
                api_key = load_api_key(environ={})

        self.assertEqual(api_key, "AIzaSyPortableKey1234567890abcd")

    def test_loads_generation_config_from_portable_local_config_before_legacy_root_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            local_config_path = Path(temp_dir) / "config" / "local" / "GenerationConfig"
            local_config_path.parent.mkdir(parents=True)
            local_config_path.write_text(
                json.dumps({"COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-flash"}),
                encoding="utf-8",
            )
            legacy_config_path = Path(temp_dir) / "GenerationConfig"
            legacy_config_path.write_text(
                json.dumps({"COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-pro"}),
                encoding="utf-8",
            )

            with (
                patch(
                    "src.gemini_generation_adapter.DEFAULT_LOCAL_GENERATION_CONFIG_FILE",
                    local_config_path,
                ),
                patch(
                    "src.gemini_generation_adapter.DEFAULT_GENERATION_CONFIG_FILE",
                    legacy_config_path,
                ),
            ):
                config = load_generation_config(environ={})

        self.assertEqual(config["COPY_FORMAT_GEMINI_MODEL"], "gemini-2.5-flash")

    def test_builds_generation_prompt_from_prompt_text_and_word(self) -> None:
        prompt = build_generation_prompt("原始提示", "abandon")

        self.assertIn("原始提示", prompt)
        self.assertIn("现在只执行任务一：单词解析", prompt)
        self.assertIn("待解析单词：abandon", prompt)

    def test_extracts_joined_text_from_gemini_response(self) -> None:
        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "第一段"},
                            {"text": "第二段"},
                        ]
                    }
                }
            ]
        }

        self.assertEqual(extract_response_text(response), "第一段\n第二段")

    def test_extracts_text_from_openai_compatible_response(self) -> None:
        response = {
            "choices": [
                {"message": {"content": "(复制专用: $abandon hope$ $放弃希望$)"}}
            ]
        }

        self.assertEqual(
            extract_response_text(response), "(复制专用: $abandon hope$ $放弃希望$)"
        )

    def test_builds_openai_compatible_request_when_base_url_is_configured(self) -> None:
        config = GeminiAdapterConfig(
            api_key="sk-test-openai-compatible-key",
            prompt_text="prompt",
            model_name="gemini-2.5-flash",
            base_url="https://api.apifast.tech/v1",
        )

        self.assertEqual(
            build_generation_request_url(config),
            "https://api.apifast.tech/v1/chat/completions",
        )
        self.assertEqual(
            build_generation_request_headers(config),
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer sk-test-openai-compatible-key",
            },
        )
        self.assertEqual(
            build_generation_request_payload(config, "test prompt"),
            {
                "model": "gemini-2.5-flash",
                "messages": [{"role": "user", "content": "test prompt"}],
                "temperature": 0.3,
            },
        )

    def test_returns_content_dictionary_from_generate_word(self) -> None:
        recorded_request = {}

        def fake_post(url, payload, headers, timeout_seconds):
            recorded_request["url"] = url
            recorded_request["payload"] = payload
            recorded_request["headers"] = headers
            recorded_request["timeout_seconds"] = timeout_seconds
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "(复制专用: $abandon hope$ $放弃希望$)"}]
                        }
                    }
                ]
            }

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "AIzaSyEnvKey1234567890abcd",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-pro",
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=fake_post,
        )

        result = adapter.generate_word("abandon")

        self.assertIn("generativelanguage.googleapis.com", recorded_request["url"])
        self.assertEqual(
            recorded_request["headers"]["x-goog-api-key"],
            "AIzaSyEnvKey1234567890abcd",
        )
        self.assertIn(
            "待解析单词：abandon",
            recorded_request["payload"]["contents"][0]["parts"][0]["text"],
        )
        self.assertEqual(recorded_request["timeout_seconds"], 60.0)
        self.assertEqual(result["content"], "(复制专用: $abandon hope$ $放弃希望$)")

    def test_wraps_timeout_error_with_retry_message(self) -> None:
        attempts: list[int] = []
        sleep_calls: list[float] = []

        def flaky_post(url, payload, headers, timeout_seconds):
            attempts.append(1)
            raise TimeoutError("timed out")

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "AIzaSyEnvKey1234567890abcd",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=flaky_post,
            sleep=lambda seconds: sleep_calls.append(seconds),
        )

        with self.assertRaisesRegex(
            RuntimeError, "Gemini request timed out after retries"
        ):
            adapter.generate_word("abandon")

        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep_calls, [1.0, 2.0])

    def test_wraps_network_error_with_retry_message(self) -> None:
        attempts: list[int] = []
        sleep_calls: list[float] = []

        def flaky_post(url, payload, headers, timeout_seconds):
            attempts.append(1)
            raise URLError("network down")

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "AIzaSyEnvKey1234567890abcd",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=flaky_post,
            sleep=lambda seconds: sleep_calls.append(seconds),
        )

        with self.assertRaisesRegex(
            RuntimeError, "Gemini request failed after retries"
        ):
            adapter.generate_word("abandon")

        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep_calls, [1.0, 2.0])

    def test_retries_timeout_then_succeeds(self) -> None:
        attempts: list[int] = []
        sleep_calls: list[float] = []

        def flaky_post(url, payload, headers, timeout_seconds):
            attempts.append(1)
            if len(attempts) < 3:
                raise TimeoutError("timed out")
            return {
                "choices": [
                    {"message": {"content": "(复制专用: $abandon ship$ $弃船$)"}}
                ]
            }

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "sk-test-openai-compatible-key",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=flaky_post,
            sleep=lambda seconds: sleep_calls.append(seconds),
        )

        result = adapter.generate_word("abandon")

        self.assertEqual(result["content"], "(复制专用: $abandon ship$ $弃船$)")
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep_calls, [1.0, 2.0])

    def test_retries_retryable_http_error_then_succeeds(self) -> None:
        attempts: list[int] = []
        sleep_calls: list[float] = []

        def flaky_post(url, payload, headers, timeout_seconds):
            attempts.append(1)
            if len(attempts) == 1:
                raise HTTPError(url, 429, "Too Many Requests", hdrs=Message(), fp=None)
            return {
                "choices": [
                    {"message": {"content": "(复制专用: $abandon plan$ $放弃计划$)"}}
                ]
            }

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "sk-test-openai-compatible-key",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=flaky_post,
            sleep=lambda seconds: sleep_calls.append(seconds),
        )

        result = adapter.generate_word("abandon")

        self.assertEqual(result["content"], "(复制专用: $abandon plan$ $放弃计划$)")
        self.assertEqual(len(attempts), 2)
        self.assertEqual(sleep_calls, [1.0])

    def test_does_not_retry_non_retryable_http_error(self) -> None:
        attempts: list[int] = []
        sleep_calls: list[float] = []

        def failing_post(url, payload, headers, timeout_seconds):
            attempts.append(1)
            raise HTTPError(url, 401, "Unauthorized", hdrs=Message(), fp=None)

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "sk-test-openai-compatible-key",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=failing_post,
            sleep=lambda seconds: sleep_calls.append(seconds),
        )

        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            adapter.generate_word("abandon")

        self.assertEqual(len(attempts), 1)
        self.assertEqual(sleep_calls, [])

    def test_uses_openai_compatible_gateway_when_base_url_is_configured(self) -> None:
        recorded_request = {}

        def fake_post(url, payload, headers, timeout_seconds):
            recorded_request["url"] = url
            recorded_request["payload"] = payload
            recorded_request["headers"] = headers
            recorded_request["timeout_seconds"] = timeout_seconds
            return {
                "choices": [
                    {"message": {"content": "(复制专用: $abandon hope$ $放弃希望$)"}}
                ]
            }

        adapter = GeminiGenerationAdapter.from_local_files(
            environ={
                "GEMINI_API_KEY": "sk-test-openai-compatible-key",
                "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
                "COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-flash",
                "COPY_FORMAT_GENERATION_CONFIG_FILE": self._missing_generation_config_path(),
            },
            post_json=fake_post,
        )

        result = adapter.generate_word("abandon")

        self.assertEqual(
            recorded_request["url"],
            "https://api.apifast.tech/v1/chat/completions",
        )
        self.assertEqual(
            recorded_request["headers"]["Authorization"],
            "Bearer sk-test-openai-compatible-key",
        )
        self.assertEqual(
            recorded_request["payload"]["model"],
            "gemini-2.5-flash",
        )
        self.assertEqual(recorded_request["timeout_seconds"], 60.0)
        self.assertEqual(result["content"], "(复制专用: $abandon hope$ $放弃希望$)")

    def test_prefers_environment_model_over_generation_config_file(self) -> None:
        recorded_request = {}

        def fake_post(url, payload, headers, timeout_seconds):
            recorded_request["payload"] = payload
            return {
                "choices": [
                    {"message": {"content": "(复制专用: $abandon hope$ $放弃希望$)"}}
                ]
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "GenerationConfig"
            config_path.write_text(
                json.dumps(
                    {
                        "COPY_FORMAT_GENERATION_API_BASE_URL": "https://api.apifast.tech/v1",
                        "COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-flash",
                    }
                ),
                encoding="utf-8",
            )

            adapter = GeminiGenerationAdapter.from_local_files(
                environ={
                    "GEMINI_API_KEY": "sk-test-openai-compatible-key",
                    "COPY_FORMAT_PROMPT_FILE": self._existing_prompt_path(),
                    "COPY_FORMAT_GENERATION_CONFIG_FILE": str(config_path),
                    "COPY_FORMAT_GEMINI_MODEL": "gemini-2.5-pro",
                },
                post_json=fake_post,
            )

            adapter.generate_word("abandon")

        self.assertEqual(recorded_request["payload"]["model"], "gemini-2.5-pro")


if __name__ == "__main__":
    unittest.main()

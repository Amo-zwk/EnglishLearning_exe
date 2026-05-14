import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.desktop_settings import (
    ANKI_CONNECT_CONFIG_FILE_NAME,
    GENERATION_CONFIG_FILE_NAME,
    KEY_FILE_NAME,
    apply_desktop_environment,
    desktop_config_dir,
    load_desktop_settings,
    save_desktop_settings,
)


class DesktopSettingsTests(unittest.TestCase):
    def test_uses_environment_config_directory_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            resolved_dir = desktop_config_dir({"ENGLISHLEARNING_CONFIG_DIR": temp_dir})

        self.assertEqual(resolved_dir, Path(temp_dir))

    def test_saves_desktop_settings_to_user_config_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = save_desktop_settings(
                {
                    "api_key": "sk-test-openai-compatible-key",
                    "base_url": "https://api.apifast.tech/v1/",
                    "model_name": "gemini-2.5-flash",
                    "anki_connect_url": "http://127.0.0.1:9001",
                },
                config_dir=Path(temp_dir),
            )

            generation_config = json.loads(
                (Path(temp_dir) / GENERATION_CONFIG_FILE_NAME).read_text(
                    encoding="utf-8"
                )
            )
            anki_config = json.loads(
                (Path(temp_dir) / ANKI_CONNECT_CONFIG_FILE_NAME).read_text(
                    encoding="utf-8"
                )
            )

        self.assertTrue(settings.has_api_key)
        self.assertEqual(settings.base_url, "https://api.apifast.tech/v1")
        self.assertEqual(settings.model_name, "gemini-2.5-flash")
        self.assertEqual(
            generation_config["COPY_FORMAT_GENERATION_API_BASE_URL"],
            "https://api.apifast.tech/v1",
        )
        self.assertEqual(anki_config["webBindPort"], 9001)

    def test_keeps_existing_key_when_api_key_field_is_blank(self) -> None:
        with TemporaryDirectory() as temp_dir:
            key_file = Path(temp_dir) / KEY_FILE_NAME
            key_file.write_text("sk-existing-openai-compatible-key\n", encoding="utf-8")

            save_desktop_settings(
                {
                    "api_key": "",
                    "base_url": "",
                    "model_name": "gemini-2.5-pro",
                    "anki_connect_url": "http://127.0.0.1:8765",
                },
                config_dir=Path(temp_dir),
            )

            self.assertEqual(
                key_file.read_text(encoding="utf-8").strip(),
                "sk-existing-openai-compatible-key",
            )

    def test_apply_desktop_environment_points_runtime_to_user_config(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(os.environ, {}, clear=True):
            save_desktop_settings(
                {
                    "api_key": "sk-test-openai-compatible-key",
                    "base_url": "",
                    "model_name": "gemini-2.5-pro",
                    "anki_connect_url": "http://127.0.0.1:8765",
                },
                config_dir=Path(temp_dir),
            )

            settings = apply_desktop_environment(config_dir=Path(temp_dir), port=8010)

            self.assertEqual(os.environ["COPY_FORMAT_DESKTOP_MODE"], "1")
            self.assertEqual(os.environ["COPY_FORMAT_WEB_PORT"], "8010")
            self.assertEqual(
                os.environ["COPY_FORMAT_GEMINI_KEY_FILE"],
                str(settings.paths.key_file),
            )
            self.assertEqual(
                load_desktop_settings(config_dir=Path(temp_dir)).model_name,
                "gemini-2.5-pro",
            )

    def test_rejects_anki_connect_url_without_port(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "端口"):
                save_desktop_settings(
                    {
                        "api_key": "",
                        "base_url": "",
                        "model_name": "gemini-2.5-pro",
                        "anki_connect_url": "http://127.0.0.1",
                    },
                    config_dir=Path(temp_dir),
                )


if __name__ == "__main__":
    unittest.main()

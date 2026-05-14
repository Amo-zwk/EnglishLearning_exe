from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.git_sync_tool import (
    APP_NAME,
    authenticated_remote_url,
    GitSyncConfig,
    default_commit_message,
    filter_sensitive_paths,
    has_builtin_git_backend,
    is_sensitive_repo_path,
    load_config,
    parse_force_include_paths,
    save_config,
)


class GitSyncToolTests(unittest.TestCase):
    def test_sensitive_path_detection_blocks_local_secrets_and_environments(
        self,
    ) -> None:
        self.assertTrue(is_sensitive_repo_path("key"))
        self.assertTrue(is_sensitive_repo_path("AnkiConnect"))
        self.assertTrue(is_sensitive_repo_path("GenerationConfig"))
        self.assertTrue(is_sensitive_repo_path(".env"))
        self.assertTrue(is_sensitive_repo_path("private.pem"))
        self.assertTrue(is_sensitive_repo_path(".venv/Scripts/python.exe"))
        self.assertTrue(is_sensitive_repo_path("node_modules/package/index.js"))
        self.assertTrue(is_sensitive_repo_path("runtime/.venv/pyvenv.cfg"))
        self.assertTrue(is_sensitive_repo_path("config/local/runtime.env"))
        self.assertFalse(is_sensitive_repo_path("config/templates/GenerationConfig.example.json"))
        self.assertFalse(is_sensitive_repo_path("dist/EnglishLearning.exe"))

    def test_filter_sensitive_paths_preserves_only_blocked_paths(self) -> None:
        paths = [
            "README.md",
            "key",
            "src/web_entrypoint.py",
            "runtime/.venv/Scripts/python.exe",
            "node_modules/lib/index.js",
            "dist/EnglishLearning.exe",
        ]

        self.assertEqual(
            filter_sensitive_paths(paths),
            ["key", "runtime/.venv/Scripts/python.exe", "node_modules/lib/index.js"],
        )

    def test_config_roundtrip_uses_plain_json(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            saved = GitSyncConfig(
                repo_path="D:/AnyProject",
                remote_url="https://github.com/example/repo.git",
                branch="release",
                git_path="C:/Program Files/Git/bin/git.exe",
                user_name="Tester",
                user_email="tester@example.com",
                auth_username="tester",
                auth_token="token",
                force_include_paths="dist/app.exe",
                backend="builtin",
            )

            save_config(saved, path=config_path)
            loaded = load_config(path=config_path)

        self.assertEqual(loaded, saved)

    def test_default_commit_message_is_readable(self) -> None:
        message = default_commit_message()

        self.assertIn("Update project", message)
        self.assertGreaterEqual(len(message), 24)

    def test_missing_config_uses_generic_default_shape(self) -> None:
        with TemporaryDirectory() as temp_dir:
            loaded = load_config(path=Path(temp_dir) / "missing.json")

        self.assertEqual(loaded.remote_url, "")
        self.assertEqual(loaded.branch, "main")
        self.assertEqual(loaded.backend, "auto")

    def test_force_include_paths_accepts_newlines_and_semicolons(self) -> None:
        self.assertEqual(
            parse_force_include_paths("dist/app.exe; build/out.zip\nrelease/tool.exe"),
            ["dist/app.exe", "build/out.zip", "release/tool.exe"],
        )

    def test_authenticated_remote_url_masks_setup_to_runtime_only(self) -> None:
        config = GitSyncConfig(
            repo_path="D:/AnyProject",
            remote_url="https://github.com/example/repo.git",
            auth_username="octo",
            auth_token="secret token",
        )

        self.assertEqual(
            authenticated_remote_url(config),
            "https://octo:secret%20token@github.com/example/repo.git",
        )

    def test_app_is_generic_not_project_specific(self) -> None:
        self.assertEqual(APP_NAME, "QuickGitSync")

    def test_builtin_backend_probe_returns_boolean(self) -> None:
        self.assertIsInstance(has_builtin_git_backend(), bool)


if __name__ == "__main__":
    unittest.main()

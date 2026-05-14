import json
import os
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from unittest.mock import patch

from src.desktop_entrypoint import create_desktop_app, render_settings_page
from src.app_metadata import APP_VERSION
from src.desktop_settings import load_desktop_settings


def build_wsgi_environ(
    method: str = "GET",
    path: str = "/desktop/settings",
    body: bytes = b"",
) -> dict[str, object]:
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
        "QUERY_STRING": "",
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8031",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(body),
        "wsgi.errors": __import__("sys").stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }


def call_wsgi_app(app, environ: dict[str, object]):
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app(environ, start_response)).decode("utf-8")
    return captured["status"], captured["headers"], body


class DesktopEntrypointTests(unittest.TestCase):
    def test_settings_route_renders_first_run_configuration_page(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"ENGLISHLEARNING_CONFIG_DIR": temp_dir}, clear=True
        ):
            status, headers, body = call_wsgi_app(
                create_desktop_app(),
                build_wsgi_environ(),
            )

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("EnglishLearning", body)
        self.assertIn('name="api_key"', body)
        self.assertIn('class="setup-steps"', body)
        self.assertIn("配置记录", body)
        self.assertIn('class="setup-step is-current"', body)
        self.assertIn('class="setup-step is-pending"', body)
        self.assertIn('class="setup-step is-neutral"', body)
        self.assertIn("去填写", body)
        self.assertIn("确认模型", body)
        self.assertIn("检测 Anki", body)
        self.assertIn("AI 生成配置", body)
        self.assertIn("Anki 连接", body)
        self.assertIn("待检测", body)
        self.assertIn("确认配置后进入工作台", body)
        self.assertIn("打开诊断", body)
        self.assertIn('href="/desktop/diagnostics"', body)
        self.assertIn('href="/static/desktop.css"', body)
        self.assertIn('src="/static/desktop.js"', body)

    def test_desktop_static_javascript_route_supports_smooth_step_navigation(
        self,
    ) -> None:
        app = create_desktop_app()

        status, headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(path="/static/desktop.js"),
        )

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/javascript; charset=utf-8"), headers)
        self.assertIn("scrollIntoView", body)
        self.assertIn("is-focus-glow", body)
        self.assertIn("initInstantFeedback()", body)
        self.assertIn("is-pressing", body)

    def test_diagnostics_route_renders_environment_overview(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"ENGLISHLEARNING_CONFIG_DIR": temp_dir}, clear=True
        ):
            status, headers, body = call_wsgi_app(
                create_desktop_app(),
                build_wsgi_environ(path="/desktop/diagnostics"),
            )

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("运行诊断", body)
        self.assertIn('class="diagnostics-grid"', body)
        self.assertIn("API Key", body)
        self.assertIn("Prompt 文件", body)
        self.assertIn("AnkiConnect", body)
        self.assertIn("关键路径", body)
        self.assertIn('href="/desktop/settings"', body)
        self.assertIn('href="/"', body)
        self.assertIn('href="/desktop/about"', body)
        self.assertIn("重新诊断", body)

    def test_about_route_renders_final_release_help(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"ENGLISHLEARNING_CONFIG_DIR": temp_dir}, clear=True
        ):
            status, headers, body = call_wsgi_app(
                create_desktop_app(),
                build_wsgi_environ(path="/desktop/about"),
            )

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("正式版信息", body)
        self.assertIn(APP_VERSION, body)
        self.assertIn("正式收官版", body)
        self.assertIn("使用流程", body)
        self.assertIn("常见问题", body)
        self.assertIn("迁移电脑", body)
        self.assertIn('href="/desktop/diagnostics"', body)

    def test_health_route_reports_version(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"ENGLISHLEARNING_CONFIG_DIR": temp_dir}, clear=True
        ):
            status, _headers, body = call_wsgi_app(
                create_desktop_app(),
                build_wsgi_environ(path="/desktop/health"),
            )

        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["version"], APP_VERSION)

    def test_settings_wizard_does_not_mark_model_or_anki_complete_on_first_run(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = load_desktop_settings(config_dir=Path(temp_dir))
            body = render_settings_page(settings)

        self.assertIn('data-status="is-current"', body)
        self.assertIn('data-status="is-pending"', body)
        self.assertIn('data-status="is-neutral"', body)
        self.assertIn('class="setup-step-action setup-step-action-primary"', body)
        self.assertIn('class="setup-step-action setup-step-action-secondary"', body)
        self.assertIn('class="setup-step-action setup-step-action-warning"', body)
        self.assertNotIn("已完成", body)
        self.assertNotIn("已读取 0 个 Deck", body)

    def test_settings_wizard_uses_saved_not_completed_for_existing_records(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "key").write_text("saved-key\n", encoding="utf-8")
            (config_dir / "GenerationConfig").write_text(
                '{"COPY_FORMAT_MODEL": "gemini-2.5-pro"}\n',
                encoding="utf-8",
            )

            body = render_settings_page(load_desktop_settings(config_dir=config_dir))

        self.assertIn('data-status="is-saved"', body)
        self.assertIn("更新密钥", body)
        self.assertIn("调整模型", body)
        self.assertIn("已保存", body)
        self.assertNotIn("已完成", body)

    def test_settings_post_saves_configuration_and_redirects_to_workspace(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"ENGLISHLEARNING_CONFIG_DIR": temp_dir}, clear=True
        ):
            app = create_desktop_app()
            body = urlencode(
                {
                    "api_key": "sk-test-openai-compatible-key",
                    "base_url": "https://api.apifast.tech/v1",
                    "model_name": "gemini-2.5-flash",
                    "anki_connect_url": "http://127.0.0.1:8765",
                }
            ).encode("utf-8")

            status, headers, _body = call_wsgi_app(
                app,
                build_wsgi_environ(
                    method="POST",
                    path="/desktop/settings",
                    body=body,
                ),
            )
            health_status, _health_headers, health_body = call_wsgi_app(
                app,
                build_wsgi_environ(path="/desktop/health"),
            )

        self.assertEqual(status, "303 See Other")
        self.assertIn(("Location", "/"), headers)
        self.assertEqual(health_status, "200 OK")
        self.assertTrue(json.loads(health_body)["configured"])

    def test_settings_post_returns_error_for_invalid_anki_connect_url(self) -> None:
        with TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"ENGLISHLEARNING_CONFIG_DIR": temp_dir}, clear=True
        ):
            body = urlencode(
                {
                    "api_key": "",
                    "base_url": "",
                    "model_name": "gemini-2.5-pro",
                    "anki_connect_url": "127.0.0.1:8765",
                }
            ).encode("utf-8")

            status, _headers, response_body = call_wsgi_app(
                create_desktop_app(),
                build_wsgi_environ(
                    method="POST",
                    path="/desktop/settings",
                    body=body,
                ),
            )

        self.assertEqual(status, "400 Bad Request")
        self.assertIn("AnkiConnect 地址必须", response_body)


if __name__ == "__main__":
    unittest.main()

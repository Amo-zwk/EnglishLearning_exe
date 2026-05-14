from __future__ import annotations

import html
import json
import socket
from socketserver import ThreadingMixIn
import threading
from typing import Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, make_server

from src.app_metadata import APP_NAME, APP_VERSION
from src.desktop_settings import (
    DesktopSettings,
    apply_desktop_environment,
    is_first_run,
    load_desktop_settings,
    save_desktop_settings,
)
from src.anki_submission_gateway import AnkiConnectGateway, AnkiConnectHttpClient
from src.web_entrypoint import DEFAULT_HOST, create_web_app


DESKTOP_WINDOW_TITLE = APP_NAME
SETTINGS_PATH = "/desktop/settings"
DIAGNOSTICS_PATH = "/desktop/diagnostics"
ABOUT_PATH = "/desktop/about"
HEALTH_PATH = "/desktop/health"
DESKTOP_TEST_PORT_ENV = "ENGLISHLEARNING_DESKTOP_PORT"
DESKTOP_HEADLESS_ENV = "ENGLISHLEARNING_DESKTOP_HEADLESS"
SETTINGS_ANKI_TIMEOUT_SECONDS = 0.18


class ThreadingDesktopServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class DesktopApplication:
    def __init__(self) -> None:
        self._workspace_app: Callable | None = None

    def __call__(self, environ, start_response):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))

        if method == "GET" and path == HEALTH_PATH:
            return _json_response(
                start_response,
                {
                    "ok": True,
                    "configured": load_desktop_settings().has_api_key,
                    "version": APP_VERSION,
                },
            )

        if path == SETTINGS_PATH:
            if method == "POST":
                return self._save_settings(environ, start_response)
            return _html_response(
                start_response,
                render_settings_page(
                    load_desktop_settings(),
                    check_anki=_request_checks_anki(environ),
                ),
            )

        if method == "GET" and path == DIAGNOSTICS_PATH:
            return _html_response(
                start_response,
                render_diagnostics_page(load_desktop_settings()),
            )

        if method == "GET" and path == ABOUT_PATH:
            return _html_response(
                start_response,
                render_about_page(load_desktop_settings()),
            )

        return self._workspace(environ, start_response)

    def _workspace(self, environ, start_response):
        if self._workspace_app is None:
            self._workspace_app = create_web_app()
        return self._workspace_app(environ, start_response)

    def _save_settings(self, environ, start_response):
        form_data = _read_form_data(environ)
        try:
            settings = save_desktop_settings(form_data)
            apply_desktop_environment(settings.paths.config_dir)
            self._workspace_app = None
        except ValueError as error:
            current_settings = load_desktop_settings()
            return _html_response(
                start_response,
                render_settings_page(current_settings, error_message=str(error)),
                status="400 Bad Request",
            )

        response_body = b""
        start_response(
            "303 See Other",
            [
                ("Location", "/"),
                ("Content-Length", "0"),
            ],
        )
        return [response_body]


def render_settings_page(
    settings: DesktopSettings,
    error_message: str = "",
    check_anki: bool = False,
) -> str:
    anki_probe = _probe_anki_status(settings, check_anki=check_anki)
    model_configured = settings.paths.generation_config_file.exists()
    key_status = "已保存" if settings.has_api_key else "待填写"
    model_status = "已保存" if model_configured else "待确认"
    key_hint = "留空保持当前密钥" if settings.has_api_key else "首次使用需要填写"
    setup_steps_html = _render_setup_steps(settings, anki_probe)
    recorded_step_count = _count_recorded_setup_steps(settings, anki_probe)
    progress_width = int(recorded_step_count / 3 * 100)
    error_html = (
        f'<div class="settings-banner is-error">{html.escape(error_message)}</div>'
        if error_message
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>EnglishLearning 设置</title>
    <link rel="stylesheet" href="/static/desktop.css">
</head>
<body class="desktop-settings-body">
    <main class="desktop-settings-shell">
        <section class="settings-panel" aria-labelledby="settings-title">
            <div class="settings-heading">
                <p class="settings-kicker">桌面版设置</p>
                <h1 id="settings-title">EnglishLearning</h1>
                <p class="settings-subtitle">按三步完成本机配置，保存后进入工作台。配置会保存在用户目录，方便整包迁移和再次启动。</p>
            </div>
            <section class="settings-progress" aria-label="配置记录">
                <div class="settings-progress-header">
                    <strong>配置记录</strong>
                    <span>已有记录 {recorded_step_count} 项</span>
                </div>
                <div class="settings-progress-track" aria-hidden="true">
                    <span style="width: {progress_width}%"></span>
                </div>
            </section>
            {setup_steps_html}
            {error_html}
            <form method="post" action="/desktop/settings" class="settings-form">
                <section class="settings-section">
                    <div class="settings-section-heading">
                        <h2>AI 生成配置</h2>
                        <p>填写密钥后即可使用本地工作台生成词组解析。</p>
                    </div>
                    <label class="settings-field">
                        <span>API Key</span>
                        <input id="api-key-field" name="api_key" type="password" autocomplete="off" placeholder="{html.escape(key_hint)}">
                    </label>
                    <label class="settings-field">
                        <span>模型接口地址</span>
                        <input id="base-url-field" name="base_url" type="url" value="{html.escape(settings.base_url)}" placeholder="官方 Gemini 可留空">
                    </label>
                    <label class="settings-field">
                        <span>模型名称</span>
                        <input id="model-name-field" name="model_name" type="text" value="{html.escape(settings.model_name)}">
                    </label>
                </section>
                <section class="settings-section">
                    <div class="settings-section-heading">
                        <h2>Anki 连接</h2>
                        <p>保持默认地址即可连接本机 AnkiConnect；换电脑后可在这里重新确认。</p>
                    </div>
                    <div class="settings-inline-status {anki_probe['class']}">
                        <strong>{html.escape(anki_probe['label'])}</strong>
                        <span>{html.escape(anki_probe['detail'])}</span>
                        <a href="/desktop/settings?check_anki=1#anki-connect-field">{html.escape(str(anki_probe['action_label']))}</a>
                    </div>
                    <label class="settings-field">
                        <span>AnkiConnect 地址</span>
                        <input id="anki-connect-field" name="anki_connect_url" type="url" value="{html.escape(settings.anki_connect_url)}" required>
                    </label>
                </section>
                <section class="settings-actions" aria-label="完成配置">
                    <div class="settings-actions-copy">
                        <strong>确认配置后进入工作台</strong>
                        <span>保存会写入本机配置；直接进入不会修改当前内容。</span>
                    </div>
                    <div class="settings-action-buttons">
                        <button type="submit">保存并进入工作台</button>
                        <a href="/desktop/diagnostics" class="settings-secondary-action">打开诊断</a>
                        <a href="/" class="settings-secondary-action">直接进入</a>
                    </div>
                </section>
            </form>
        </section>
        <aside class="settings-status" aria-label="当前状态">
            <div class="status-row">
                <span>密钥</span>
                <strong class="status-badge {'status-badge-success' if settings.has_api_key else 'status-badge-warning'}">{key_status}</strong>
            </div>
            <div class="status-row">
                <span>模型</span>
                <strong class="status-badge {'status-badge-success' if model_configured else 'status-badge-neutral'}">{model_status}</strong>
                <em>{html.escape(settings.model_name)}</em>
            </div>
            <div class="status-row">
                <span>AnkiConnect</span>
                <strong class="status-badge {html.escape(anki_probe['badge_class'])}">{html.escape(anki_probe['label'])}</strong>
                <em>{html.escape(anki_probe['detail'])}</em>
            </div>
            <div class="status-row">
                <span>配置目录</span>
                <strong>{html.escape(str(settings.paths.config_dir))}</strong>
            </div>
            <div class="status-row">
                <span>Prompt</span>
                <strong>{html.escape(settings.paths.prompt_file.name)}</strong>
            </div>
        </aside>
    </main>
    <script src="/static/desktop.js" defer></script>
</body>
</html>"""


def render_diagnostics_page(settings: DesktopSettings) -> str:
    anki_probe = _probe_anki_status(settings, check_anki=True)
    prompt_exists = settings.paths.prompt_file.exists()
    generation_config_exists = settings.paths.generation_config_file.exists()
    anki_config_exists = settings.paths.anki_connect_config_file.exists()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>EnglishLearning 诊断</title>
    <link rel="stylesheet" href="/static/desktop.css">
</head>
<body class="desktop-settings-body">
    <main class="diagnostics-shell">
        <section class="diagnostics-panel" aria-labelledby="diagnostics-title">
            <div class="settings-heading">
                <p class="settings-kicker">运行诊断</p>
                <h1 id="diagnostics-title">EnglishLearning</h1>
                <p class="settings-subtitle">这里汇总当前电脑上的配置、Prompt 和 Anki 连接状态，方便排查移植后的问题。</p>
            </div>
            <div class="diagnostics-grid">
                {_render_diagnostic_card('API Key', '已找到' if settings.has_api_key else '待填写', 'success' if settings.has_api_key else 'warning', '用于连接 AI 生成接口。')}
                {_render_diagnostic_card('模型配置', '已保存' if generation_config_exists else '使用默认值', 'success' if generation_config_exists else 'neutral', settings.model_name)}
                {_render_diagnostic_card('Prompt 文件', '已找到' if prompt_exists else '缺失', 'success' if prompt_exists else 'danger', str(settings.paths.prompt_file))}
                {_render_diagnostic_card('AnkiConnect', str(anki_probe['label']), _diagnostic_tone_from_probe(anki_probe), str(anki_probe['detail']))}
                {_render_diagnostic_card('Anki 配置', '已保存' if anki_config_exists else '使用默认地址', 'success' if anki_config_exists else 'neutral', settings.anki_connect_url)}
                {_render_diagnostic_card('配置目录', '可用', 'success', str(settings.paths.config_dir))}
            </div>
            <section class="diagnostics-paths" aria-label="关键路径">
                <h2>关键路径</h2>
                <dl>
                    <div><dt>配置目录</dt><dd>{html.escape(str(settings.paths.config_dir))}</dd></div>
                    <div><dt>密钥文件</dt><dd>{html.escape(str(settings.paths.key_file))}</dd></div>
                    <div><dt>模型配置</dt><dd>{html.escape(str(settings.paths.generation_config_file))}</dd></div>
                    <div><dt>Anki 配置</dt><dd>{html.escape(str(settings.paths.anki_connect_config_file))}</dd></div>
                    <div><dt>Prompt</dt><dd>{html.escape(str(settings.paths.prompt_file))}</dd></div>
                </dl>
            </section>
            <div class="diagnostics-actions">
                <a href="/desktop/settings" class="settings-secondary-action">返回设置</a>
                <a href="/" class="settings-secondary-action">进入工作台</a>
                <a href="/desktop/about" class="settings-secondary-action">查看关于</a>
                <a href="/desktop/diagnostics" class="settings-secondary-action">重新诊断</a>
            </div>
        </section>
    </main>
    <script src="/static/desktop.js" defer></script>
</body>
</html>"""


def render_about_page(settings: DesktopSettings) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(APP_NAME)} 关于</title>
    <link rel="stylesheet" href="/static/desktop.css">
</head>
<body class="desktop-settings-body">
    <main class="diagnostics-shell about-shell">
        <section class="diagnostics-panel about-panel" aria-labelledby="about-title">
            <div class="settings-heading">
                <p class="settings-kicker">正式版信息</p>
                <h1 id="about-title">{html.escape(APP_NAME)}</h1>
                <p class="settings-subtitle">这是面向 Windows 10/11 的桌面版英语词组制卡软件，核心流程固定为输入、生成、审核、提交到 Anki。</p>
            </div>
            <section class="about-release" aria-label="版本信息">
                <div class="about-version-card">
                    <span>版本</span>
                    <strong>{html.escape(APP_VERSION)}</strong>
                    <em>正式收官版</em>
                </div>
                <div class="about-version-card">
                    <span>运行方式</span>
                    <strong>桌面窗口</strong>
                    <em>内置本地服务和 WebView 窗口</em>
                </div>
                <div class="about-version-card">
                    <span>配置位置</span>
                    <strong>用户目录</strong>
                    <em>{html.escape(str(settings.paths.config_dir))}</em>
                </div>
            </section>
            <section class="about-section" aria-label="使用流程">
                <h2>使用流程</h2>
                <ol class="about-flow-list">
                    <li><strong>1. 配置</strong><span>填写 API Key，确认模型，必要时检测 AnkiConnect。</span></li>
                    <li><strong>2. 制卡</strong><span>在工作台输入单词或导入 txt，生成后勾选真正要提交的词组。</span></li>
                    <li><strong>3. 提交</strong><span>确认 Deck 和提交预览后，将选中词组写入 Anki。</span></li>
                </ol>
            </section>
            <section class="about-help-grid" aria-label="常见问题">
                {_render_about_help_card('首次使用', '先打开设置页填 API Key；官方 Gemini 默认模型可以直接保留。')}
                {_render_about_help_card('Anki 未连接', '先打开 Anki，确认 AnkiConnect 插件已安装并运行，再到诊断页重新检测。')}
                {_render_about_help_card('生成失败', '检查 API Key、模型名称和模型接口地址；如果换过电脑，建议重新保存一次设置。')}
                {_render_about_help_card('迁移电脑', '复制 exe 到新电脑即可启动；首次使用时重新填写本机配置。')}
            </section>
            <section class="diagnostics-paths" aria-label="软件文件">
                <h2>软件文件</h2>
                <dl>
                    <div><dt>配置目录</dt><dd>{html.escape(str(settings.paths.config_dir))}</dd></div>
                    <div><dt>Prompt</dt><dd>{html.escape(str(settings.paths.prompt_file))}</dd></div>
                    <div><dt>模型配置</dt><dd>{html.escape(str(settings.paths.generation_config_file))}</dd></div>
                    <div><dt>Anki 配置</dt><dd>{html.escape(str(settings.paths.anki_connect_config_file))}</dd></div>
                </dl>
            </section>
            <div class="diagnostics-actions">
                <a href="/" class="settings-secondary-action">进入工作台</a>
                <a href="/desktop/settings" class="settings-secondary-action">打开设置</a>
                <a href="/desktop/diagnostics" class="settings-secondary-action">运行诊断</a>
            </div>
        </section>
    </main>
    <script src="/static/desktop.js" defer></script>
</body>
</html>"""


def _render_about_help_card(title: str, detail: str) -> str:
    return (
        '<article class="about-help-card">'
        f"<strong>{html.escape(title)}</strong>"
        f"<p>{html.escape(detail)}</p>"
        "</article>"
    )


def _render_diagnostic_card(
    title: str,
    status: str,
    tone: str,
    detail: str,
) -> str:
    return (
        f'<article class="diagnostic-card diagnostic-card-{html.escape(tone)}">'
        f"<span>{html.escape(title)}</span>"
        f"<strong>{html.escape(status)}</strong>"
        f"<p>{html.escape(detail)}</p>"
        "</article>"
    )


def _diagnostic_tone_from_probe(anki_probe: dict[str, object]) -> str:
    if anki_probe["connected"]:
        return "success"
    if anki_probe["checked"]:
        return "warning"
    return "neutral"


def _render_setup_steps(
    settings: DesktopSettings,
    anki_probe: dict[str, object],
) -> str:
    model_configured = settings.paths.generation_config_file.exists()
    key_step_class = "is-saved" if settings.has_api_key else "is-current"
    model_step_class = "is-saved" if model_configured else "is-pending"
    if not settings.has_api_key and not model_configured:
        model_step_class = "is-pending"
    elif settings.has_api_key and not model_configured:
        model_step_class = "is-current"
    if anki_probe["connected"]:
        anki_step_class = "is-saved"
    elif anki_probe["checked"]:
        anki_step_class = "is-warning"
    else:
        anki_step_class = "is-neutral"
    key_marker = "1"
    model_marker = "2"
    anki_marker = "3"
    key_action = (
        '<a class="setup-step-action setup-step-action-primary" href="#api-key-field">更新密钥</a>'
        if settings.has_api_key
        else '<a class="setup-step-action setup-step-action-primary" href="#api-key-field">去填写</a>'
    )
    model_action = (
        '<a class="setup-step-action setup-step-action-secondary" href="#model-name-field">调整模型</a>'
        if model_configured
        else '<a class="setup-step-action setup-step-action-secondary" href="#model-name-field">确认模型</a>'
    )
    anki_action = (
        '<a class="setup-step-action setup-step-action-secondary" href="/desktop/settings?check_anki=1#anki-connect-field">重新检测</a>'
        if anki_probe["connected"]
        else '<a class="setup-step-action setup-step-action-warning" href="/desktop/settings?check_anki=1#anki-connect-field">检测 Anki</a>'
    )
    return f"""
            <ol class="setup-steps" aria-label="配置向导">
                <li class="setup-step {key_step_class}" data-status="{key_step_class}">
                    <span class="setup-step-number">{key_marker}</span>
                    <span class="setup-step-copy"><strong>填写密钥</strong><em>{'本机已有密钥记录，可按需更新' if settings.has_api_key else '连接 AI 生成接口'}</em></span>
                    <span class="setup-step-status">{'已保存' if settings.has_api_key else '待填写'}</span>
                    {key_action}
                </li>
                <li class="setup-step {model_step_class}" data-status="{model_step_class}">
                    <span class="setup-step-number">{model_marker}</span>
                    <span class="setup-step-copy"><strong>确认模型</strong><em>{html.escape(settings.model_name)}</em></span>
                    <span class="setup-step-status">{'已保存' if model_configured else '待确认'}</span>
                    {model_action}
                </li>
                <li class="setup-step {anki_step_class}" data-status="{anki_step_class}">
                    <span class="setup-step-number">{anki_marker}</span>
                    <span class="setup-step-copy"><strong>连接 Anki</strong><em>{html.escape(str(anki_probe['detail']))}</em></span>
                    <span class="setup-step-status">{html.escape(str(anki_probe['step_status']))}</span>
                    {anki_action}
                </li>
            </ol>"""


def _count_recorded_setup_steps(
    settings: DesktopSettings,
    anki_probe: dict[str, object],
) -> int:
    recorded_steps = 0
    if settings.has_api_key:
        recorded_steps += 1
    if settings.paths.generation_config_file.exists():
        recorded_steps += 1
    if anki_probe["connected"]:
        recorded_steps += 1
    return recorded_steps


def _probe_anki_status(
    settings: DesktopSettings,
    check_anki: bool = False,
) -> dict[str, object]:
    if not check_anki:
        return {
            "checked": False,
            "connected": False,
            "class": "settings-inline-status-neutral",
            "badge_class": "status-badge-neutral",
            "label": "待检测",
            "detail": "点击检测 Anki 后确认连接状态。",
            "step_status": "待检测",
            "action_label": "检测 Anki",
        }

    try:
        deck_names = AnkiConnectGateway(
            AnkiConnectHttpClient(
                base_url=settings.anki_connect_url,
                timeout_seconds=SETTINGS_ANKI_TIMEOUT_SECONDS,
            )
        ).list_deck_names()
    except Exception:
        return {
            "checked": True,
            "connected": False,
            "class": "settings-inline-status-warning",
            "badge_class": "status-badge-warning",
            "label": "未连接",
            "detail": "请先打开 Anki，并确认 AnkiConnect 插件正在运行。",
            "step_status": "未连接",
            "action_label": "重新检测",
        }

    deck_count = len(deck_names)
    deck_label = "暂无 Deck" if deck_count == 0 else f"{deck_count} 个 Deck"
    return {
        "checked": True,
        "connected": True,
        "class": "settings-inline-status-success",
        "badge_class": "status-badge-success",
        "label": "已连接",
        "detail": f"已读取 {deck_label}。",
        "step_status": "已连接",
        "action_label": "重新检测",
    }


def _request_checks_anki(environ) -> bool:
    parsed_query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
    values = parsed_query.get("check_anki", [])
    return any(value in {"1", "true", "yes", "on"} for value in values)


def create_desktop_app() -> DesktopApplication:
    return DesktopApplication()


def run_desktop_app() -> None:
    port = _resolve_desktop_port()
    settings = apply_desktop_environment(port=port)
    app = create_desktop_app()
    start_path = SETTINGS_PATH if is_first_run(settings) else "/"
    url = f"http://{DEFAULT_HOST}:{port}{start_path}"

    with make_server(
        DEFAULT_HOST,
        port,
        app,
        server_class=ThreadingDesktopServer,
    ) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        try:
            _open_desktop_window(url)
        finally:
            httpd.shutdown()


def _open_desktop_window(url: str) -> None:
    if _is_headless_desktop_mode():
        threading.Event().wait()
        return

    try:
        import webview
        webview.create_window(
            DESKTOP_WINDOW_TITLE,
            url,
            width=1280,
            height=860,
            min_size=(1024, 700),
            text_select=True,
        )
        webview.start(gui="edgechromium")
    except Exception as error:
        _show_startup_error(
            "EnglishLearning 无法打开桌面窗口。\n\n"
            "请确认这台电脑已安装 Microsoft Edge WebView2 Runtime。"
            "本程序不需要 Python 环境，但桌面窗口需要 WebView2。\n\n"
            f"错误信息：{error}"
        )


def _show_startup_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, DESKTOP_WINDOW_TITLE, 0x10)
    except Exception:
        print(message)


def _resolve_desktop_port() -> int:
    import os

    configured_port = os.environ.get(DESKTOP_TEST_PORT_ENV, "").strip()
    if configured_port:
        return int(configured_port)
    return _find_available_port()


def _is_headless_desktop_mode() -> bool:
    import os

    value = os.environ.get(DESKTOP_HEADLESS_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


def _read_form_data(environ) -> dict[str, str]:
    content_length_value = str(environ.get("CONTENT_LENGTH", "0") or "0")
    content_length = int(content_length_value) if content_length_value.isdigit() else 0
    raw_body = environ["wsgi.input"].read(content_length)
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _html_response(start_response, html_text: str, status: str = "200 OK"):
    response_body = html_text.encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(response_body))),
        ],
    )
    return [response_body]


def _json_response(start_response, payload: dict[str, object]):
    response_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(response_body))),
        ],
    )
    return [response_body]


def main() -> None:
    run_desktop_app()


if __name__ == "__main__":
    main()

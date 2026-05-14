from __future__ import annotations

from dataclasses import dataclass
from importlib import util
import os
from pathlib import Path
from socketserver import ThreadingMixIn
import sys
import time
from typing import Callable, Protocol, cast
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, make_server

from src.ai_generation_orchestrator import (
    EndpointWordGenerationApi,
    OrchestratedResultGroup,
    orchestrate_generation_requests,
)
from src.anki_submission_gateway import (
    AnkiConnectGateway,
    AnkiConnectHttpClient,
    SubmissionResult,
)
from src.copy_format_contract import ExtractedPhrasePair
from src.gemini_generation_adapter import (
    GeminiGenerationAdapter,
    can_build_local_adapter,
)
from src.review_workspace import ReviewWorkspaceController


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8031
GENERATION_CALLABLE_ENV = "COPY_FORMAT_GENERATION_CALLABLE"
PORT_ENV = "COPY_FORMAT_WEB_PORT"
ANKI_STATUS_TIMEOUT_SECONDS = 0.18
ANKI_STATUS_CACHE_SECONDS = 6.0
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_ASSETS = {
    "/static/app.css": ("text/css; charset=utf-8", STATIC_DIR / "app.css"),
    "/static/desktop.css": ("text/css; charset=utf-8", STATIC_DIR / "desktop.css"),
    "/static/desktop.js": ("text/javascript; charset=utf-8", STATIC_DIR / "desktop.js"),
    "/static/app.js": ("text/javascript; charset=utf-8", STATIC_DIR / "app.js"),
}


GenerationCallable = Callable[[str], object]
ListDecksAction = Callable[[], list[str]]
SubmitAction = Callable[[str, list[ExtractedPhrasePair]], SubmissionResult]
StatusResult = tuple[str, str]
_ANKI_STATUS_CACHE: tuple[float, StatusResult] | None = None


class WorkspaceStateProtocol(Protocol):
    @property
    def input_blocks(self) -> list[object]: ...

    @property
    def result_groups(self) -> list[OrchestratedResultGroup]: ...


class WorkspaceControllerProtocol(Protocol):
    @property
    def state(self) -> WorkspaceStateProtocol: ...

    def add_input_block(self) -> None: ...

    def add_input_blocks(self, count: int) -> None: ...

    def set_input_blocks(self, values: list[str]) -> None: ...

    def set_txt_import_summary(
        self,
        imported_count: int,
        source_name: str = "",
        status_tone: str = "success",
    ) -> None: ...

    def update_input_block(self, index: int, value: str) -> None: ...

    def generate_results(self) -> list[OrchestratedResultGroup]: ...

    def select_deck(self, deck_name: str) -> None: ...

    def edit_phrase(
        self,
        group_index: int,
        phrase_index: int,
        front_value: str | None = None,
        back_value: str | None = None,
    ) -> None: ...

    def set_phrase_selected(
        self,
        group_index: int,
        phrase_index: int,
        selected: bool,
    ) -> None: ...

    def set_phrase_locked(
        self,
        group_index: int,
        phrase_index: int,
        locked: bool,
    ) -> None: ...

    def submit_selected_pairs(self) -> list[object]: ...

    def render_html(self) -> str: ...


class ThreadingWebServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


@dataclass(frozen=True)
class WebAppDependencies:
    generation_callable: GenerationCallable
    list_decks_action: ListDecksAction
    submit_action: SubmitAction
    initial_input_count: int = 2


def demo_generation_endpoint(input_word: str) -> dict[str, str]:
    return {
        "content": (
            f"Full response for {input_word}.\n"
            f"Useful phrase notes for {input_word}.\n"
            f"(复制专用: ${input_word} example phrase$ ${input_word} 示例含义$)\n"
            f"(复制专用: ${input_word} exam phrase$ ${input_word} 考研短语含义$)"
        )
    }


def load_generation_endpoint() -> GenerationCallable:
    configured_target = (
        __import__("os").environ.get(GENERATION_CALLABLE_ENV, "").strip()
    )
    if not configured_target:
        if can_build_local_adapter():
            return GeminiGenerationAdapter.from_local_files().generate_word
        return demo_generation_endpoint
    return _load_callable_from_target(configured_target)


def build_default_dependencies() -> WebAppDependencies:
    gateway = AnkiConnectGateway(AnkiConnectHttpClient())
    return WebAppDependencies(
        generation_callable=load_generation_endpoint(),
        list_decks_action=lambda: _safe_list_decks(gateway),
        submit_action=gateway.submit_phrase_pairs,
    )


def create_workspace_controller(
    dependencies: WebAppDependencies,
) -> ReviewWorkspaceController:
    generation_api = EndpointWordGenerationApi(dependencies.generation_callable)
    return ReviewWorkspaceController(
        generation_action=lambda input_words: orchestrate_generation_requests(
            input_words,
            generation_api,
        ),
        list_decks_action=dependencies.list_decks_action,
        submit_action=cast(SubmitAction, dependencies.submit_action),
        initial_input_count=dependencies.initial_input_count,
    )


def create_web_app(
    controller_factory: Callable[[], WorkspaceControllerProtocol] | None = None,
    dependencies: WebAppDependencies | None = None,
):
    resolved_dependencies = dependencies or build_default_dependencies()
    workspace_controller: WorkspaceControllerProtocol = (
        controller_factory()
        if controller_factory is not None
        else cast(
            WorkspaceControllerProtocol,
            create_workspace_controller(resolved_dependencies),
        )
    )

    def app(environ, start_response):
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))

        if method == "GET" and path in STATIC_ASSETS:
            content_type, asset_path = STATIC_ASSETS[path]
            return _serve_static_asset(start_response, asset_path, content_type)

        if path != "/":
            response_body = "Not Found".encode("utf-8")
            start_response(
                "404 Not Found",
                [
                    ("Content-Type", "text/plain; charset=utf-8"),
                    ("Content-Length", str(len(response_body))),
                ],
            )
            return [response_body]

        if method == "POST":
            form_data = _read_form_data(environ)
            _apply_request_to_workspace(workspace_controller, form_data)

        page = render_page(workspace_controller.render_html())
        response_body = page.encode("utf-8")
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ],
        )
        return [response_body]

    return app


def render_page(workspace_html: str) -> str:
    desktop_settings_link = _render_desktop_settings_link()
    ai_status_class, ai_status_label = _resolve_ai_status()
    anki_status_class, anki_status_label = _resolve_anki_status()
    desktop_mode_chip = _render_desktop_mode_chip()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="个人英语词组制卡工具，生成解析、整理可复制词组，并提交到 Anki。">
    <title>英语词组制卡工作台</title>
    <link rel="stylesheet" href="/static/app.css">
</head>
<body>
    <div class="desktop-app-shell">
        <aside class="desktop-sidebar" aria-label="主导航">
            <a class="desktop-brand" href="/">
                <span class="desktop-brand-mark">EN</span>
                <span class="desktop-brand-copy">
                    <strong>EnglishLearning</strong>
                    <span>本地制卡工作台</span>
                </span>
            </a>
            <nav class="sidebar-nav">
                <a class="sidebar-nav-link sidebar-nav-primary is-active" href="#workspace-input">工作台</a>
                <div class="sidebar-nav-group" aria-label="工作台流程">
                    <span class="sidebar-nav-label">工作台流程</span>
                    <a class="sidebar-nav-link sidebar-nav-sublink" href="#workspace-import">导入</a>
                    <a class="sidebar-nav-link sidebar-nav-sublink" href="#workspace-results">解析结果</a>
                    <a class="sidebar-nav-link sidebar-nav-sublink" href="#workspace-submit">提交预览</a>
                </div>
                {desktop_settings_link}
            </nav>
            <div class="sidebar-help">
                <strong>使用顺序</strong>
                <span>输入单词，生成解析，勾选词组，再提交到 Anki。</span>
            </div>
        </aside>
        <main class="desktop-main">
            <header class="desktop-topbar">
                <section class="page-hero">
                    <div class="page-hero-copy">
                        <span class="eyebrow">个人英语词组卡片台</span>
                        <h1>英语词组制卡工作台</h1>
                        <p class="page-intro">输入单词，审核 AI 解析，整理真正值得加入 Anki 的词组卡片。</p>
                    </div>
                </section>
                <div class="desktop-status-strip" aria-label="运行状态">
                    <span class="status-pill {ai_status_class}">{ai_status_label}</span>
                    <span class="status-pill {anki_status_class}">{anki_status_label}</span>
                    {desktop_mode_chip}
                </div>
            </header>
            <form method="post" enctype="multipart/form-data">
                <div class="generation-pending-banner" data-generation-pending-banner aria-live="polite"><p class="generation-pending-label">生成中</p><p class="generation-pending-text">正在等待 AI 返回结果，请稍候，页面会在完成后自动刷新。</p></div>
                <div class="submission-pending-banner" data-submission-pending-banner aria-live="polite"><p class="submission-pending-label">提交中</p><p class="submission-pending-text">正在提交选中词组到 Anki，请稍候，完成后会在页面顶部显示结果摘要。</p></div>
                <section id="workspace-import" class="top-workbench" aria-label="制卡输入区">
                    <section class="txt-import-panel" data-txt-import-panel>
                        <label for="txt-import-file" class="txt-import-label">导入 txt 文本</label>
                        <div class="txt-import-controls"><input id="txt-import-file" name="txt_import_file" type="file" accept=".txt,text/plain"><button type="submit" name="action" value="import-txt" class="secondary-action">读取 txt</button></div>
                        <p class="txt-import-hint">按每行一条读取，自动去掉首尾空白，空行会跳过，并覆盖当前输入区内容。</p>
                    </section>
                </section>
                {workspace_html}
                <div class="action-bar"><button type="submit" name="action" value="add-input" class="secondary-action">新增输入框</button><button type="submit" name="action" value="add-50-inputs" class="secondary-action">一次加 50 个</button><button type="submit" name="action" value="generate">开始生成</button><button type="submit" name="action" value="submit">提交选中词组</button></div>
            </form>
        </main>
    </div>
    <script src="/static/app.js" defer></script>
</body>
</html>"""


def _render_desktop_settings_link() -> str:
    if not _is_desktop_mode():
        return ""
    return (
        '<div class="sidebar-nav-group" aria-label="软件管理">'
        '<span class="sidebar-nav-label">软件管理</span>'
        '<a class="sidebar-nav-link" href="/desktop/settings">设置</a>'
        '<a class="sidebar-nav-link" href="/desktop/diagnostics">诊断</a>'
        '<a class="sidebar-nav-link" href="/desktop/about">关于</a>'
        "</div>"
    )


def _render_desktop_mode_chip() -> str:
    if not _is_desktop_mode():
        return ""
    return '<span class="status-pill status-neutral">桌面版</span>'


def _is_desktop_mode() -> bool:
    return os.environ.get("COPY_FORMAT_DESKTOP_MODE", "").strip() == "1"


def _resolve_ai_status() -> tuple[str, str]:
    if can_build_local_adapter():
        return "status-success", "AI 已配置"
    return "status-warning", "AI 未配置"


def _resolve_anki_status() -> tuple[str, str]:
    if not _is_desktop_mode():
        return "status-neutral", "AnkiConnect 运行后可读取 Deck"

    global _ANKI_STATUS_CACHE
    current_time = time.monotonic()
    if (
        _ANKI_STATUS_CACHE is not None
        and current_time - _ANKI_STATUS_CACHE[0] < ANKI_STATUS_CACHE_SECONDS
    ):
        return _ANKI_STATUS_CACHE[1]

    gateway = AnkiConnectGateway(
        AnkiConnectHttpClient(timeout_seconds=ANKI_STATUS_TIMEOUT_SECONDS)
    )
    try:
        deck_names = gateway.list_deck_names()
    except Exception:
        result = ("status-warning", "Anki 未连接")
        _ANKI_STATUS_CACHE = (current_time, result)
        return result

    if not deck_names:
        result = ("status-success", "Anki 已连接 · 暂无 Deck")
    else:
        result = ("status-success", f"Anki 已连接 · {len(deck_names)} 个 Deck")
    _ANKI_STATUS_CACHE = (current_time, result)
    return result


def _serve_static_asset(start_response, asset_path: Path, content_type: str):
    if not asset_path.is_file():
        response_body = "Not Found".encode("utf-8")
        start_response(
            "404 Not Found",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ],
        )
        return [response_body]

    response_body = asset_path.read_bytes()
    start_response(
        "200 OK",
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(response_body))),
        ],
    )
    return [response_body]

def run_local_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    app = create_web_app()
    try:
        with make_server(host, port, app, server_class=ThreadingWebServer) as httpd:
            print(f"Serving review workspace on http://{host}:{port}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping review workspace server.")


def main() -> None:
    port_value = __import__("os").environ.get(PORT_ENV, str(DEFAULT_PORT)).strip()
    run_local_server(host=DEFAULT_HOST, port=int(port_value))


def _read_form_data(environ) -> dict[str, str]:
    content_type = str(environ.get("CONTENT_TYPE", "") or "")
    content_length_value = str(environ.get("CONTENT_LENGTH", "0") or "0")
    content_length = int(content_length_value) if content_length_value.isdigit() else 0
    raw_body = environ["wsgi.input"].read(content_length)
    if "multipart/form-data" in content_type:
        return _read_multipart_form_data(environ, raw_body)
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _read_multipart_form_data(environ, raw_body: bytes) -> dict[str, str]:
    content_type = str(environ.get("CONTENT_TYPE", "") or "")
    boundary = _extract_multipart_boundary(content_type)
    if not boundary:
        return {}

    parsed: dict[str, str] = {}
    delimiter = b"--" + boundary.encode("utf-8")
    for part in raw_body.split(delimiter):
        normalized_part = part
        if normalized_part.startswith(b"\r\n"):
            normalized_part = normalized_part[2:]
        if not normalized_part or normalized_part in {b"--", b"--\r\n"}:
            continue

        if normalized_part.endswith(b"\r\n"):
            normalized_part = normalized_part[:-2]
        if normalized_part.endswith(b"--"):
            normalized_part = normalized_part[:-2]

        header_block, separator, content_block = normalized_part.partition(b"\r\n\r\n")
        if not separator:
            continue

        header_lines = header_block.decode("utf-8", errors="replace").split("\r\n")
        headers = _parse_multipart_headers(header_lines)
        disposition = headers.get("content-disposition", "")
        field_name = _extract_disposition_value(disposition, "name")
        if not field_name:
            continue

        content = content_block
        if content.endswith(b"\r\n"):
            content = content[:-2]

        filename = _extract_disposition_value(disposition, "filename")
        if filename:
            parsed[field_name] = content.decode("utf-8-sig", errors="replace")
            parsed[f"{field_name}__filename"] = filename
            continue

        parsed[field_name] = content.decode("utf-8", errors="replace")
    return parsed


def _extract_multipart_boundary(content_type: str) -> str:
    for segment in content_type.split(";"):
        trimmed_segment = segment.strip()
        if trimmed_segment.startswith("boundary="):
            return trimmed_segment.split("=", 1)[1].strip('"')
    return ""


def _parse_multipart_headers(header_lines: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for header_line in header_lines:
        name, separator, value = header_line.partition(":")
        if not separator:
            continue
        headers[name.strip().lower()] = value.strip()
    return headers


def _extract_disposition_value(disposition: str, key: str) -> str:
    for segment in disposition.split(";"):
        trimmed_segment = segment.strip()
        prefix = f"{key}="
        if trimmed_segment.startswith(prefix):
            return trimmed_segment[len(prefix) :].strip('"')
    return ""


def _apply_request_to_workspace(
    workspace: WorkspaceControllerProtocol,
    form_data: dict[str, str],
) -> None:
    _sync_input_blocks(workspace, form_data)

    action = form_data.get("action", "").strip()
    if action == "add-input":
        workspace.add_input_block()
        return

    if action == "add-50-inputs":
        workspace.add_input_blocks(50)
        return

    if action == "import-txt":
        _import_txt_into_workspace(
            workspace,
            form_data.get("txt_import_file", ""),
            form_data.get("txt_import_file__filename", ""),
        )
        return

    if action == "generate":
        workspace.generate_results()
        return

    if action == "submit":
        workspace.select_deck(form_data.get("selected_deck", ""))
        _sync_phrase_edits(workspace, form_data)
        workspace.submit_selected_pairs()
        return


def _sync_input_blocks(
    workspace: WorkspaceControllerProtocol,
    form_data: dict[str, str],
) -> None:
    indexed_fields = sorted(
        (
            int(key.removeprefix("input_word_")),
            value,
        )
        for key, value in form_data.items()
        if key.startswith("input_word_") and key.removeprefix("input_word_").isdigit()
    )
    if not indexed_fields:
        return

    while len(workspace.state.input_blocks) < len(indexed_fields):
        workspace.add_input_block()

    for index, value in indexed_fields:
        workspace.update_input_block(index, value)


def _sync_phrase_edits(
    workspace: WorkspaceControllerProtocol,
    form_data: dict[str, str],
) -> None:
    for group_index, result_group in enumerate(workspace.state.result_groups):
        for phrase_index, _phrase_pair in enumerate(result_group.extracted_phrases):
            front_key = f"phrase_front_{group_index}_{phrase_index}"
            back_key = f"phrase_back_{group_index}_{phrase_index}"
            selected_key = f"phrase_selected_{group_index}_{phrase_index}"
            locked_key = f"phrase_lock_{group_index}_{phrase_index}"

            if front_key in form_data:
                workspace.edit_phrase(
                    group_index=group_index,
                    phrase_index=phrase_index,
                    front_value=form_data[front_key],
                )
            if back_key in form_data:
                workspace.edit_phrase(
                    group_index=group_index,
                    phrase_index=phrase_index,
                    back_value=form_data[back_key],
                )

            workspace.set_phrase_selected(
                group_index=group_index,
                phrase_index=phrase_index,
                selected=selected_key in form_data,
            )
            workspace.set_phrase_locked(
                group_index=group_index,
                phrase_index=phrase_index,
                locked=locked_key in form_data,
            )


def _import_txt_into_workspace(
    workspace: WorkspaceControllerProtocol,
    txt_content: str,
    source_name: str,
) -> None:
    imported_lines = [line.strip() for line in txt_content.splitlines()]
    filtered_lines = [line for line in imported_lines if line]
    if not filtered_lines:
        if hasattr(workspace, "set_txt_import_summary"):
            workspace.set_txt_import_summary(0, source_name, status_tone="empty")
        return
    workspace.set_input_blocks(filtered_lines)
    if hasattr(workspace, "set_txt_import_summary"):
        workspace.set_txt_import_summary(
            len(filtered_lines),
            source_name,
            status_tone="success",
        )


def _load_callable_from_target(target: str) -> GenerationCallable:
    module_path_text, separator, callable_name = target.rpartition(":")
    if not separator or not module_path_text.strip() or not callable_name.strip():
        raise ValueError(
            f"{GENERATION_CALLABLE_ENV} must use '<file-path>:<callable-name>' format."
        )

    module_path = Path(module_path_text).expanduser().resolve()
    module_name = f"copy_format_generation_adapter_{module_path.stem}"
    spec = util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ValueError(
            f"Could not load generation adapter module from {module_path}."
        )

    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    loaded_callable = getattr(module, callable_name)
    if not callable(loaded_callable):
        raise TypeError(
            f"Configured generation adapter '{callable_name}' is not callable."
        )
    return loaded_callable


def _safe_list_decks(gateway: AnkiConnectGateway) -> list[str]:
    try:
        return gateway.list_deck_names()
    except Exception:
        return []


if __name__ == "__main__":
    main()

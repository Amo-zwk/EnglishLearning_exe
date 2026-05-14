import os
import tempfile
import unittest
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from src.ai_generation_orchestrator import OrchestratedResultGroup
from src.anki_submission_gateway import AnkiConnectGateway, SubmissionResult
from src.copy_format_contract import ExtractedPhrasePair
from src.web_entrypoint import (
    WebAppDependencies,
    create_web_app,
    load_generation_endpoint,
)


class RecordingWorkspaceController:
    def __init__(self) -> None:
        self.render_calls = 0
        self.select_deck_calls: list[str] = []
        self.edit_calls: list[tuple[int, int, str | None, str | None]] = []
        self.lock_calls: list[tuple[int, int, bool]] = []
        self.submit_calls = 0
        self.add_input_calls = 0
        self.add_multiple_input_calls: list[int] = []
        self.set_input_blocks_calls: list[list[str]] = []
        self.set_txt_import_summary_calls: list[tuple[int, str, str]] = []
        self.generate_calls = 0
        self.state = RecordingState(
            input_blocks=[object()],
            result_groups=[
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full response",
                    extracted_phrases=[
                        ExtractedPhrasePair(
                            front="deliver keynote",
                            back="做主题演讲",
                        )
                    ],
                )
            ],
        )

    def add_input_block(self) -> None:
        self.add_input_calls += 1
        self.state.input_blocks.append(object())

    def add_input_blocks(self, count: int) -> None:
        self.add_multiple_input_calls.append(count)
        for _ in range(count):
            self.state.input_blocks.append(object())

    def update_input_block(self, index: int, value: str) -> None:
        while len(self.state.input_blocks) <= index:
            self.state.input_blocks.append(object())

    def set_input_blocks(self, values: list[str]) -> None:
        self.set_input_blocks_calls.append(list(values))
        self.state.input_blocks = [object() for _ in values]

    def set_txt_import_summary(
        self,
        imported_count: int,
        source_name: str = "",
        status_tone: str = "success",
    ) -> None:
        self.set_txt_import_summary_calls.append(
            (imported_count, source_name, status_tone)
        )

    def generate_results(self):
        self.generate_calls += 1
        return []

    def select_deck(self, deck_name: str) -> None:
        self.select_deck_calls.append(deck_name)

    def edit_phrase(
        self,
        group_index: int,
        phrase_index: int,
        front_value: str | None = None,
        back_value: str | None = None,
    ) -> None:
        self.edit_calls.append((group_index, phrase_index, front_value, back_value))

    def set_phrase_selected(
        self,
        group_index: int,
        phrase_index: int,
        selected: bool,
    ) -> None:
        self.edit_calls.append((group_index, phrase_index, None, str(selected)))

    def set_phrase_locked(
        self,
        group_index: int,
        phrase_index: int,
        locked: bool,
    ) -> None:
        self.lock_calls.append((group_index, phrase_index, locked))

    def submit_selected_pairs(self):
        self.submit_calls += 1
        return []

    def render_html(self) -> str:
        self.render_calls += 1
        return (
            '<section class="review-workspace">'
            '<button type="submit" name="action" value="generate" class="generate-action">开始生成</button>'
            '<label class="input-block" for="input-word-0"><span>输入单词 1</span>'
            '<textarea id="input-word-0" class="input-word-field">deliver</textarea></label>'
            "</section>"
        )


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def invoke(self, action: str, params=None):
        self.calls.append((action, params))
        if action == "deckNames":
            return ["Default", "English::考研短语"]
        if action == "findNotes":
            return []
        if action == "addNotes":
            notes = cast(dict[str, Any], params)["notes"]
            return [index + 5000 for index, _note in enumerate(notes)]
        raise AssertionError(f"Unexpected action: {action}")


@dataclass
class RecordingState:
    input_blocks: list[object] = field(default_factory=list)
    result_groups: list[OrchestratedResultGroup] = field(default_factory=list)


def build_wsgi_environ(
    method: str = "GET",
    path: str = "/",
    body: bytes = b"",
    content_type: str = "application/x-www-form-urlencoded",
) -> dict[str, object]:
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
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


def call_wsgi_app(
    app, environ: dict[str, object]
) -> tuple[str, list[tuple[str, str]], str]:
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app(environ, start_response)).decode("utf-8")
    return (
        cast(str, captured["status"]),
        cast(list[tuple[str, str]], captured["headers"]),
        body,
    )


class WebEntryRouteTests(unittest.TestCase):
    def test_root_route_returns_html_document_with_workspace_root_and_generate_control(
        self,
    ) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)

        status, headers, body = call_wsgi_app(app, build_wsgi_environ())

        self.assertEqual(status, "200 OK")
        self.assertIn(("Content-Type", "text/html; charset=utf-8"), headers)
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn('class="review-workspace"', body)
        self.assertIn('class="generate-action"', body)
        self.assertIn('<html lang="zh-CN">', body)
        self.assertIn('meta name="description"', body)
        self.assertIn("英语词组制卡工作台", body)
        self.assertIn('class="page-hero"', body)
        self.assertIn('class="desktop-app-shell"', body)
        self.assertIn('class="desktop-sidebar"', body)
        self.assertIn('class="sidebar-nav"', body)
        self.assertIn("工作台流程", body)
        self.assertIn('class="sidebar-nav-link sidebar-nav-sublink"', body)
        self.assertIn('class="desktop-status-strip"', body)
        self.assertIn("AnkiConnect 运行后可读取 Deck", body)
        self.assertIn("个人英语词组卡片台", body)
        self.assertIn('href="/static/app.css"', body)
        self.assertIn('src="/static/app.js"', body)
        self.assertEqual(controller.render_calls, 1)

    def test_static_asset_routes_return_css_and_javascript(self) -> None:
        app = create_web_app(lambda: RecordingWorkspaceController())

        css_status, css_headers, css_body = call_wsgi_app(
            app,
            build_wsgi_environ(path="/static/app.css"),
        )
        js_status, js_headers, js_body = call_wsgi_app(
            app,
            build_wsgi_environ(path="/static/app.js"),
        )

        self.assertEqual(css_status, "200 OK")
        self.assertIn(("Content-Type", "text/css; charset=utf-8"), css_headers)
        self.assertIn(".generate-action.is-pending", css_body)
        self.assertIn(".submission-preview-submit-button.is-pending", css_body)
        self.assertIn(".review-input-shell", css_body)
        self.assertIn(".desktop-app-shell", css_body)
        self.assertIn(".workspace-dashboard", css_body)
        self.assertIn(".workspace-column-header", css_body)
        self.assertIn(".status-pill", css_body)
        self.assertIn(".phrase-fields", css_body)
        self.assertIn(".sidebar-nav-group", css_body)
        self.assertIn(".sidebar-nav-sublink", css_body)
        self.assertIn("scroll-behavior: smooth", css_body)
        self.assertIn(".sidebar-nav-link.is-pressing", css_body)
        self.assertIn(".review-workspace.is-updating", css_body)
        self.assertIn(".review-workspace.is-fresh", css_body)
        self.assertIn("@keyframes workspaceFresh", css_body)
        self.assertEqual(js_status, "200 OK")
        self.assertIn(("Content-Type", "text/javascript; charset=utf-8"), js_headers)
        self.assertIn("refreshCopyExportArea()", js_body)
        self.assertIn("filterDeckOptions(searchInput, select, feedback)", js_body)
        self.assertIn("initDeckSearch()", js_body)
        self.assertIn("initGenerationPendingState()", js_body)
        self.assertIn("initSubmissionPendingState()", js_body)
        self.assertIn('submitter.value !== "generate"', js_body)
        self.assertIn("initTxtDropImport()", js_body)
        self.assertIn('panel.classList.toggle("is-dragging", isDragging)', js_body)
        self.assertIn('fileInput.addEventListener("change", submitImport)', js_body)
        self.assertIn("form.requestSubmit()", js_body)
        self.assertIn('actionInput.value = "import-txt"', js_body)
        self.assertIn("WORKSPACE_DRAFT_STORAGE_KEY", js_body)
        self.assertIn("restoreWorkspaceDraft()", js_body)
        self.assertIn("scheduleWorkspaceDraftSave()", js_body)
        self.assertIn("initAjaxWorkspaceSubmission()", js_body)
        self.assertIn("initSidebarNavigation()", js_body)
        self.assertIn("initInstantFeedback()", js_body)
        self.assertIn("IntersectionObserver", js_body)
        self.assertIn("scrollIntoView", js_body)
        self.assertIn('fetch(form.getAttribute("action") || window.location.href', js_body)
        self.assertIn("replaceWorkspaceFromDocument(responseDocument)", js_body)
        self.assertIn('button.classList.add("is-pending")', js_body)
        self.assertIn('button.setAttribute("aria-disabled", "true")', js_body)
        self.assertIn("生成中...", js_body)
        self.assertIn("提交中...", js_body)
        self.assertIn("当前没有可导出的已勾选词组。", js_body)
        self.assertIn("buildSubmissionPreviewCards(grouped)", js_body)
        self.assertIn("copy-format-export-options", js_body)
        self.assertIn("restoreExportOptions(initialExportContainer)", js_body)
        self.assertIn("saveExportOptions(exportContainer)", js_body)
        self.assertIn('lines.join("\\n")', js_body)
        self.assertNotIn('lines.join("\\\\n")', js_body)

    def test_add_input_action_returns_html_with_additional_input_block(self) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)

        status, _headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(method="POST", body=b"action=add-input"),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(controller.add_input_calls, 1)
        self.assertIn('class="review-workspace"', body)

    def test_add_fifty_inputs_action_returns_html_with_many_additional_input_blocks(
        self,
    ) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)

        status, _headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(method="POST", body=b"action=add-50-inputs"),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(controller.add_multiple_input_calls, [50])
        self.assertIn('class="review-workspace"', body)

    def test_import_txt_action_reads_lines_and_overwrites_input_blocks(self) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)
        boundary = "----BoundaryForTxtImport"
        body = build_multipart_form_data(
            boundary,
            {
                "action": "import-txt",
                "txt_import_file": {
                    "filename": "words.txt",
                    "content_type": "text/plain",
                    "content": "  play football  \n\n on top of\n   take part in   \n",
                },
            },
        )

        status, _headers, html = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST",
                body=body,
                content_type=f"multipart/form-data; boundary={boundary}",
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(
            controller.set_input_blocks_calls,
            [["play football", "on top of", "take part in"]],
        )
        self.assertEqual(
            controller.set_txt_import_summary_calls,
            [(3, "words.txt", "success")],
        )
        self.assertIn('class="review-workspace"', html)

    def test_import_txt_action_reads_utf8_bom_content_without_cgi_module(self) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)
        boundary = "----BoundaryForBomTxtImport"
        body = build_multipart_form_data_bytes(
            boundary,
            {
                "action": b"import-txt",
                "txt_import_file": {
                    "filename": "bom_words.txt",
                    "content_type": "text/plain",
                    "content_bytes": b"\xef\xbb\xbfline one\r\nline two\r\n",
                },
            },
        )

        status, _headers, html = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST",
                body=body,
                content_type=f"multipart/form-data; boundary={boundary}",
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(
            controller.set_input_blocks_calls,
            [["line one", "line two"]],
        )
        self.assertEqual(
            controller.set_txt_import_summary_calls,
            [(2, "bom_words.txt", "success")],
        )
        self.assertIn('class="review-workspace"', html)

    def test_import_txt_action_ignores_empty_file_content(self) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)
        boundary = "----BoundaryForEmptyTxtImport"
        body = build_multipart_form_data(
            boundary,
            {
                "action": "import-txt",
                "txt_import_file": {
                    "filename": "empty.txt",
                    "content_type": "text/plain",
                    "content": "   \n\n  ",
                },
            },
        )

        status, _headers, html = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST",
                body=body,
                content_type=f"multipart/form-data; boundary={boundary}",
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(controller.set_input_blocks_calls, [])
        self.assertEqual(
            controller.set_txt_import_summary_calls,
            [(0, "empty.txt", "empty")],
        )
        self.assertIn('class="review-workspace"', html)


class WebAppFactoryAdapterTests(unittest.TestCase):
    def test_app_factory_uses_configured_generation_callable_through_existing_workspace(
        self,
    ) -> None:
        def generation_endpoint(input_word: str) -> dict[str, str]:
            return {
                "content": (
                    f"Full response for {input_word}.\n"
                    f"(复制专用: ${input_word} phrase$ ${input_word} 含义$)"
                )
            }

        submit_action = lambda deck_name, phrase_pairs: SubmissionResult(
            submitted_count=len(phrase_pairs),
            skipped_count=0,
            failed_count=0,
            submitted_pairs=list(phrase_pairs),
            skipped_pairs=[],
            failed_pairs=[],
        )

        dependencies = WebAppDependencies(
            generation_callable=generation_endpoint,
            list_decks_action=lambda: ["Default"],
            submit_action=submit_action,
        )
        app = create_web_app(dependencies=dependencies)

        status, _headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST", body=b"action=generate&input_word_0=deliver"
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertIn("Full response for deliver.", body)
        self.assertIn("deliver phrase", body)
        self.assertIn("开始生成", body)
        self.assertIn('class="page-intro"', body)

    def test_app_factory_renders_total_and_group_generation_timing(self) -> None:
        def generation_endpoint(input_word: str) -> dict[str, str]:
            return {
                "content": (
                    f"Full response for {input_word}.\n"
                    f"(复制专用: ${input_word} phrase$ ${input_word} 含义$)"
                )
            }

        dependencies = WebAppDependencies(
            generation_callable=generation_endpoint,
            list_decks_action=lambda: ["Default"],
            submit_action=lambda deck_name, phrase_pairs: SubmissionResult(
                submitted_count=len(phrase_pairs),
                skipped_count=0,
                failed_count=0,
                submitted_pairs=list(phrase_pairs),
                skipped_pairs=[],
                failed_pairs=[],
            ),
        )
        app = create_web_app(dependencies=dependencies)

        status, _headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST", body=b"action=generate&input_word_0=deliver"
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertIn("本次生成总耗时", body)
        self.assertIn('class="group-generation-timing"', body)
        self.assertIn("deliver 含义", body)
        self.assertIn("提取结果汇总", body)
        self.assertIn("复制当前格式", body)
        self.assertIn('class="copy-export-area"', body)
        self.assertIn('data-export-format="plain"', body)
        self.assertIn('data-export-format="markdown"', body)
        self.assertIn('data-export-format="anki"', body)
        self.assertIn('data-export-option="trim"', body)
        self.assertIn('data-export-option="dedupe-front"', body)
        self.assertIn('class="full-response-panel"', body)
        self.assertNotIn('class="full-response-panel" open', body)
        self.assertIn('class="full-response-toggle"', body)
        self.assertIn('enctype="multipart/form-data"', body)
        self.assertIn('value="import-txt"', body)
        self.assertIn('name="txt_import_file"', body)
        self.assertIn("data-txt-import-panel", body)
        self.assertIn("导入 txt 文本", body)
        self.assertIn("按每行一条读取", body)
        self.assertIn('value="add-50-inputs"', body)
        self.assertIn("一次加 50 个", body)
        self.assertIn("data-generation-pending-banner", body)
        self.assertIn("data-submission-pending-banner", body)
        self.assertIn("data-deck-search", body)
        self.assertIn("data-deck-selection", body)
        self.assertIn("data-deck-feedback", body)
        self.assertIn('class="submission-preview-submit-button"', body)
        self.assertIn("最终提交预览", body)
        self.assertIn('id="submission-preview-cards"', body)
        self.assertIn('class="phrase-lock-input"', body)
        self.assertIn('name="phrase_lock_0_0"', body)
        self.assertIn('class="review-overview"', body)

    def test_submit_response_includes_top_level_submission_feedback_banner(
        self,
    ) -> None:
        submit_action = lambda deck_name, phrase_pairs: SubmissionResult(
            submitted_count=len(phrase_pairs),
            skipped_count=0,
            failed_count=0,
            submitted_pairs=list(phrase_pairs),
            skipped_pairs=[],
            failed_pairs=[],
        )

        dependencies = WebAppDependencies(
            generation_callable=lambda input_word: {
                "content": (
                    f"Full response for {input_word}.\n"
                    f"(复制专用: ${input_word} phrase$ ${input_word} 含义$)"
                )
            },
            list_decks_action=lambda: ["Default"],
            submit_action=submit_action,
        )
        app = create_web_app(dependencies=dependencies)

        call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST", body=b"action=generate&input_word_0=deliver"
            ),
        )
        status, _headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST",
                body=(
                    b"action=submit&selected_deck=Default"
                    b"&phrase_selected_0_0=true"
                    b"&phrase_front_0_0=deliver+phrase"
                    b"&phrase_back_0_0=deliver+%E5%90%AB%E4%B9%89"
                ),
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertIn("data-submission-feedback-banner", body)
        self.assertIn("已完成提交", body)
        self.assertIn("目标 Deck", body)
        self.assertIn(">Default</strong>", body)
        self.assertIn("本次处理", body)
        self.assertIn(">1 条</strong>", body)
        self.assertIn("已加入", body)
        self.assertIn("重复跳过", body)
        self.assertIn("提交失败", body)
        self.assertIn("本次已加入", body)
        self.assertIn("原因: Written to the selected deck successfully.", body)
        self.assertIn("已自动清空本轮输入和提取结果", body)

    def test_app_factory_renders_generation_failure_message(self) -> None:
        def generation_endpoint(input_word: str) -> dict[str, str]:
            raise RuntimeError("missing Gemini API key")

        dependencies = WebAppDependencies(
            generation_callable=generation_endpoint,
            list_decks_action=lambda: ["Default"],
            submit_action=lambda deck_name, phrase_pairs: SubmissionResult(
                submitted_count=len(phrase_pairs),
                skipped_count=0,
                failed_count=0,
                submitted_pairs=list(phrase_pairs),
                skipped_pairs=[],
                failed_pairs=[],
            ),
        )
        app = create_web_app(dependencies=dependencies)

        status, _headers, body = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST", body=b"action=generate&input_word_0=claim"
            ),
        )

        self.assertEqual(status, "200 OK")
        self.assertIn('class="generation-failure-banner"', body)
        self.assertIn("没有找到 Gemini API Key", body)
        self.assertIn(
            "Generation failed for &#x27;claim&#x27;: missing Gemini API key.", body
        )
        self.assertIn(
            "这次生成没有产出可提交词组，请先根据上面的失败原因检查配置或重试。",
            body,
        )

    def test_load_generation_endpoint_returns_environment_configured_callable_unchanged(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = Path(temp_dir) / "fake_generation_adapter.py"
            module_path.write_text(
                "def test_generation(word):\n"
                "    return {'content': f'Configured response for {word}'}\n",
                encoding="utf-8",
            )
            os.environ["COPY_FORMAT_GENERATION_CALLABLE"] = (
                f"{module_path}:test_generation"
            )

            generation_callable = load_generation_endpoint()

            self.assertEqual(
                generation_callable("abandon"),
                {"content": "Configured response for abandon"},
            )

        os.environ.pop("COPY_FORMAT_GENERATION_CALLABLE", None)


class WebSubmissionRoundtripTests(unittest.TestCase):
    def test_submit_route_forwards_deck_and_reviewed_phrase_edits_unchanged(
        self,
    ) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)

        body = (
            b"action=submit&selected_deck=English%3A%3A%E8%80%83%E7%A0%94%E7%9F%AD%E8%AF%AD"
            b"&phrase_front_0_0=deliver+keynote+unique&phrase_back_0_0=%E5%81%9A%E4%B8%BB%E9%A2%98%E6%BC%94%E8%AE%B2"
        )
        status, _headers, _html = call_wsgi_app(
            app,
            build_wsgi_environ(method="POST", body=body),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(controller.select_deck_calls, ["English::考研短语"])
        self.assertIn((0, 0, "deliver keynote unique", None), controller.edit_calls)
        self.assertIn((0, 0, None, "做主题演讲"), controller.edit_calls)
        self.assertEqual(controller.lock_calls, [(0, 0, False)])
        self.assertEqual(controller.submit_calls, 1)

    def test_submit_route_syncs_phrase_lock_checkbox(self) -> None:
        controller = RecordingWorkspaceController()
        app = create_web_app(lambda: controller)

        body = (
            b"action=submit&selected_deck=English%3A%3A%E8%80%83%E7%A0%94%E7%9F%AD%E8%AF%AD"
            b"&phrase_front_0_0=deliver+keynote&phrase_back_0_0=%E5%81%9A%E4%B8%BB%E9%A2%98%E6%BC%94%E8%AE%B2"
            b"&phrase_selected_0_0=true&phrase_lock_0_0=true"
        )
        status, _headers, _html = call_wsgi_app(
            app,
            build_wsgi_environ(method="POST", body=body),
        )

        self.assertEqual(status, "200 OK")
        self.assertEqual(controller.lock_calls, [(0, 0, True)])

    def test_real_boundaries_complete_generate_to_submit_cycle_on_same_page(
        self,
    ) -> None:
        transport = RecordingTransport()
        gateway = AnkiConnectGateway(transport)
        dependencies = WebAppDependencies(
            generation_callable=lambda input_word: {
                "content": (
                    f"Full response for {input_word}.\n"
                    f"(复制专用: ${input_word} a speech$ ${input_word} 演讲$)"
                )
            },
            list_decks_action=gateway.list_deck_names,
            submit_action=gateway.submit_phrase_pairs,
        )
        app = create_web_app(dependencies=dependencies)

        _generate_status, _headers, generated_body = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST",
                body=b"action=generate&input_word_0=deliver&input_word_1=claim",
            ),
        )
        submit_status, _submit_headers, submitted_body = call_wsgi_app(
            app,
            build_wsgi_environ(
                method="POST",
                body=(
                    b"action=submit&selected_deck=English%3A%3A%E8%80%83%E7%A0%94%E7%9F%AD%E8%AF%AD"
                    b"&input_word_0=deliver&input_word_1=claim"
                    b"&phrase_selected_0_0=true&phrase_selected_1_0=true"
                    b"&phrase_front_0_0=deliver+a+speech&phrase_back_0_0=deliver+%E6%BC%94%E8%AE%B2"
                    b"&phrase_front_1_0=claim+a+speech&phrase_back_1_0=claim+%E6%BC%94%E8%AE%B2"
                ),
            ),
        )

        self.assertIn("Full response for deliver.", generated_body)
        self.assertIn("deliver a speech", generated_body)
        self.assertEqual(submit_status, "200 OK")
        self.assertIn("已完成提交", submitted_body)
        self.assertIn("本次处理", submitted_body)
        self.assertIn(">2 条</strong>", submitted_body)
        self.assertIn("已加入", submitted_body)
        self.assertIn("重复跳过", submitted_body)
        self.assertIn("提交失败", submitted_body)
        self.assertIn("本次已加入", submitted_body)
        self.assertIn(
            "原因: Written to the selected deck successfully.", submitted_body
        )
        self.assertIn("已自动清空本轮输入和提取结果", submitted_body)
        add_notes_calls = [call for call in transport.calls if call[0] == "addNotes"]
        self.assertEqual(len(add_notes_calls), 2)


if __name__ == "__main__":
    unittest.main()


def build_multipart_form_data(
    boundary: str,
    fields: dict[str, object],
) -> bytes:
    normalized_fields: dict[str, object] = {}
    for name, value in fields.items():
        if isinstance(value, dict):
            normalized_fields[name] = value
            continue
        normalized_fields[name] = str(value).encode("utf-8")
    return build_multipart_form_data_bytes(boundary, normalized_fields)


def build_multipart_form_data_bytes(
    boundary: str,
    fields: dict[str, object],
) -> bytes:
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        if isinstance(value, dict):
            filename = cast(str, value["filename"])
            content_type = cast(str, value["content_type"])
            content_bytes = cast(bytes, value.get("content_bytes", b""))
            if not content_bytes:
                content_bytes = cast(str, value["content"]).encode("utf-8")
            parts.append(
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8")
            )
            parts.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            parts.append(content_bytes)
            parts.append(b"\r\n")
            continue
        parts.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        parts.append(cast(bytes, value))
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts)

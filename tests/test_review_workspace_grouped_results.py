import unittest
from unittest.mock import patch

from src.ai_generation_orchestrator import GenerationFailure, OrchestratedResultGroup
from src.anki_submission_gateway import SubmissionResult
from src.copy_format_contract import ExtractedPhrasePair
from src.review_workspace import ReviewWorkspaceController


def no_op_submit_action(
    deck_name: str, phrase_pairs: list[ExtractedPhrasePair]
) -> SubmissionResult:
    return SubmissionResult(
        submitted_count=0,
        skipped_count=0,
        failed_count=0,
        submitted_pairs=[],
        skipped_pairs=[],
        failed_pairs=[],
    )


class ReviewWorkspaceGroupedResultsTests(unittest.TestCase):
    def test_renders_full_response_and_four_editable_phrase_boxes(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full AI response for deliver.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="deliver a speech", back="发表演讲"),
                        ExtractedPhrasePair(front="deliver results", back="取得成果"),
                        ExtractedPhrasePair(front="deliver goods", back="交货"),
                        ExtractedPhrasePair(front="deliver value", back="创造价值"),
                    ],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn("Full AI response for deliver.", html)
        self.assertIn('class="full-response-panel"', html)
        self.assertIn('class="full-response-toggle">完整 AI 响应</summary>', html)
        self.assertIn('class="full-ai-response"', html)
        self.assertIn('class="extracted-review-area"', html)
        self.assertIn('class="review-overview"', html)
        self.assertEqual(html.count('class="phrase-box"'), 4)
        self.assertEqual(html.count('class="phrase-front-input"'), 4)
        self.assertEqual(html.count('class="phrase-back-input"'), 4)
        self.assertIn("min-height: fit-content;", html)
        self.assertIn("overflow: visible;", html)
        self.assertIn("单词：deliver", html)

    def test_renders_empty_extracted_review_area_when_no_pairs_exist(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Explanation only.",
                    extracted_phrases=[],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "claim")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn('class="extracted-review-area"', html)
        self.assertIn(
            "这次生成返回了内容，但没有识别出可提交词组。请展开上方完整 AI 响应，检查复制专用格式是否发生漂移。",
            html,
        )
        self.assertEqual(html.count('class="phrase-box"'), 0)

    def test_renders_plain_empty_message_when_response_is_blank(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="   ",
                    extracted_phrases=[],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "claim")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn("没有可提交的提取词组。", html)

    def test_renders_generation_failure_message_when_request_fails(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="",
                    extracted_phrases=[],
                    failure=GenerationFailure(
                        status="generation-failed",
                        message="Generation failed for 'claim': missing Gemini API key.",
                    ),
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "claim")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn('class="generation-failure-banner"', html)
        self.assertIn("生成失败", html)
        self.assertIn("没有找到 Gemini API Key", html)
        self.assertIn("missing Gemini API key", html)
        self.assertIn(
            "这次生成没有产出可提交词组，请先根据上面的失败原因检查配置或重试。",
            html,
        )
        self.assertNotIn("没有可提交的提取词组。", html)

    def test_sizes_phrase_boxes_to_fit_normal_phrase_lengths_without_truncation(
        self,
    ) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="abandon",
                    full_ai_response="Full AI response.",
                    extracted_phrases=[
                        ExtractedPhrasePair(
                            front="abandon responsibility for the project",
                            back="放弃对项目的责任",
                        )
                    ],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "abandon")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn('rows="2"', html)
        self.assertIn("abandon responsibility for the project", html)
        self.assertIn("放弃对项目的责任", html)

    def test_renders_last_generation_time_after_generate(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="power",
                    full_ai_response="Full AI response for power.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="in power", back="当权")
                    ],
                    generation_duration_seconds=1.234,
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "power")
        with patch(
            "src.review_workspace.time.perf_counter", side_effect=[10.0, 12.3456]
        ):
            workspace.generate_results()

        html = workspace.render_html()

        self.assertIn('class="generation-timing-banner"', html)
        self.assertIn("本次生成总耗时", html)
        self.assertIn("2.346 秒", html)
        self.assertIn('class="group-generation-timing"', html)
        self.assertIn('class="group-generation-timing">1.234 秒</span>', html)

    def test_renders_copy_export_area_with_all_extracted_pairs(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="power",
                    full_ai_response="Full response for power.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="in power", back="当权"),
                        ExtractedPhrasePair(front="come to power", back="上台执政"),
                    ],
                ),
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Full response for claim.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="claim damages", back="索赔")
                    ],
                ),
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "power")
        workspace.update_input_block(1, "claim")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn("提取结果汇总", html)
        self.assertIn("复制当前格式", html)
        self.assertIn('data-export-format="plain"', html)
        self.assertIn('data-export-format="markdown"', html)
        self.assertIn('data-export-format="anki"', html)
        self.assertIn('data-export-option="trim"', html)
        self.assertIn('data-export-option="dedupe-front"', html)
        self.assertIn("[power]", html)
        self.assertIn("in power - 当权", html)
        self.assertIn("come to power - 上台执政", html)
        self.assertIn("[claim]", html)
        self.assertIn("claim damages - 索赔", html)
        self.assertIn("## power", html)
        self.assertIn("- in power: 当权", html)
        self.assertIn("in power\t当权", html)
        self.assertIn('id="copy-export-text-markdown"', html)
        self.assertIn('id="copy-export-text-anki"', html)
        self.assertIn(
            "仅汇总当前勾选的词组，默认会清理首尾空白并按英文词组去重。", html
        )
        self.assertIn("最终提交预览", html)
        self.assertIn(
            "这里展示按当前勾选、去空白和去重规则后，真正会提交到 Anki 的词组集合。",
            html,
        )
        self.assertIn('id="submission-preview-cards"', html)
        self.assertIn('class="submission-preview-submit-button"', html)
        self.assertIn('id="deck-search"', html)
        self.assertIn("data-deck-selection", html)
        self.assertIn("data-deck-feedback", html)
        self.assertIn('class="submission-preview-card-front">in power</p>', html)
        self.assertIn('class="submission-preview-card-back">当权</p>', html)

    def test_full_ai_response_is_collapsed_by_default(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full AI response for deliver.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="deliver a speech", back="发表演讲")
                    ],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn('<details class="full-response-panel">', html)
        self.assertNotIn('<details class="full-response-panel" open>', html)

    def test_copy_export_area_only_includes_selected_phrase_pairs(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="power",
                    full_ai_response="Full response for power.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="in power", back="当权"),
                        ExtractedPhrasePair(front="come to power", back="上台执政"),
                    ],
                ),
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Full response for claim.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="claim damages", back="索赔")
                    ],
                ),
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "power")
        workspace.update_input_block(1, "claim")
        workspace.generate_results()
        workspace.set_phrase_selected(0, 1, False)
        workspace.set_phrase_selected(1, 0, False)

        html = workspace.render_html()

        self.assertIn("[power]", html)
        self.assertIn("in power - 当权", html)
        self.assertNotIn("come to power - 上台执政", html)
        self.assertNotIn("[claim]", html)
        self.assertNotIn("claim damages - 索赔", html)
        self.assertNotIn("come to power\t上台执政", html)

    def test_copy_export_area_trims_whitespace_and_dedupes_by_front(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="power",
                    full_ai_response="Full response for power.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="  in power  ", back=" 当权 "),
                        ExtractedPhrasePair(front="in power", back="当权-重复"),
                    ],
                ),
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Full response for claim.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="   ", back="空白短语"),
                        ExtractedPhrasePair(front="claim damages", back="  索赔  "),
                    ],
                ),
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "power")
        workspace.update_input_block(1, "claim")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertIn("in power - 当权", html)
        self.assertIn("claim damages - 索赔", html)
        self.assertNotIn("in power - 当权-重复", html)
        self.assertNotIn("   - 空白短语", html)
        self.assertNotIn("\t空白短语", html)

    def test_successful_submit_clears_inputs_and_results_but_keeps_top_feedback(
        self,
    ) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full response for deliver.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="deliver a speech", back="发表演讲")
                    ],
                )
            ],
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

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()
        workspace.select_deck("Default")
        workspace.submit_selected_pairs()

        html = workspace.render_html()

        self.assertIn("data-submission-feedback-banner", html)
        self.assertIn("已完成提交", html)
        self.assertIn("目标 Deck", html)
        self.assertIn(">Default</strong>", html)
        self.assertIn("本次处理", html)
        self.assertIn("已加入", html)
        self.assertIn("本次已加入", html)
        self.assertIn("原因: Written to the selected deck successfully.", html)
        self.assertIn("已自动清空本轮输入和提取结果，可以直接开始下一批。", html)
        self.assertNotIn("提取结果汇总", html)
        self.assertNotIn("最终提交预览", html)
        self.assertIn("deliver a speech", html)
        self.assertIn('class="grouped-result-card grouped-results-empty"', html)
        self.assertIn("等待 AI 解析", html)

    def test_failed_submit_keeps_current_results_for_follow_up(self) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Full response for claim.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="claim damages", back="索赔")
                    ],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=lambda deck_name, phrase_pairs: (_ for _ in ()).throw(
                RuntimeError("AnkiConnect offline")
            ),
        )

        workspace.update_input_block(0, "claim")
        workspace.generate_results()
        workspace.select_deck("Default")
        workspace.submit_selected_pairs()

        html = workspace.render_html()

        self.assertIn("data-submission-feedback-banner", html)
        self.assertIn("提交未完成", html)
        self.assertIn("提交失败", html)
        self.assertIn(">1 条</strong>", html)
        self.assertIn("当前内容已保留", html)
        self.assertIn(
            "原因: This item was not written successfully during submission.", html
        )
        self.assertIn("AnkiConnect 未连接", html)
        self.assertIn("AnkiConnect offline", html)
        self.assertIn("提取结果汇总", html)
        self.assertIn("claim damages", html)

    def test_locked_duplicate_replaces_unlocked_duplicate_in_export_and_preview(
        self,
    ) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="power",
                    full_ai_response="Full response for power.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="in power", back="当权"),
                    ],
                ),
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Full response for claim.",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="in power", back="掌权局面"),
                    ],
                ),
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "power")
        workspace.update_input_block(1, "claim")
        workspace.generate_results()
        workspace.set_phrase_locked(1, 0, True)

        export_text = workspace._build_copy_export_text()
        preview_html = workspace._build_submission_preview_cards_html()

        self.assertNotIn("in power - 当权", export_text)
        self.assertIn("in power - 掌权局面", export_text)
        self.assertNotIn('class="submission-preview-card-back">当权</p>', preview_html)
        self.assertIn('class="submission-preview-card-back">掌权局面</p>', preview_html)


if __name__ == "__main__":
    unittest.main()

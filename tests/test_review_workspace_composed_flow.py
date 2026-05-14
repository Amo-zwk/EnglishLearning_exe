import unittest
from typing import Any, cast

from src.ai_generation_orchestrator import (
    EndpointWordGenerationApi,
    OrchestratedResultGroup,
    orchestrate_generation_requests,
)
from src.anki_submission_gateway import (
    AnkiConnectGateway,
    SubmissionOutcomeItem,
    SubmissionResult,
)
from src.copy_format_contract import ExtractedPhrasePair
from src.review_workspace import ReviewWorkspaceController


def no_op_submit_action(
    deck_name: str,
    phrase_pairs: list[ExtractedPhrasePair],
) -> SubmissionResult:
    return SubmissionResult(
        submitted_count=0,
        skipped_count=0,
        failed_count=0,
        submitted_pairs=[],
        skipped_pairs=[],
        failed_pairs=[],
    )


class RecordingTransport:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []

    def invoke(self, action: str, params: object = None):
        self.calls.append((action, params))
        if action == "deckNames":
            return ["Default", "English::考研短语"]
        if action == "findNotes":
            if not isinstance(params, dict):
                raise AssertionError("findNotes params should not be None")
            query = params["query"]
            if 'Front:"deliver keynote"' in query:
                return [101]
            return []
        if action == "addNotes":
            if not isinstance(params, dict):
                raise AssertionError("addNotes params should not be None")
            return [index + 3000 for index, _note in enumerate(params["notes"])]
        raise AssertionError(f"Unexpected action: {action}")


class FlakySubmitAction:
    def __init__(self):
        self.calls = []

    def __call__(self, deck_name: str, phrase_pairs: list[ExtractedPhrasePair]):
        self.calls.append((deck_name, list(phrase_pairs)))
        fronts = [phrase_pair.front for phrase_pair in phrase_pairs]
        if "group two edited" in fronts:
            raise RuntimeError("Simulated gateway failure")
        return SubmissionResult(
            submitted_count=len(phrase_pairs),
            skipped_count=0,
            failed_count=0,
            submitted_pairs=list(phrase_pairs),
            skipped_pairs=[],
            failed_pairs=[],
        )


class RecordingSubmitAction:
    def __init__(self):
        self.calls = []

    def __call__(self, deck_name: str, phrase_pairs: list[ExtractedPhrasePair]):
        self.calls.append((deck_name, list(phrase_pairs)))
        return SubmissionResult(
            submitted_count=len(phrase_pairs),
            skipped_count=0,
            failed_count=0,
            submitted_pairs=list(phrase_pairs),
            skipped_pairs=[],
            failed_pairs=[],
        )


class ReviewWorkspaceComposedFlowTests(unittest.TestCase):
    def test_formats_submitted_skipped_and_failed_counts_in_distinct_buckets(
        self,
    ) -> None:
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [],
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
        )
        workspace.state = workspace.state.__class__(
            input_blocks=workspace.state.input_blocks,
            result_groups=[
                workspace._build_result_group(
                    input_word="deliver",
                    full_ai_response="Full response",
                    extracted_phrases=[
                        workspace._build_phrase_pair("deliver a speech", "发表演讲"),
                        workspace._build_phrase_pair("deliver keynote", "做主题演讲"),
                        workspace._build_phrase_pair("deliver value", "创造价值"),
                    ],
                )
            ],
            available_decks=workspace.state.available_decks,
            selected_deck="Default",
            submission_outcomes=[
                workspace._build_group_submission_outcome(
                    input_word="deliver",
                    result=SubmissionResult(
                        submitted_count=1,
                        skipped_count=1,
                        failed_count=1,
                        submitted_pairs=[
                            workspace._build_phrase_pair("deliver a speech", "发表演讲")
                        ],
                        skipped_pairs=[
                            workspace._build_phrase_pair(
                                "deliver keynote", "做主题演讲"
                            )
                        ],
                        failed_pairs=[
                            workspace._build_phrase_pair("deliver value", "创造价值")
                        ],
                        submitted_items=[
                            SubmissionOutcomeItem(
                                phrase_pair=workspace._build_phrase_pair(
                                    "deliver a speech", "发表演讲"
                                ),
                                reason="Written to the selected deck successfully.",
                            )
                        ],
                        skipped_items=[
                            SubmissionOutcomeItem(
                                phrase_pair=workspace._build_phrase_pair(
                                    "deliver keynote", "做主题演讲"
                                ),
                                reason="Front already exists in Anki, so this item is skipped to avoid duplicates.",
                            )
                        ],
                        failed_items=[
                            SubmissionOutcomeItem(
                                phrase_pair=workspace._build_phrase_pair(
                                    "deliver value", "创造价值"
                                ),
                                reason="AnkiConnect returned an empty note id, so this item was not written successfully.",
                            )
                        ],
                    ),
                )
            ],
            latest_submission_summary=workspace._build_submission_summary(
                "Default",
                [
                    workspace._build_group_submission_outcome(
                        input_word="deliver",
                        result=SubmissionResult(
                            submitted_count=1,
                            skipped_count=1,
                            failed_count=1,
                            submitted_pairs=[
                                workspace._build_phrase_pair(
                                    "deliver a speech", "发表演讲"
                                )
                            ],
                            skipped_pairs=[
                                workspace._build_phrase_pair(
                                    "deliver keynote", "做主题演讲"
                                )
                            ],
                            failed_pairs=[
                                workspace._build_phrase_pair(
                                    "deliver value", "创造价值"
                                )
                            ],
                            submitted_items=[
                                SubmissionOutcomeItem(
                                    phrase_pair=workspace._build_phrase_pair(
                                        "deliver a speech", "发表演讲"
                                    ),
                                    reason="Written to the selected deck successfully.",
                                )
                            ],
                            skipped_items=[
                                SubmissionOutcomeItem(
                                    phrase_pair=workspace._build_phrase_pair(
                                        "deliver keynote", "做主题演讲"
                                    ),
                                    reason="Front already exists in Anki, so this item is skipped to avoid duplicates.",
                                )
                            ],
                            failed_items=[
                                SubmissionOutcomeItem(
                                    phrase_pair=workspace._build_phrase_pair(
                                        "deliver value", "创造价值"
                                    ),
                                    reason="AnkiConnect returned an empty note id, so this item was not written successfully.",
                                )
                            ],
                        ),
                    )
                ],
            ),
        )

        html = workspace.render_html()

        self.assertIn("部分提交成功", html)
        self.assertIn("目标 Deck", html)
        self.assertIn(">Default</strong>", html)
        self.assertIn("本次处理", html)
        self.assertIn("已加入", html)
        self.assertIn("重复跳过", html)
        self.assertIn("提交失败", html)
        self.assertIn("当前内容已保留", html)
        self.assertIn('class="submission-outcome submitted-outcome"', html)
        self.assertIn('class="submission-outcome skipped-outcome"', html)
        self.assertIn('class="submission-outcome failed-outcome"', html)
        self.assertIn(
            'class="submission-outcome-summary submission-outcome-summary-partial"',
            html,
        )
        self.assertIn("本次已加入", html)
        self.assertIn("重复跳过", html)
        self.assertIn("已加入 Anki: 1", html)
        self.assertIn("重复跳过: 1", html)
        self.assertIn("提交失败: 1", html)
        self.assertIn("本组有一部分提交成功，另一部分失败", html)
        self.assertIn(
            "原因: Front already exists in Anki, so this item is skipped to avoid duplicates.",
            html,
        )
        self.assertIn(
            "原因: AnkiConnect returned an empty note id, so this item was not written successfully.",
            html,
        )
        self.assertIn("deliver keynote", html)

    def test_preserves_reviewed_phrase_edits_when_one_group_submission_fails(
        self,
    ) -> None:
        submit_action = FlakySubmitAction()
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [],
            list_decks_action=lambda: ["Default"],
            submit_action=submit_action,
        )
        workspace.state = workspace.state.__class__(
            input_blocks=workspace.state.input_blocks,
            result_groups=[
                workspace._build_result_group(
                    input_word="deliver",
                    full_ai_response="Full response 1",
                    extracted_phrases=[
                        workspace._build_phrase_pair("deliver a speech", "发表演讲")
                    ],
                ),
                workspace._build_result_group(
                    input_word="claim",
                    full_ai_response="Full response 2",
                    extracted_phrases=[
                        workspace._build_phrase_pair("claim damages", "索赔")
                    ],
                ),
            ],
            available_decks=workspace.state.available_decks,
            selected_deck="Default",
        )
        workspace.edit_phrase(
            group_index=0, phrase_index=0, front_value="deliver edited"
        )
        workspace.edit_phrase(
            group_index=1, phrase_index=0, front_value="group two edited"
        )

        workspace.submit_selected_pairs()

        self.assertEqual(
            workspace.state.result_groups[0].extracted_phrases[0].front,
            "deliver edited",
        )
        self.assertEqual(
            workspace.state.result_groups[1].extracted_phrases[0].front,
            "group two edited",
        )
        self.assertEqual(workspace.state.submission_outcomes[0].submitted_count, 1)
        self.assertEqual(workspace.state.submission_outcomes[1].failed_count, 1)
        self.assertIn(
            "group two edited",
            [
                phrase_pair.front
                for phrase_pair in workspace.state.submission_outcomes[1].failed_pairs
            ],
        )

    def test_submits_only_phrase_pairs_selected_by_the_user(self) -> None:
        submit_action = RecordingSubmitAction()
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full response",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="deliver a speech", back="发表演讲"),
                        ExtractedPhrasePair(front="deliver results", back="取得成果"),
                    ],
                )
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=submit_action,
        )

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()
        workspace.select_deck("Default")
        workspace.set_phrase_selected(group_index=0, phrase_index=1, selected=False)

        workspace.submit_selected_pairs()

        self.assertEqual(len(submit_action.calls), 1)
        self.assertEqual(
            [phrase_pair.front for phrase_pair in submit_action.calls[0][1]],
            ["deliver a speech"],
        )

    def test_duplicate_skip_is_visible_in_submission_feedback(self) -> None:
        transport = RecordingTransport()
        gateway = AnkiConnectGateway(transport)
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
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
            list_decks_action=gateway.list_deck_names,
            submit_action=gateway.submit_phrase_pairs,
        )

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()
        workspace.select_deck("English::考研短语")

        workspace.submit_selected_pairs()
        html = workspace.render_html()

        self.assertIn("本次处理", html)
        self.assertIn("重复跳过", html)
        self.assertIn("本次没有新增卡片", html)
        self.assertIn("重复跳过", html)
        self.assertIn(
            "原因: Front already exists in Anki, so this item is skipped to avoid duplicates.",
            html,
        )
        self.assertIn("已自动清空本轮输入和提取结果", html)

    def test_submits_reviewed_group_into_selected_deck_and_renders_feedback(
        self,
    ) -> None:
        transport = RecordingTransport()
        gateway = AnkiConnectGateway(transport)
        api = EndpointWordGenerationApi(
            lambda input_word: {
                "content": (
                    f"Full response for {input_word}.\n"
                    f"(复制专用: ${input_word} a speech$ ${input_word} 演讲$)"
                )
            }
        )
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: orchestrate_generation_requests(
                input_words,
                api,
            ),
            list_decks_action=gateway.list_deck_names,
            submit_action=gateway.submit_phrase_pairs,
        )

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()
        workspace.select_deck("English::考研短语")

        outcomes = workspace.submit_selected_pairs()
        html = workspace.render_html()

        self.assertEqual(outcomes[0].submitted_count, 1)
        self.assertEqual(outcomes[0].skipped_count, 0)
        add_notes_call = next(call for call in transport.calls if call[0] == "addNotes")
        add_notes_params = cast(dict[str, Any], add_notes_call[1])
        self.assertEqual(
            add_notes_params["notes"][0]["deckName"],
            "English::考研短语",
        )
        self.assertIn("本次处理", html)
        self.assertIn("已加入", html)
        self.assertIn("目标 Deck", html)
        self.assertIn(">English::考研短语</strong>", html)
        self.assertIn("本次已加入", html)
        self.assertIn("原因: Written to the selected deck successfully.", html)
        self.assertIn("已自动清空本轮输入和提取结果", html)
        self.assertNotIn("提取结果汇总", html)

    def test_submits_edited_phrase_text_instead_of_original_extracted_value(
        self,
    ) -> None:
        transport = RecordingTransport()
        gateway = AnkiConnectGateway(transport)
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full response",
                    extracted_phrases=[
                        ExtractedPhrasePair(
                            front="deliver a speech",
                            back="发表演讲",
                        )
                    ],
                )
            ],
            list_decks_action=gateway.list_deck_names,
            submit_action=gateway.submit_phrase_pairs,
        )

        workspace.update_input_block(0, "deliver")
        workspace.generate_results()
        workspace.edit_phrase(
            group_index=0,
            phrase_index=0,
            front_value="deliver keynote unique",
        )
        workspace.select_deck("English::考研短语")

        workspace.submit_selected_pairs()

        add_notes_call = next(call for call in transport.calls if call[0] == "addNotes")
        add_notes_params = cast(dict[str, Any], add_notes_call[1])
        self.assertEqual(
            add_notes_params["notes"][0]["fields"]["Front"],
            "deliver keynote unique",
        )

    def test_submit_uses_locked_duplicate_as_final_kept_pair(self) -> None:
        submit_action = RecordingSubmitAction()
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [
                OrchestratedResultGroup(
                    input_word="deliver",
                    full_ai_response="Full response 1",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="shared phrase", back="旧释义")
                    ],
                ),
                OrchestratedResultGroup(
                    input_word="claim",
                    full_ai_response="Full response 2",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="shared phrase", back="新释义")
                    ],
                ),
            ],
            list_decks_action=lambda: ["Default"],
            submit_action=submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "deliver")
        workspace.update_input_block(1, "claim")
        workspace.generate_results()
        workspace.select_deck("Default")
        workspace.set_phrase_locked(group_index=1, phrase_index=0, locked=True)

        outcomes = workspace.submit_selected_pairs()

        self.assertEqual(len(submit_action.calls), 1)
        self.assertEqual(
            [phrase_pair.back for phrase_pair in submit_action.calls[0][1]],
            ["新释义"],
        )
        self.assertEqual(outcomes[0].submitted_count, 0)
        self.assertEqual(outcomes[1].submitted_count, 1)


if __name__ == "__main__":
    unittest.main()

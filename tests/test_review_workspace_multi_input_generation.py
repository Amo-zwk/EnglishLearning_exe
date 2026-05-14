import unittest

from src.ai_generation_orchestrator import OrchestratedResultGroup
from src.anki_submission_gateway import SubmissionResult
from src.copy_format_contract import ExtractedPhrasePair
from src.review_workspace import ReviewWorkspaceController


class RecordingGenerationAction:
    def __init__(self, results):
        self._results = results
        self.calls = []

    def __call__(self, input_words):
        self.calls.append(list(input_words))
        return self._results


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


class ReviewWorkspaceMultiInputGenerationTests(unittest.TestCase):
    def test_renders_grouped_cards_for_two_generated_input_words(self) -> None:
        generation_action = RecordingGenerationAction(
            [
                OrchestratedResultGroup(
                    input_word="abandon",
                    full_ai_response="Response for abandon",
                    extracted_phrases=[
                        ExtractedPhrasePair(front="abandon ship", back="弃船")
                    ],
                    generation_duration_seconds=1.111,
                ),
                OrchestratedResultGroup(
                    input_word="bear",
                    full_ai_response="Response for bear",
                    extracted_phrases=[
                        ExtractedPhrasePair(
                            front="bear responsibility",
                            back="承担责任",
                        )
                    ],
                    generation_duration_seconds=2.222,
                ),
            ]
        )
        workspace = ReviewWorkspaceController(
            generation_action=generation_action,
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "abandon")
        workspace.update_input_block(1, "bear")
        workspace.generate_results()

        html = workspace.render_html()

        self.assertEqual(generation_action.calls, [["abandon", "bear"]])
        self.assertEqual(html.count('class="grouped-result-card"'), 2)
        self.assertIn('data-input-word="abandon"', html)
        self.assertIn('data-input-word="bear"', html)
        self.assertIn("单词：abandon", html)
        self.assertIn("单词：bear", html)
        self.assertIn('class="group-generation-timing">1.111 秒</span>', html)
        self.assertIn('class="group-generation-timing">2.222 秒</span>', html)

    def test_does_not_call_generation_action_during_input_activity(self) -> None:
        generation_action = RecordingGenerationAction([])
        workspace = ReviewWorkspaceController(
            generation_action=generation_action,
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "abandon")
        workspace.add_input_block()
        workspace.update_input_block(2, "claim")

        self.assertEqual(generation_action.calls, [])

    def test_can_add_fifty_input_blocks_without_triggering_generation(self) -> None:
        generation_action = RecordingGenerationAction([])
        workspace = ReviewWorkspaceController(
            generation_action=generation_action,
            list_decks_action=lambda: ["Default"],
            submit_action=no_op_submit_action,
            initial_input_count=2,
        )

        workspace.add_input_blocks(50)

        self.assertEqual(len(workspace.state.input_blocks), 52)
        self.assertEqual(generation_action.calls, [])


if __name__ == "__main__":
    unittest.main()

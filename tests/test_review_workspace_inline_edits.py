import unittest

from src.ai_generation_orchestrator import OrchestratedResultGroup
from src.copy_format_contract import ExtractedPhrasePair
from src.review_workspace import ReviewWorkspaceController


def _build_workspace() -> ReviewWorkspaceController:
    workspace = ReviewWorkspaceController(
        generation_action=lambda input_words: [
            OrchestratedResultGroup(
                input_word="deliver",
                full_ai_response="Full AI response",
                extracted_phrases=[
                    ExtractedPhrasePair(front="deliver a speech", back="发表演讲"),
                    ExtractedPhrasePair(front="deliver results", back="取得成果"),
                ],
            )
        ],
        list_decks_action=lambda: ["Default"],
        submit_action=lambda deck_name, phrase_pairs: None,
    )
    workspace.update_input_block(0, "deliver")
    workspace.generate_results()
    return workspace


class ReviewWorkspaceInlineEditsTests(unittest.TestCase):
    def test_updates_only_the_edited_english_phrase_item(self) -> None:
        workspace = _build_workspace()

        workspace.edit_phrase(
            group_index=0, phrase_index=0, front_value="deliver keynote"
        )

        phrases = workspace.state.result_groups[0].extracted_phrases

        self.assertEqual(phrases[0].front, "deliver keynote")
        self.assertEqual(phrases[0].back, "发表演讲")
        self.assertEqual(
            phrases[1], ExtractedPhrasePair(front="deliver results", back="取得成果")
        )

    def test_updates_only_the_edited_chinese_meaning_item(self) -> None:
        workspace = _build_workspace()

        workspace.edit_phrase(group_index=0, phrase_index=1, back_value="带来成果")

        phrases = workspace.state.result_groups[0].extracted_phrases

        self.assertEqual(
            phrases[0], ExtractedPhrasePair(front="deliver a speech", back="发表演讲")
        )
        self.assertEqual(phrases[1].front, "deliver results")
        self.assertEqual(phrases[1].back, "带来成果")


if __name__ == "__main__":
    unittest.main()

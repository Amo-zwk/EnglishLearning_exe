import unittest

from src.ai_generation_orchestrator import (
    EndpointWordGenerationApi,
    orchestrate_generation_requests,
)
from src.anki_submission_gateway import AnkiConnectGateway
from src.review_workspace import ReviewWorkspaceController


class RecordingTransport:
    def __init__(self):
        self.calls = []

    def invoke(self, action: str, params=None):
        self.calls.append((action, params))
        if action == "deckNames":
            return ["Default", "English::考研短语"]
        if action == "findNotes":
            return []
        if action == "addNotes":
            return [index + 1000 for index, _note in enumerate(params["notes"])]
        raise AssertionError(f"Unexpected action: {action}")


class ReviewWorkspaceDeckSubmissionTests(unittest.TestCase):
    def test_generate_click_uses_real_orchestrator_output_for_grouped_cards(
        self,
    ) -> None:
        api = EndpointWordGenerationApi(
            lambda input_word: {
                "content": (
                    f"Full response for {input_word}.\n"
                    f"(复制专用: ${input_word} phrase 1$ ${input_word} 含义 1$)\n"
                    f"(复制专用: ${input_word} phrase 2$ ${input_word} 含义 2$)"
                )
            }
        )
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: orchestrate_generation_requests(
                input_words,
                api,
            ),
            list_decks_action=lambda: ["Default"],
            submit_action=lambda deck_name, phrase_pairs: None,
            initial_input_count=2,
        )

        workspace.update_input_block(0, "abandon")
        workspace.update_input_block(1, "bear")
        workspace.generate_results()

        groups = workspace.state.result_groups
        html = workspace.render_html()

        self.assertEqual([group.input_word for group in groups], ["abandon", "bear"])
        self.assertEqual([len(group.extracted_phrases) for group in groups], [2, 2])
        self.assertEqual(
            groups[0].full_ai_response.splitlines()[0], "Full response for abandon."
        )
        self.assertIn("Full response for bear.", html)

    def test_passes_selected_deck_value_unchanged_into_submission_request(self) -> None:
        transport = RecordingTransport()
        gateway = AnkiConnectGateway(transport)
        workspace = ReviewWorkspaceController(
            generation_action=lambda input_words: [],
            list_decks_action=gateway.list_deck_names,
            submit_action=gateway.submit_phrase_pairs,
        )

        workspace.select_deck("English::考研短语")
        workspace.state = workspace.state.__class__(
            input_blocks=workspace.state.input_blocks,
            result_groups=[
                workspace._build_result_group(
                    input_word="deliver",
                    full_ai_response="Full response",
                    extracted_phrases=[
                        workspace._build_phrase_pair("deliver results", "取得成果")
                    ],
                )
            ],
            available_decks=workspace.state.available_decks,
            selected_deck=workspace.state.selected_deck,
        )

        workspace.submit_selected_pairs()

        add_notes_call = next(call for call in transport.calls if call[0] == "addNotes")
        self.assertEqual(
            add_notes_call[1]["notes"][0]["deckName"],
            "English::考研短语",
        )


if __name__ == "__main__":
    unittest.main()

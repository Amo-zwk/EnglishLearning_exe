import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError

from src.copy_format_contract import ExtractedPhrasePair
from src.anki_submission_gateway import (
    ANKI_CONNECT_CONFIG_ENV,
    ANKI_CONNECT_URL_ENV,
    AnkiConnectGateway,
    AnkiConnectHttpClient,
    MissingDeckSelectionError,
    build_basic_notes,
    plan_phrase_submission,
    resolve_anki_connect_url,
)


class RecordingTransport:
    def __init__(self, responses_by_action):
        self.responses_by_action = responses_by_action
        self.calls = []

    def invoke(self, action: str, params=None):
        self.calls.append((action, params))
        response = self.responses_by_action[action]

        if callable(response):
            return response(params)

        return response


class AnkiGatewayUnitTests(unittest.TestCase):
    def test_returns_selectable_deck_list_without_altering_names(self) -> None:
        gateway = AnkiConnectGateway(
            RecordingTransport(
                {
                    "deckNames": [
                        "Default",
                        "English::考研短语",
                        "中文 Deck With Space",
                    ],
                }
            )
        )

        deck_names = gateway.list_deck_names()

        self.assertEqual(
            deck_names,
            ["Default", "English::考研短语", "中文 Deck With Space"],
        )

    def test_returns_empty_selectable_deck_list_when_anki_has_no_decks(self) -> None:
        gateway = AnkiConnectGateway(RecordingTransport({"deckNames": []}))

        self.assertEqual(gateway.list_deck_names(), [])

    def test_marks_duplicate_front_as_skipped_before_note_creation(self) -> None:
        phrase_pairs = [
            ExtractedPhrasePair(front="abandon ship", back="弃船"),
            ExtractedPhrasePair(front="bear responsibility", back="承担责任"),
        ]

        plan = plan_phrase_submission(
            phrase_pairs=phrase_pairs,
            existing_fronts={"abandon ship"},
        )

        self.assertEqual(plan.skipped_pairs, [phrase_pairs[0]])
        self.assertEqual(plan.note_candidates, [phrase_pairs[1]])

    def test_marks_all_duplicates_as_skipped_when_every_front_exists(self) -> None:
        phrase_pairs = [
            ExtractedPhrasePair(front="abandon ship", back="弃船"),
            ExtractedPhrasePair(front="bear responsibility", back="承担责任"),
        ]

        plan = plan_phrase_submission(
            phrase_pairs=phrase_pairs,
            existing_fronts={"abandon ship", "bear responsibility"},
        )

        self.assertEqual(plan.skipped_pairs, phrase_pairs)
        self.assertEqual(plan.note_candidates, [])

    def test_builds_basic_notes_with_front_and_back_fields(self) -> None:
        notes = build_basic_notes(
            deck_name="English::考研短语",
            phrase_pairs=[
                ExtractedPhrasePair(front="abandon ship", back="弃船"),
                ExtractedPhrasePair(front="bear responsibility", back="承担责任"),
            ],
        )

        self.assertEqual(
            notes,
            [
                {
                    "deckName": "English::考研短语",
                    "modelName": "Basic",
                    "fields": {"Front": "abandon ship", "Back": "弃船"},
                },
                {
                    "deckName": "English::考研短语",
                    "modelName": "Basic",
                    "fields": {"Front": "bear responsibility", "Back": "承担责任"},
                },
            ],
        )

    def test_requires_explicit_deck_selection_before_note_creation(self) -> None:
        with self.assertRaises(MissingDeckSelectionError):
            build_basic_notes(
                deck_name="",
                phrase_pairs=[ExtractedPhrasePair(front="abandon ship", back="弃船")],
            )

    def test_reports_submitted_skipped_and_failed_counts_separately(self) -> None:
        transport = RecordingTransport(
            {
                "findNotes": lambda params: (
                    [101] if "abandon ship" in params["query"] else []
                ),
                "addNotes": [2001, None],
            }
        )
        gateway = AnkiConnectGateway(transport)

        result = gateway.submit_phrase_pairs(
            deck_name="English::考研短语",
            phrase_pairs=[
                ExtractedPhrasePair(front="abandon ship", back="弃船"),
                ExtractedPhrasePair(front="bear responsibility", back="承担责任"),
                ExtractedPhrasePair(front="claim damages", back="索赔"),
            ],
        )

        self.assertEqual(result.submitted_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.failed_count, 1)


class AnkiGatewayIntegrationTests(unittest.TestCase):
    def test_uses_real_extracted_phrase_shape_to_build_valid_note_payloads(
        self,
    ) -> None:
        phrase_pairs = [
            ExtractedPhrasePair(front="deliver a speech", back="发表演讲"),
            ExtractedPhrasePair(front="deliver results", back="取得成果"),
        ]

        notes = build_basic_notes(deck_name="Default", phrase_pairs=phrase_pairs)

        self.assertEqual(notes[0]["fields"]["Front"], "deliver a speech")
        self.assertEqual(notes[0]["fields"]["Back"], "发表演讲")
        self.assertEqual(notes[1]["fields"]["Front"], "deliver results")
        self.assertEqual(notes[1]["modelName"], "Basic")

    def test_queries_real_deck_names_through_transport_contract(self) -> None:
        transport = RecordingTransport({"deckNames": ["Default", "English::考研短语"]})
        gateway = AnkiConnectGateway(transport)

        deck_names = gateway.list_deck_names()

        self.assertEqual(deck_names, ["Default", "English::考研短语"])
        self.assertEqual(transport.calls, [("deckNames", {})])

    def test_skips_existing_front_instead_of_attempting_add(self) -> None:
        transport = RecordingTransport(
            {
                "findNotes": [999],
                "addNotes": lambda params: self.fail("addNotes should not be called"),
            }
        )
        gateway = AnkiConnectGateway(transport)

        result = gateway.submit_phrase_pairs(
            deck_name="Default",
            phrase_pairs=[
                ExtractedPhrasePair(front="deliver a speech", back="发表演讲")
            ],
        )

        self.assertEqual(result.submitted_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.failed_count, 0)


class AnkiConnectHttpClientTests(unittest.TestCase):
    def test_builds_ankiconnect_request_envelope_for_deck_names(self) -> None:
        recorded_requests = []

        def fake_post(url: str, payload: dict, timeout_seconds: float):
            recorded_requests.append((url, payload, timeout_seconds))
            return {"result": ["Default"], "error": None}

        client = AnkiConnectHttpClient(post_json=fake_post)

        result = client.invoke("deckNames", {})

        self.assertEqual(result, ["Default"])
        self.assertEqual(
            recorded_requests,
            [
                (
                    "http://127.0.0.1:8765",
                    {"action": "deckNames", "version": 6, "params": {}},
                    15.0,
                )
            ],
        )

    def test_wraps_timeout_error_with_actionable_message(self) -> None:
        def fake_post(url: str, payload: dict, timeout_seconds: float):
            raise TimeoutError("timed out")

        client = AnkiConnectHttpClient(post_json=fake_post)

        with self.assertRaisesRegex(RuntimeError, "AnkiConnect request timed out"):
            client.invoke("deckNames", {})

    def test_wraps_connection_error_with_actionable_message(self) -> None:
        def fake_post(url: str, payload: dict, timeout_seconds: float):
            raise URLError("connection refused")

        client = AnkiConnectHttpClient(post_json=fake_post)

        with self.assertRaisesRegex(RuntimeError, "Could not reach AnkiConnect"):
            client.invoke("deckNames", {})

    def test_resolves_anki_connect_url_from_project_config_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "AnkiConnect"
            config_path.write_text(
                '{"webBindAddress":"127.0.0.1","webBindPort":9001}',
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {ANKI_CONNECT_CONFIG_ENV: str(config_path)},
                clear=False,
            ):
                self.assertEqual(
                    resolve_anki_connect_url(),
                    "http://127.0.0.1:9001",
                )

    def test_resolves_anki_connect_url_from_portable_local_config_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config" / "local" / "AnkiConnect"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                '{"webBindAddress":"127.0.0.1","webBindPort":9002}',
                encoding="utf-8",
            )

            with (
                patch.dict("os.environ", {}, clear=True),
                patch(
                    "src.anki_submission_gateway.DEFAULT_LOCAL_ANKI_CONNECT_CONFIG_FILE",
                    config_path,
                ),
            ):
                self.assertEqual(
                    resolve_anki_connect_url(),
                    "http://127.0.0.1:9002",
                )

    def test_prefers_explicit_anki_connect_url_environment_override(self) -> None:
        with patch.dict(
            "os.environ",
            {
                ANKI_CONNECT_URL_ENV: "http://127.0.0.1:9900",
                ANKI_CONNECT_CONFIG_ENV: "/tmp/ignored-AnkiConnect",
            },
            clear=False,
        ):
            self.assertEqual(resolve_anki_connect_url(), "http://127.0.0.1:9900")


if __name__ == "__main__":
    unittest.main()

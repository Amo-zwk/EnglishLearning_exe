from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.error import URLError
from urllib import request

from src.copy_format_contract import ExtractedPhrasePair


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
ANKI_CONNECT_VERSION = 6
ANKI_CONNECT_URL_ENV = "COPY_FORMAT_ANKI_CONNECT_URL"
ANKI_CONNECT_CONFIG_ENV = "COPY_FORMAT_ANKI_CONNECT_CONFIG_FILE"
DEFAULT_ANKI_CONNECT_CONFIG_FILE = "AnkiConnect"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_ANKI_CONNECT_CONFIG_FILE = (
    PROJECT_ROOT / "config" / "local" / "AnkiConnect"
)
DEFAULT_ANKI_CONNECT_TIMEOUT_SECONDS = 15.0


class MissingDeckSelectionError(ValueError):
    pass


class AnkiConnectTransport(Protocol):
    def invoke(self, action: str, params: dict[str, Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class SubmissionPlan:
    skipped_pairs: list[ExtractedPhrasePair] = field(default_factory=list)
    note_candidates: list[ExtractedPhrasePair] = field(default_factory=list)


@dataclass(frozen=True)
class SubmissionOutcomeItem:
    phrase_pair: ExtractedPhrasePair
    reason: str = ""


@dataclass(frozen=True)
class SubmissionResult:
    submitted_count: int
    skipped_count: int
    failed_count: int
    submitted_pairs: list[ExtractedPhrasePair] = field(default_factory=list)
    skipped_pairs: list[ExtractedPhrasePair] = field(default_factory=list)
    failed_pairs: list[ExtractedPhrasePair] = field(default_factory=list)
    submitted_items: list[SubmissionOutcomeItem] = field(default_factory=list)
    skipped_items: list[SubmissionOutcomeItem] = field(default_factory=list)
    failed_items: list[SubmissionOutcomeItem] = field(default_factory=list)


def _require_deck_name(deck_name: str) -> str:
    normalized_deck_name = deck_name.strip()
    if not normalized_deck_name:
        raise MissingDeckSelectionError(
            "A target deck must be selected before creating Anki notes."
        )
    return normalized_deck_name


def _escape_anki_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_front_duplicate_query(front_value: str) -> str:
    escaped_front = _escape_anki_query_value(front_value)
    return f'Front:"{escaped_front}"'


def plan_phrase_submission(
    phrase_pairs: list[ExtractedPhrasePair],
    existing_fronts: set[str],
) -> SubmissionPlan:
    skipped_pairs: list[ExtractedPhrasePair] = []
    note_candidates: list[ExtractedPhrasePair] = []

    for phrase_pair in phrase_pairs:
        if phrase_pair.front in existing_fronts:
            skipped_pairs.append(phrase_pair)
            continue
        note_candidates.append(phrase_pair)

    return SubmissionPlan(
        skipped_pairs=skipped_pairs,
        note_candidates=note_candidates,
    )


def build_basic_notes(
    deck_name: str,
    phrase_pairs: list[ExtractedPhrasePair],
) -> list[dict[str, Any]]:
    selected_deck = _require_deck_name(deck_name)
    return [
        {
            "deckName": selected_deck,
            "modelName": "Basic",
            "fields": {"Front": phrase_pair.front, "Back": phrase_pair.back},
        }
        for phrase_pair in phrase_pairs
    ]


class AnkiConnectHttpClient:
    def __init__(
        self,
        base_url: str | None = None,
        version: int = ANKI_CONNECT_VERSION,
        timeout_seconds: float = DEFAULT_ANKI_CONNECT_TIMEOUT_SECONDS,
        post_json: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None,
    ) -> None:
        self._base_url = base_url or resolve_anki_connect_url()
        self._version = version
        self._timeout_seconds = timeout_seconds
        self._post_json = post_json or self._default_post_json

    def invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "action": action,
            "version": self._version,
            "params": params or {},
        }
        try:
            response = self._post_json(
                self._base_url,
                payload,
                self._timeout_seconds,
            )
        except TimeoutError as error:
            raise RuntimeError(
                "AnkiConnect request timed out. Please confirm Anki and AnkiConnect are running, then retry."
            ) from error
        except URLError as error:
            reason = getattr(error, "reason", None)
            if isinstance(reason, TimeoutError):
                raise RuntimeError(
                    "AnkiConnect request timed out. Please confirm Anki and AnkiConnect are running, then retry."
                ) from error
            raise RuntimeError(
                f"Could not reach AnkiConnect at {self._base_url}. Please confirm Anki and AnkiConnect are running."
            ) from error

        if response.get("error") is not None:
            raise RuntimeError(f"AnkiConnect error for {action}: {response['error']}")

        return response.get("result")

    @staticmethod
    def _default_post_json(
        url: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request_body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(
            http_request,
            timeout=timeout_seconds,
        ) as http_response:
            response_body = http_response.read().decode("utf-8")
        return json.loads(response_body)


def resolve_anki_connect_url() -> str:
    configured_url = os.environ.get(ANKI_CONNECT_URL_ENV, "").strip()
    if configured_url:
        return configured_url

    config_path = _resolve_anki_connect_config_path()

    if not config_path.is_file():
        return ANKI_CONNECT_URL

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ANKI_CONNECT_URL

    if not isinstance(payload, dict):
        return ANKI_CONNECT_URL

    bind_address = payload.get("webBindAddress", "")
    bind_port = payload.get("webBindPort")
    if not isinstance(bind_address, str) or not bind_address.strip():
        return ANKI_CONNECT_URL
    if not isinstance(bind_port, int):
        return ANKI_CONNECT_URL
    return f"http://{bind_address.strip()}:{bind_port}"


def _resolve_anki_connect_config_path() -> Path:
    config_path_text = os.environ.get(ANKI_CONNECT_CONFIG_ENV, "").strip()
    if config_path_text:
        config_path = Path(config_path_text).expanduser()
        if config_path.is_absolute():
            return config_path
        return Path.cwd() / config_path

    if DEFAULT_LOCAL_ANKI_CONNECT_CONFIG_FILE.exists():
        return DEFAULT_LOCAL_ANKI_CONNECT_CONFIG_FILE
    cwd_config_path = Path.cwd() / DEFAULT_ANKI_CONNECT_CONFIG_FILE
    if cwd_config_path.exists():
        return cwd_config_path
    return PROJECT_ROOT / DEFAULT_ANKI_CONNECT_CONFIG_FILE


class AnkiConnectGateway:
    def __init__(self, transport: AnkiConnectTransport) -> None:
        self._transport = transport

    def list_deck_names(self) -> list[str]:
        deck_names = self._transport.invoke("deckNames", {})
        return list(deck_names or [])

    def lookup_existing_fronts(
        self,
        phrase_pairs: list[ExtractedPhrasePair],
    ) -> set[str]:
        existing_fronts: set[str] = set()

        for phrase_pair in phrase_pairs:
            note_ids = self._transport.invoke(
                "findNotes",
                {"query": build_front_duplicate_query(phrase_pair.front)},
            )
            if note_ids:
                existing_fronts.add(phrase_pair.front)

        return existing_fronts

    def submit_phrase_pairs(
        self,
        deck_name: str,
        phrase_pairs: list[ExtractedPhrasePair],
    ) -> SubmissionResult:
        _require_deck_name(deck_name)
        existing_fronts = self.lookup_existing_fronts(phrase_pairs)
        submission_plan = plan_phrase_submission(phrase_pairs, existing_fronts)
        notes = build_basic_notes(deck_name, submission_plan.note_candidates)

        if not notes:
            return SubmissionResult(
                submitted_count=0,
                skipped_count=len(submission_plan.skipped_pairs),
                failed_count=0,
                submitted_pairs=[],
                skipped_pairs=list(submission_plan.skipped_pairs),
                failed_pairs=[],
                skipped_items=[
                    SubmissionOutcomeItem(
                        phrase_pair=phrase_pair,
                        reason="Front already exists in Anki, so this item is skipped to avoid duplicates.",
                    )
                    for phrase_pair in submission_plan.skipped_pairs
                ],
            )

        add_results = self._transport.invoke("addNotes", {"notes": notes}) or []
        submitted_pairs: list[ExtractedPhrasePair] = []
        failed_pairs: list[ExtractedPhrasePair] = []
        submitted_items: list[SubmissionOutcomeItem] = []
        skipped_items = [
            SubmissionOutcomeItem(
                phrase_pair=phrase_pair,
                reason="Front already exists in Anki, so this item is skipped to avoid duplicates.",
            )
            for phrase_pair in submission_plan.skipped_pairs
        ]
        failed_items: list[SubmissionOutcomeItem] = []
        for phrase_pair, note_id in zip(submission_plan.note_candidates, add_results):
            if note_id is None:
                failed_pairs.append(phrase_pair)
                failed_items.append(
                    SubmissionOutcomeItem(
                        phrase_pair=phrase_pair,
                        reason="AnkiConnect returned an empty note id, so this item was not written successfully.",
                    )
                )
            else:
                submitted_pairs.append(phrase_pair)
                submitted_items.append(
                    SubmissionOutcomeItem(
                        phrase_pair=phrase_pair,
                        reason="Written to the selected deck successfully.",
                    )
                )

        if len(add_results) < len(submission_plan.note_candidates):
            for phrase_pair in submission_plan.note_candidates[len(add_results) :]:
                failed_pairs.append(phrase_pair)
                failed_items.append(
                    SubmissionOutcomeItem(
                        phrase_pair=phrase_pair,
                        reason="AnkiConnect returned fewer results than expected, so this item is treated as failed.",
                    )
                )

        submitted_count = len(submitted_pairs)
        failed_count = len(failed_pairs)

        return SubmissionResult(
            submitted_count=submitted_count,
            skipped_count=len(submission_plan.skipped_pairs),
            failed_count=failed_count,
            submitted_pairs=submitted_pairs,
            skipped_pairs=list(submission_plan.skipped_pairs),
            failed_pairs=failed_pairs,
            submitted_items=submitted_items,
            skipped_items=skipped_items,
            failed_items=failed_items,
        )

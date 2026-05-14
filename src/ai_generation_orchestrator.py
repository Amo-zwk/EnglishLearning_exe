from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Protocol

from src.copy_format_contract import (
    ExtractedPhrasePair,
    ExtractionRequest,
    extract_copy_format_phrase_pairs,
)


class WordGenerationApi(Protocol):
    def generate_for_word(self, input_word: str) -> str: ...


@dataclass(frozen=True)
class GenerationFailure:
    status: str
    message: str


@dataclass(frozen=True)
class OrchestratedResultGroup:
    input_word: str
    full_ai_response: str | None = None
    extracted_phrases: list[ExtractedPhrasePair] = field(default_factory=list)
    failure: GenerationFailure | None = None
    generation_duration_seconds: float | None = None


class EndpointWordGenerationApi:
    def __init__(self, endpoint: Callable[[str], Any]) -> None:
        self._endpoint = endpoint

    def generate_for_word(self, input_word: str) -> str:
        payload = self._endpoint(input_word)

        if isinstance(payload, str):
            return payload

        if isinstance(payload, dict):
            content = payload.get("content")
            if isinstance(content, str):
                return content

        raise TypeError(
            "Generation response must be a string or a dict containing string content; retry the request."
        )


def _build_failure(input_word: str, error: Exception) -> OrchestratedResultGroup:
    detail = str(error).strip() or error.__class__.__name__
    return OrchestratedResultGroup(
        input_word=input_word,
        failure=GenerationFailure(
            status="generation-failed",
            message=f"Generation failed for '{input_word}': {detail}. Please retry this word.",
        ),
    )


def _build_success(input_word: str, full_ai_response: str) -> OrchestratedResultGroup:
    extraction_result = extract_copy_format_phrase_pairs(
        ExtractionRequest(input_word=input_word, ai_response=full_ai_response)
    )
    return OrchestratedResultGroup(
        input_word=input_word,
        full_ai_response=full_ai_response,
        extracted_phrases=extraction_result.phrases,
    )


def orchestrate_generation_requests(
    input_words: list[str],
    generation_api: WordGenerationApi,
) -> list[OrchestratedResultGroup]:
    result_groups: list[OrchestratedResultGroup] = []

    for input_word in input_words:
        start_time = time.perf_counter()
        try:
            full_ai_response = generation_api.generate_for_word(input_word)
            result_group = _build_success(input_word, full_ai_response)
        except Exception as error:
            failed_group = _build_failure(input_word, error)
            result_groups.append(
                OrchestratedResultGroup(
                    input_word=failed_group.input_word,
                    full_ai_response=failed_group.full_ai_response,
                    extracted_phrases=failed_group.extracted_phrases,
                    failure=failed_group.failure,
                    generation_duration_seconds=time.perf_counter() - start_time,
                )
            )
            continue

        result_groups.append(
            OrchestratedResultGroup(
                input_word=result_group.input_word,
                full_ai_response=result_group.full_ai_response,
                extracted_phrases=result_group.extracted_phrases,
                failure=result_group.failure,
                generation_duration_seconds=time.perf_counter() - start_time,
            )
        )

    return result_groups

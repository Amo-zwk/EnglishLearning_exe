import unittest
from unittest.mock import patch

from src.ai_generation_orchestrator import (
    EndpointWordGenerationApi,
    orchestrate_generation_requests,
)
from src.copy_format_contract import ExtractedPhrasePair


def require_failure(failure):
    if failure is None:
        raise AssertionError("Expected failure to be present")
    return failure


class MockGenerationApi:
    def __init__(self, responses_by_word):
        self.responses_by_word = responses_by_word

    def generate_for_word(self, input_word: str):
        response = self.responses_by_word[input_word]
        if isinstance(response, Exception):
            raise response
        return response


class AIGenerationOrchestratorUnitTests(unittest.TestCase):
    def test_returns_grouped_results_in_original_input_order(self) -> None:
        api = MockGenerationApi(
            {
                "abandon": "(复制专用: $abandon ship$ $弃船$)",
                "bear": "(复制专用: $bear responsibility$ $承担责任$)",
                "claim": "(复制专用: $claim damages$ $索赔$)",
            }
        )

        result_groups = orchestrate_generation_requests(
            ["abandon", "bear", "claim"],
            api,
        )

        self.assertEqual(
            [group.input_word for group in result_groups],
            ["abandon", "bear", "claim"],
        )
        self.assertEqual(result_groups[0].extracted_phrases[0].front, "abandon ship")
        self.assertEqual(
            result_groups[1].extracted_phrases[0].front, "bear responsibility"
        )
        self.assertEqual(result_groups[2].extracted_phrases[0].front, "claim damages")

    def test_marks_malformed_group_as_failed_without_blocking_other_words(self) -> None:
        api = MockGenerationApi(
            {
                "abandon": "(复制专用: $abandon ship$ $弃船$)",
                "bear": {"unexpected": "payload"},
                "claim": "(复制专用: $claim damages$ $索赔$)",
            }
        )

        result_groups = orchestrate_generation_requests(
            ["abandon", "bear", "claim"],
            api,
        )

        self.assertIsNone(result_groups[0].failure)
        self.assertEqual(result_groups[0].extracted_phrases[0].front, "abandon ship")
        failure = require_failure(result_groups[1].failure)
        self.assertEqual(failure.status, "generation-failed")
        self.assertIn("retry", failure.message.lower())
        self.assertEqual(result_groups[1].extracted_phrases, [])
        self.assertEqual(result_groups[2].extracted_phrases[0].front, "claim damages")

    def test_preserves_dynamic_copy_format_counts_exactly(self) -> None:
        api = MockGenerationApi(
            {
                "abandon": (
                    "(复制专用: $abandon ship$ $弃船$)\n"
                    "(复制专用: $abandon hope$ $放弃希望$)"
                ),
                "bear": "(复制专用: $bear responsibility$ $承担责任$)",
                "claim": "只有解释文本，没有复制专用内容。",
            }
        )

        result_groups = orchestrate_generation_requests(
            ["abandon", "bear", "claim"],
            api,
        )

        self.assertEqual(
            [len(group.extracted_phrases) for group in result_groups], [2, 1, 0]
        )

    def test_preserves_full_explanation_text_while_exposing_only_copy_format_pair(
        self,
    ) -> None:
        full_response = (
            "这个短语常用于正式语境。\n"
            "重点记忆它的固定搭配。\n"
            "deliver a speech 演讲 (复制专用: $deliver a speech$ $发表演讲$)"
        )
        api = MockGenerationApi({"deliver": full_response})

        result_groups = orchestrate_generation_requests(["deliver"], api)

        self.assertEqual(result_groups[0].full_ai_response, full_response)
        self.assertEqual(
            result_groups[0].extracted_phrases,
            [ExtractedPhrasePair(front="deliver a speech", back="发表演讲")],
        )

    def test_records_generation_duration_for_each_word(self) -> None:
        api = MockGenerationApi(
            {
                "abandon": "(复制专用: $abandon ship$ $弃船$)",
                "bear": "(复制专用: $bear responsibility$ $承担责任$)",
            }
        )

        with patch(
            "src.ai_generation_orchestrator.time.perf_counter",
            side_effect=[1.0, 1.25, 3.0, 3.75],
        ):
            result_groups = orchestrate_generation_requests(["abandon", "bear"], api)

        self.assertEqual(result_groups[0].generation_duration_seconds, 0.25)
        self.assertEqual(result_groups[1].generation_duration_seconds, 0.75)


class AIGenerationOrchestratorIntegrationTests(unittest.TestCase):
    def test_uses_real_extraction_contract_without_manual_reshaping(self) -> None:
        api = MockGenerationApi(
            {
                "deliver": (
                    "说明文本\n"
                    "(复制专用: $deliver a speech$ $发表演讲$)\n"
                    "(复制专用: $deliver results$ $取得成果$)"
                )
            }
        )

        result_group = orchestrate_generation_requests(["deliver"], api)[0]

        self.assertEqual(
            result_group.extracted_phrases,
            [
                ExtractedPhrasePair(front="deliver a speech", back="发表演讲"),
                ExtractedPhrasePair(front="deliver results", back="取得成果"),
            ],
        )

    def test_endpoint_adapter_reports_only_failed_word_when_request_raises(
        self,
    ) -> None:
        def endpoint(input_word: str):
            if input_word == "bear":
                raise RuntimeError("temporary API timeout")

            return {"content": f"(复制专用: ${input_word} phrase$ ${input_word} 含义$)"}

        api = EndpointWordGenerationApi(endpoint)

        result_groups = orchestrate_generation_requests(
            ["abandon", "bear", "claim"],
            api,
        )

        self.assertEqual(result_groups[0].extracted_phrases[0].front, "abandon phrase")
        failure = require_failure(result_groups[1].failure)
        self.assertEqual(failure.status, "generation-failed")
        self.assertIn("temporary API timeout", failure.message)
        self.assertEqual(result_groups[2].extracted_phrases[0].front, "claim phrase")


if __name__ == "__main__":
    unittest.main()

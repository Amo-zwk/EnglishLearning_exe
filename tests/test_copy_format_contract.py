import unittest

from src.copy_format_contract import (
    ExtractionRequest,
    extract_copy_format_phrase_pairs,
    make_front_dedupe_key,
)


class CopyFormatExtractionContractTests(unittest.TestCase):
    def test_extracts_two_valid_segments_and_preserves_input_word(self) -> None:
        request = ExtractionRequest(
            input_word="abandon",
            ai_response=(
                "解析内容。\n"
                "常见搭配 放弃计划 (复制专用: $abandon the plan$ $放弃计划$)\n"
                "常见搭配 放弃希望 (复制专用: $abandon hope$ $放弃希望$)"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(result.input_word, "abandon")
        self.assertEqual(len(result.phrases), 2)
        self.assertEqual(result.phrases[0].front, "abandon the plan")
        self.assertEqual(result.phrases[0].back, "放弃计划")
        self.assertEqual(result.phrases[1].front, "abandon hope")
        self.assertEqual(result.phrases[1].back, "放弃希望")

    def test_rejects_segment_missing_chinese_and_keeps_other_valid_segments(
        self,
    ) -> None:
        request = ExtractionRequest(
            input_word="bear",
            ai_response=(
                "(复制专用: $bear responsibility$ $承担责任$)\n"
                "(复制专用: $bear in mind$ $   $)\n"
                "(复制专用: $bear hardship$ $忍受苦难$)"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(
            [phrase.front for phrase in result.phrases],
            ["bear responsibility", "bear hardship"],
        )
        self.assertEqual(
            [phrase.back for phrase in result.phrases], ["承担责任", "忍受苦难"]
        )

    def test_returns_empty_phrase_list_when_no_valid_copy_format_segments_exist(
        self,
    ) -> None:
        request = ExtractionRequest(
            input_word="claim",
            ai_response="这里是解释文本，没有复制专用内容，只有含义说明。",
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(result.input_word, "claim")
        self.assertEqual(result.phrases, [])

    def test_ignores_explanation_text_and_keeps_only_copy_format_pair(self) -> None:
        request = ExtractionRequest(
            input_word="deliver",
            ai_response=(
                "这个短语常用于正式语境。\n"
                "重点记忆它的固定搭配。\n"
                "deliver a speech 演讲 (复制专用: $deliver a speech$ $发表演讲$)"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(len(result.phrases), 1)
        self.assertEqual(result.phrases[0].front, "deliver a speech")
        self.assertEqual(result.phrases[0].back, "发表演讲")

    def test_accepts_copy_format_with_chinese_colon(self) -> None:
        request = ExtractionRequest(
            input_word="on top of",
            ai_response=(
                "on top of the cost 除成本之外 "
                "(复制专用：$on top of the cost$ $除成本之外$)\n"
                "stay on top of sth. 掌控某事的进度 "
                "(复制专用：$stay on top of sth.$ $掌控某事的进度$)"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(result.input_word, "on top of")
        self.assertEqual(
            [phrase.front for phrase in result.phrases],
            ["on top of the cost", "stay on top of sth."],
        )
        self.assertEqual(
            [phrase.back for phrase in result.phrases],
            ["除成本之外", "掌控某事的进度"],
        )

    def test_accepts_copy_format_with_chinese_parentheses(self) -> None:
        request = ExtractionRequest(
            input_word="favor",
            ai_response=(
                "帮个忙 （复制专用：$do sb a favor$ $帮某人一个忙$）\n"
                "回报别人 （复制专用：$return the favor$ $回报别人的人情$）"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(result.input_word, "favor")
        self.assertEqual(
            [phrase.front for phrase in result.phrases],
            ["do sb a favor", "return the favor"],
        )
        self.assertEqual(
            [phrase.back for phrase in result.phrases],
            ["帮某人一个忙", "回报别人的人情"],
        )

    def test_accepts_three_segment_copy_format_by_joining_front_parts(self) -> None:
        request = ExtractionRequest(
            input_word="oppose",
            ai_response=(
                "强调程度时常这样表达。\n"
                "(复制专用: $militantly$ $oppose$ $激进地反对$)\n"
                "(复制专用：$strongly$ $support$ $强烈支持$)"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(result.input_word, "oppose")
        self.assertEqual(
            [phrase.front for phrase in result.phrases],
            ["militantly oppose", "strongly support"],
        )
        self.assertEqual(
            [phrase.back for phrase in result.phrases],
            ["激进地反对", "强烈支持"],
        )

    def test_rejects_copy_format_with_unsupported_segment_count(self) -> None:
        request = ExtractionRequest(
            input_word="break",
            ai_response=(
                "(复制专用: $break$ $it$ $down$ $分解它$)\n"
                "(复制专用: $break down$ $出故障$)"
            ),
        )

        result = extract_copy_format_phrase_pairs(request)

        self.assertEqual(len(result.phrases), 1)
        self.assertEqual(result.phrases[0].front, "break down")
        self.assertEqual(result.phrases[0].back, "出故障")

    def test_dedupe_key_normalizes_surrounding_whitespace_only(self) -> None:
        self.assertEqual(
            make_front_dedupe_key(" deliver a speech "),
            make_front_dedupe_key("deliver a speech"),
        )


if __name__ == "__main__":
    unittest.main()

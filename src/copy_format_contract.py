from __future__ import annotations

from dataclasses import dataclass, field
import re


COPY_FORMAT_PATTERN = re.compile(r"[\(（]复制专用[:：](?P<body>.*?)[\)）]")
COPY_FORMAT_SEGMENT_PATTERN = re.compile(r"\$([^$]+)\$")


@dataclass(frozen=True)
class ExtractionRequest:
    input_word: str
    ai_response: str


@dataclass(frozen=True)
class ExtractedPhrasePair:
    front: str
    back: str


@dataclass(frozen=True)
class ExtractionResult:
    input_word: str
    phrases: list[ExtractedPhrasePair] = field(default_factory=list)


def make_front_dedupe_key(front_value: str) -> str:
    return front_value.strip()


def extract_copy_format_phrase_pairs(request: ExtractionRequest) -> ExtractionResult:
    phrases: list[ExtractedPhrasePair] = []

    for match in COPY_FORMAT_PATTERN.finditer(request.ai_response):
        segments = [
            segment.strip()
            for segment in COPY_FORMAT_SEGMENT_PATTERN.findall(match.group("body"))
        ]
        if len(segments) == 2:
            front = make_front_dedupe_key(segments[0])
            back = segments[1]
        elif len(segments) == 3:
            front = make_front_dedupe_key(f"{segments[0]} {segments[1]}")
            back = segments[2]
        else:
            continue

        if not front or not back:
            continue
        phrases.append(ExtractedPhrasePair(front=front, back=back))

    return ExtractionResult(input_word=request.input_word, phrases=phrases)

# Scenario: AI Generation And Extraction Orchestrator
- Given: A page submits multiple input words to the orchestrator through an injectable generation API service
- When: Some words succeed, some responses have dynamic copy-format counts, some responses contain explanation text only, or one request fails or returns malformed data
- Then: The orchestrator returns one ordered result group per input word, preserves the full AI response for review, exposes only extracted copy-format phrase pairs for submission, and isolates failures to the affected words

## Test Steps

- Case 1 (happy path): Return three grouped results in the same order as the submitted input words.
- Case 2 (edge case): Mark one malformed response as failed while preserving successful extracted groups for the other words.
- Case 3 (dynamic extraction): Preserve the exact extracted phrase count for each successful word.
- Case 4 (review versus submission): Preserve explanation text for display while exposing only the extracted copy-format pair for submission.
- Case 5 (integration): Use the real extraction contract to convert raw API response text into normalized phrase groups without manual reshaping.
- Case 6 (integration): Use the concrete API adapter so one failed request produces an error state only for the affected word while successful words remain reviewable.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

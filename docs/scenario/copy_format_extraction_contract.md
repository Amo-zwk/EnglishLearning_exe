# Scenario: Copy-Format Extraction Contract
- Given: One input word and one AI response text
- When: The response contains valid, invalid, or missing copy-format segments
- Then: The extractor returns one normalized result group with only valid phrase pairs, or an empty phrase list when none are valid

## Test Steps

- Case 1 (happy path): Extract two valid phrase pairs from one response and preserve the input word reference.
- Case 2 (edge case): Ignore a malformed copy-format segment with missing Chinese text while keeping valid segments.
- Case 3 (edge case): Return an empty phrase list when explanation text exists but there are no valid copy-format segments.
- Case 4 (mixed content): Ignore explanation sentences and include only the valid copy-format pair in the submission set.
- Case 5 (dedupe): Normalize surrounding whitespace so duplicate English phrases share the same dedupe key.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

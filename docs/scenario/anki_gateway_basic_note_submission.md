# Scenario: Basic note submission and result reporting
- Given: unique extracted phrase pairs and a chosen deck
- When: the gateway builds note payloads and submits them through AnkiConnect
- Then: each note uses Anki's Basic model with Front set to English text and Back set to Chinese meaning, and the gateway reports submitted, skipped, and failed counts separately

## Test Steps

- Case 1 (happy path): two unique phrase pairs create two Basic note payloads with the expected field mapping
- Case 2 (edge case): submitting without a chosen deck raises an error before any note creation call
- Case 3 (edge case): partial add-notes failure increments failed count while keeping skipped count separate

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

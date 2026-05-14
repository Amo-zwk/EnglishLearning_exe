# Scenario: Web submission roundtrip
- Given: generated review content rendered in the HTML workspace
- When: the browser submits reviewed phrase edits and a selected deck through the web routes
- Then: the HTTP layer forwards the reviewed values unchanged into the existing workspace flow and renders generate or submission feedback on the same page

## Test Steps

- Case 1 (happy path): the submit route forwards deck selection and edited phrase values unchanged into the existing workspace controller.
- Case 2 (integration path): using the real orchestrator and real Anki gateway boundaries, the app completes generate-to-submit flow and renders full AI response, extracted review content, and submission feedback.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

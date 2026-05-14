# Scenario: Review workspace deck selection and submission
- Given: a workspace connected to the generation orchestrator and Anki submission gateway
- When: the user generates grouped results and submits them after selecting a deck
- Then: generated groups keep the real orchestrator output, and the selected deck is passed unchanged into submission

## Test Steps

- Case 1 (integration): one generate click uses the real orchestrator and populates grouped cards with full response text and matching extracted phrase counts.
- Case 2 (integration): the selected deck value is passed unchanged into the real Anki submission gateway request.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

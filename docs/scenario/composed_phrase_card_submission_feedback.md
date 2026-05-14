# Scenario: Composed phrase card submission feedback
- Given: a review workspace with generated phrase groups, editable extracted phrase pairs, and a selected Anki deck
- When: the user reviews phrases, keeps only selected phrase pairs, and submits them through the Anki gateway
- Then: the page keeps the workflow in one place and displays submitted, skipped, and failed results in distinct status buckets for each submitted group

## Test Steps

- Case 1 (unit): mock submission results with added, skipped, and failed items render each count in the correct status bucket.
- Case 2 (integration): a reviewed phrase group submits through the real workspace controller plus real Anki gateway contract and renders visible feedback.
- Case 3 (integration): edited phrase text, not the original extracted text, is sent into the Anki submission payload.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

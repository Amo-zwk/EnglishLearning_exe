# Scenario: Composed phrase card partial failure preservation
- Given: a review workspace with multiple reviewed phrase groups ready for Anki submission
- When: one group submits successfully and another group fails
- Then: the workspace preserves reviewed phrase edits, keeps successful outcomes visible, and allows retrying the failed group without regenerating unaffected groups

## Test Steps

- Case 1 (unit): a partial failure preserves previously reviewed phrase edits for unaffected groups.
- Case 2 (integration): retrying after a partial failure submits only the failed group while preserving successful group feedback.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

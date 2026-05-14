# Scenario: Review workspace multi-input generation
- Given: a review workspace with multiple input blocks and an injectable generation action
- When: the user edits input values or explicitly clicks the generate action
- Then: the page keeps multiple input blocks available, and generation runs only after the explicit click

## Test Steps

- Case 1 (happy path): render two grouped result cards for two generated input words with the correct source labels.
- Case 2 (edge case): editing input values without clicking generate does not call the generation action.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

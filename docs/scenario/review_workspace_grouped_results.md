# Scenario: Review workspace grouped result details
- Given: generated grouped results for one or more input words
- When: the workspace renders the review cards
- Then: each card shows the full AI response and the matching extracted review area for that word

## Test Steps

- Case 1 (happy path): render the full AI response and four editable phrase boxes for one generated word.
- Case 2 (edge case): render an extracted review area with zero phrase boxes when a word has no extracted pairs.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

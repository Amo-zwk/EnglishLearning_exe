# Scenario: Review workspace inline phrase editing
- Given: a workspace containing extracted phrase pairs inside grouped review areas
- When: the user edits an English phrase or Chinese meaning inline
- Then: only the targeted extracted phrase item changes and sibling items remain unchanged

## Test Steps

- Case 1 (happy path): editing one English phrase updates only that extracted phrase item.
- Case 2 (edge case): editing one Chinese meaning updates only that extracted phrase item.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

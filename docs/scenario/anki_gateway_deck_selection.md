# Scenario: Anki deck selection
- Given: the gateway has an AnkiConnect client or transport dependency
- When: the caller requests available decks
- Then: the gateway returns the exact deck names reported by AnkiConnect in a selectable list

## Test Steps

- Case 1 (happy path): return multiple deck names unchanged and preserve order from the mocked AnkiConnect result
- Case 2 (edge case): return an empty selectable list when AnkiConnect reports no decks

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

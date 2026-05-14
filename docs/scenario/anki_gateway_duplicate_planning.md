# Scenario: Duplicate planning before note creation
- Given: extracted phrase pairs and an AnkiConnect duplicate lookup
- When: the gateway prepares a submission plan
- Then: any phrase whose English Front already exists in Anki is marked as skipped before note creation

## Test Steps

- Case 1 (happy path): one duplicate and one unique phrase produces one skipped item and one note candidate
- Case 2 (edge case): all phrases are duplicates so no note payloads are prepared

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

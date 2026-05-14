# Scenario: Web entry HTML route
- Given: a web app built around a workspace controller factory
- When: the browser requests the root route or posts an add-input action
- Then: the app returns an HTML document with the review workspace root, explicit generate control, and multiple input blocks available in the same page

## Test Steps

- Case 1 (happy path): the root route returns a full HTML document containing the review workspace root and the generate action control.
- Case 2 (edge case): posting an add-input action returns HTML with one more input block while keeping the review workspace page shape.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

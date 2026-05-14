# Scenario: Web app factory adapter seam
- Given: a configured generation callable and default workspace modules
- When: the app factory builds the web application and a generate request is made
- Then: the app uses the configured generation callable through the existing orchestrator and workspace controller without mutating the workspace business logic

## Test Steps

- Case 1 (happy path): the app factory builds an app that uses the configured generation callable to render real workspace generation output.
- Case 2 (edge case): the adapter loader resolves an environment-configured callable path and returns the callable unchanged for app construction.

## Status
- [x] Write scenario document
- [x] Write solid test according to document
- [x] Run test and watch it failing
- [x] Implement to make test pass
- [x] Run test and confirm it passed
- [x] Refactor implementation without breaking test
- [x] Run test and confirm still passing after refactor

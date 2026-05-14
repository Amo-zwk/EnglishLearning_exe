# Documentation Index

[中文文档](README.zh-CN.md)

This folder keeps lightweight scenario notes and documentation for the local review workflow.

## What Is Here

- `scenario/`: behavior-focused scenario notes used to guide and confirm implementation work
- `images/`: repository images used by the README and other docs
- contribution guides: repository maintenance notes in English and Chinese

## Suggested Reading Order

1. Start with the repository overview in [`../README.md`](../README.md).
2. Read the contribution guide in [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
3. Read the core workflow scenarios for generation, review, and submission.
4. Use the more specific gateway and web route scenarios when changing one subsystem.

## Repository Guides

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- [`../CONTRIBUTING.zh-CN.md`](../CONTRIBUTING.zh-CN.md)
- [`scenario/README.md`](scenario/README.md)
- [`scenario/README.zh-CN.md`](scenario/README.zh-CN.md)

## Core Workflow Scenarios

- [`scenario/copy_format_extraction_contract.md`](scenario/copy_format_extraction_contract.md)
- [`scenario/ai_generation_and_extraction_orchestrator.md`](scenario/ai_generation_and_extraction_orchestrator.md)
- [`scenario/review_workspace_multi_input_generation.md`](scenario/review_workspace_multi_input_generation.md)
- [`scenario/review_workspace_inline_edits.md`](scenario/review_workspace_inline_edits.md)
- [`scenario/review_workspace_grouped_results.md`](scenario/review_workspace_grouped_results.md)
- [`scenario/review_workspace_deck_submission.md`](scenario/review_workspace_deck_submission.md)
- [`scenario/composed_phrase_card_submission_feedback.md`](scenario/composed_phrase_card_submission_feedback.md)
- [`scenario/composed_phrase_card_partial_failure_preservation.md`](scenario/composed_phrase_card_partial_failure_preservation.md)
- [`scenario/web_submission_roundtrip.md`](scenario/web_submission_roundtrip.md)

## Integration Boundary Scenarios

- [`scenario/anki_gateway_deck_selection.md`](scenario/anki_gateway_deck_selection.md)
- [`scenario/anki_gateway_basic_note_submission.md`](scenario/anki_gateway_basic_note_submission.md)
- [`scenario/anki_gateway_duplicate_planning.md`](scenario/anki_gateway_duplicate_planning.md)
- [`scenario/web_entry_html_route.md`](scenario/web_entry_html_route.md)
- [`scenario/web_app_factory_adapter.md`](scenario/web_app_factory_adapter.md)

## Notes

- Most scenario files are written in English because they mirror implementation-oriented test design.
- The Chinese index exists to make the repository easier to browse on GitHub.

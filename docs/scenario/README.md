# Scenario Index

[中文索引](README.zh-CN.md)

This folder stores behavior-oriented scenario notes that describe how the workflow should act and what each related test protects.

## How To Use These Files

- Start here when you need to understand a workflow without reading code first.
- Read the matching scenario before changing a test-covered subsystem.
- Update the scenario when behavior changes in a meaningful way.

## End-To-End Workflow

- [`copy_format_extraction_contract.md`](copy_format_extraction_contract.md): extraction rules for the copy-only phrase format
- [`ai_generation_and_extraction_orchestrator.md`](ai_generation_and_extraction_orchestrator.md): multi-input generation and extraction orchestration
- [`review_workspace_multi_input_generation.md`](review_workspace_multi_input_generation.md): review workspace behavior after generating multiple inputs
- [`review_workspace_inline_edits.md`](review_workspace_inline_edits.md): inline editing of extracted phrase pairs
- [`review_workspace_grouped_results.md`](review_workspace_grouped_results.md): grouped display of AI response and review areas
- [`review_workspace_deck_submission.md`](review_workspace_deck_submission.md): selecting a deck and sending chosen cards to Anki
- [`composed_phrase_card_submission_feedback.md`](composed_phrase_card_submission_feedback.md): grouped feedback after submission
- [`composed_phrase_card_partial_failure_preservation.md`](composed_phrase_card_partial_failure_preservation.md): preserving useful results when part of a submission fails
- [`web_submission_roundtrip.md`](web_submission_roundtrip.md): browser-to-workspace submit flow

## Boundaries And Adapters

- [`anki_gateway_deck_selection.md`](anki_gateway_deck_selection.md): deck list retrieval through AnkiConnect
- [`anki_gateway_basic_note_submission.md`](anki_gateway_basic_note_submission.md): `Basic` note submission behavior
- [`anki_gateway_duplicate_planning.md`](anki_gateway_duplicate_planning.md): duplicate planning based on `Front`
- [`web_entry_html_route.md`](web_entry_html_route.md): rendering the main HTML route
- [`web_app_factory_adapter.md`](web_app_factory_adapter.md): app factory integration boundaries

## Notes

- Scenario files stay intentionally short.
- The Chinese companion index explains each file in browsing-friendly terms.

# 场景文档索引

[English Index](README.md)

这个目录放的是按行为拆分的场景文档，用来描述工作流应该怎么表现，以及对应测试大致在保护什么。

## 这些文件怎么用

- 如果你想先理解流程而不是先读代码，可以先从这里看。
- 改某个已有测试覆盖的子系统前，先读对应场景文档。
- 如果行为发生了明显变化，也顺手把对应场景文档更新掉。

## 端到端主流程

- [`copy_format_extraction_contract.md`](copy_format_extraction_contract.md)：复制专用词组格式的提取规则
- [`ai_generation_and_extraction_orchestrator.md`](ai_generation_and_extraction_orchestrator.md)：多输入生成与提取的编排流程
- [`review_workspace_multi_input_generation.md`](review_workspace_multi_input_generation.md)：生成多个输入后，审核工作台应该如何表现
- [`review_workspace_inline_edits.md`](review_workspace_inline_edits.md)：提取结果的内联编辑行为
- [`review_workspace_grouped_results.md`](review_workspace_grouped_results.md)：AI 响应与审核区按输入词分组展示
- [`review_workspace_deck_submission.md`](review_workspace_deck_submission.md)：选择 deck 并把选中卡片提交到 Anki
- [`composed_phrase_card_submission_feedback.md`](composed_phrase_card_submission_feedback.md)：提交后的分组反馈展示
- [`composed_phrase_card_partial_failure_preservation.md`](composed_phrase_card_partial_failure_preservation.md)：部分提交失败时如何保留有效结果
- [`web_submission_roundtrip.md`](web_submission_roundtrip.md)：从浏览器提交到工作台处理的完整往返

## 边界与适配层

- [`anki_gateway_deck_selection.md`](anki_gateway_deck_selection.md)：通过 AnkiConnect 获取 deck 列表
- [`anki_gateway_basic_note_submission.md`](anki_gateway_basic_note_submission.md)：`Basic` note 的提交行为
- [`anki_gateway_duplicate_planning.md`](anki_gateway_duplicate_planning.md)：基于 `Front` 的重复规划逻辑
- [`web_entry_html_route.md`](web_entry_html_route.md)：主页 HTML 路由渲染
- [`web_app_factory_adapter.md`](web_app_factory_adapter.md)：app factory 集成边界

## 说明

- 这些场景文档本身会刻意保持简短。
- 这里的中文索引重点是帮助你在 GitHub 浏览时快速知道每份文档是干什么的。

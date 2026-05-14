# 文档索引

[English Docs](README.md)

这个目录主要放与本地审核工作流相关的轻量文档和场景说明。

## 目录说明

- `scenario/`：按行为划分的场景文档，用来指导和确认实现
- `images/`：README 和其他文档中会用到的图片资源
- `contribution guides/`：仓库维护和协作说明的中英文文档

## 建议阅读顺序

1. 先看仓库总览：[`../README.zh-CN.md`](../README.zh-CN.md)
2. 再看贡献说明：[`../CONTRIBUTING.zh-CN.md`](../CONTRIBUTING.zh-CN.md)
3. 然后看生成、审核、提交这几类核心流程场景
4. 如果只改某个子系统，再补看对应的 gateway 或 web route 场景

## 仓库导览文档

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- [`../CONTRIBUTING.zh-CN.md`](../CONTRIBUTING.zh-CN.md)
- [`scenario/README.md`](scenario/README.md)
- [`scenario/README.zh-CN.md`](scenario/README.zh-CN.md)

## 核心流程场景

- [`scenario/copy_format_extraction_contract.md`](scenario/copy_format_extraction_contract.md)：复制专用格式的提取约定
- [`scenario/ai_generation_and_extraction_orchestrator.md`](scenario/ai_generation_and_extraction_orchestrator.md)：多输入生成与提取编排
- [`scenario/review_workspace_multi_input_generation.md`](scenario/review_workspace_multi_input_generation.md)：审核工作台的多输入生成
- [`scenario/review_workspace_inline_edits.md`](scenario/review_workspace_inline_edits.md)：审核区内联编辑
- [`scenario/review_workspace_grouped_results.md`](scenario/review_workspace_grouped_results.md)：按输入词分组展示审核结果
- [`scenario/review_workspace_deck_submission.md`](scenario/review_workspace_deck_submission.md)：选择 deck 并提交
- [`scenario/composed_phrase_card_submission_feedback.md`](scenario/composed_phrase_card_submission_feedback.md)：提交后的反馈分组展示
- [`scenario/composed_phrase_card_partial_failure_preservation.md`](scenario/composed_phrase_card_partial_failure_preservation.md)：部分失败时的保留逻辑
- [`scenario/web_submission_roundtrip.md`](scenario/web_submission_roundtrip.md)：从网页提交到工作流处理的完整往返

## 边界与集成场景

- [`scenario/anki_gateway_deck_selection.md`](scenario/anki_gateway_deck_selection.md)：Anki deck 列表获取
- [`scenario/anki_gateway_basic_note_submission.md`](scenario/anki_gateway_basic_note_submission.md)：Basic note 提交
- [`scenario/anki_gateway_duplicate_planning.md`](scenario/anki_gateway_duplicate_planning.md)：按 `Front` 查重与提交规划
- [`scenario/web_entry_html_route.md`](scenario/web_entry_html_route.md)：Web 入口 HTML 路由
- [`scenario/web_app_factory_adapter.md`](scenario/web_app_factory_adapter.md)：Web app factory 适配

## 说明

- 具体场景文件目前主要用英文写，因为它们更贴近测试设计和实现说明。
- 这里补了中文索引，方便直接在 GitHub 上快速理解每份文档的大致用途。

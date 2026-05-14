# 贡献说明

[English Version](CONTRIBUTING.md)

这个仓库主要还是个人工具，但把贡献和维护规则写清楚，后续自己回来看会更省心。

## 项目边界

- 保持它聚焦在个人英语词组制卡工作流上。
- 优先做实际工作流改进，而不是把它扩展成平台型产品。
- 把 `英语二的备考prompt.txt` 视为项目必需文件，而不是可替换示例。
- 继续保持只有复制专用格式里提取出的词组才能进入 Anki 提交流程。

## 改动前先看什么

- 先读 [`README.zh-CN.md`](README.zh-CN.md)，了解产品目标和整体流程。
- 再读 [`docs/README.zh-CN.md`](docs/README.zh-CN.md) 和 [`docs/scenario/README.zh-CN.md`](docs/scenario/README.zh-CN.md)，了解实现上下文。
- 尽量沿着现有结构改，不要在没有充分理由的情况下额外引入一层框架式抽象。

## 本地环境说明

- 在这个仓库里跑 `uv` 相关命令之前，先确认已经安装了 Python 3.12+。
- 如果机器上没有 `uv`，按 [`README.zh-CN.md`](README.zh-CN.md#按操作系统安装-python-和-uv) 里的分系统步骤安装。
- 如果刚装完 `uv` 还是提示 `command not found`，先重新加载 shell 配置，或者直接新开一个终端窗口。
- 如果 `uv` 能运行但识别不到 Python，先确认 Python 安装正常，再执行 `uv python list`。
- 如果后续有人反馈环境安装问题，记得把 [`README.zh-CN.md`](README.zh-CN.md#faq) 里的排错说明一起同步维护。

## 实现约定

- 面向用户的 UI 文案优先保持中文，除非该区域本来就是英文语境。
- 代码注释和英文文档继续使用英文；中文文档单独写在对应中文文件里。
- Anki 提交继续使用内置 `Basic` note type。
- 重复处理继续以 `Front` 为准。
- 不要因为模型生成了内容，就把低价值词组也一起加入。

## 提交前验证

在发起 PR 或合并本地改动前，先跑这两个命令：

```bash
uv run python -m unittest discover -s tests
uv run python -m py_compile "src/web_entrypoint.py" "src/review_workspace.py"
```

## PR 说明建议

- 多解释解决了什么工作流问题，而不只是改了哪些文件。
- 说明关联到哪些 `docs/scenario/` 场景文档。
- 如果 UI 结构有明显变化，最好附一张截图。
- 尽量保持 PR 范围可读，便于后续自己回看。

## 文档维护

- 只要影响了用户可见行为，就同步更新 [`README.md`](README.md) 和 [`README.zh-CN.md`](README.zh-CN.md)。
- 如果新增了新的文档分组或重要场景，也一起更新文档索引。

## 安全与隐私

- 不要提交像 `key` 这样的本地密钥文件。
- 项目必需 prompt 要保留在 git 中，但个人密钥和无关的本地调参文件不要进 git。
- 如果任何凭据曾被暴露，继续使用前先轮换。

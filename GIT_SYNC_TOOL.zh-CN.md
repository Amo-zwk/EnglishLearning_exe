# QuickGitSync 通用 Git 推送器

`QuickGitSync.exe` 是给不熟悉命令行的人用的通用 Git 图形工具。它不是 EnglishLearning 专用，任何项目文件夹都可以用。

## 它能做什么

- 选择任意项目文件夹
- 填写任意 GitHub 仓库地址
- 自动初始化 Git 仓库
- 一键拉取 Pull
- 一键提交并推送 Push
- 保存常用配置
- 实时显示执行日志
- 自动拦截常见敏感/环境文件，例如 `.env`、`key`、`*.pem`、`.venv`、`node_modules`、`runtime/.venv`、`config/local`
- 优先使用系统 Git；如果电脑没有 Git，会尝试使用打包在 exe 里的内置 Git 后端

## 推荐使用顺序

1. 打开 `dist\QuickGitSync.exe`
2. 选择你的项目文件夹
3. 填写 GitHub 仓库地址，例如：

```text
https://github.com/你的用户名/你的仓库.git
```

4. 分支一般填：

```text
main
```

5. 点 `检测`
6. 如果是已有仓库，先点 `拉取 Pull`
7. 修改项目后，填写提交说明
8. 点 `推送 Push`

## 关于账号登录

如果使用系统 Git，首次推送可能会弹出 GitHub 登录窗口，按提示登录即可。

如果没有弹窗，或者你使用内置 Git 后端，可以填写：

- GitHub 用户名
- Token/密码

GitHub 现在通常需要 Personal Access Token，普通账号密码可能不可用。

## 关于“强制包含”

有些文件可能被 `.gitignore` 忽略，但你又确实想上传，比如打包好的 exe。可以在 `强制包含` 里填写路径，一行一个，或用分号分隔：

```text
dist/app.exe
release/tool.zip
```

普通项目不需要填写这里。

## 后端模式

- `auto`：推荐。优先使用系统 Git，没有系统 Git 时使用内置后端
- `system`：只使用电脑里的 Git
- `builtin`：只使用 exe 内置 Git 后端

系统 Git 兼容性最好；内置后端适合“电脑没装 Git”的小白场景，但复杂冲突仍建议用系统 Git 处理。

## 常见失败提示

- `Authentication failed`：GitHub 登录失败，需要重新登录或使用 Token
- `Permission denied (publickey)`：你用了 SSH 地址但电脑没有 SSH Key，建议换成 HTTPS 地址
- `conflict`：拉取时发生冲突，需要人工处理后再继续
- `SSL/TLS connection failed`：网络握手失败，检查网络或稍后重试

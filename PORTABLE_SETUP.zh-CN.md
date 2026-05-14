# 便携安装与启动

这套项目现在保留原有源码结构，同时新增一层便携运行结构，方便复制到其他电脑后重新安装和配置。

## 推荐使用顺序

Windows:

```bat
install_environment.bat
configure_environment.bat
launch_app.bat
```

macOS / Linux / Git Bash:

```bash
sh install_environment.sh
sh configure_environment.sh
sh launch_app.sh
```

## 文件结构

- `src/`: 原有业务代码，不改变模块引用方式。
- `static/`: 页面样式和脚本资源。
- `scripts/`: 便携安装器、配置器、启动器的 Python 实现。
- `config/templates/`: 可提交到仓库的配置模板。
- `config/local/`: 配置器生成的本机配置，已加入 `.gitignore`。
- `runtime/`: 运行时目录，安装器会创建 `runtime/.venv`。

## 三个入口分别做什么

- `install_environment`: 检查 Python 3.12+，创建 `runtime/.venv`，并安装 `pyproject.toml` 中声明的依赖。
- `configure_environment`: 写入本机 API key、生成模型配置、AnkiConnect 地址和 `runtime.env`。
- `launch_app`: 读取 `config/local/runtime.env`，自动打开浏览器并启动本地网页。

## 兼容旧配置

为了不破坏当前项目功能，旧文件仍然可用：

- 根目录 `key`
- 根目录 `GenerationConfig`
- 根目录 `AnkiConnect`
- 环境变量 `GEMINI_API_KEY`、`COPY_FORMAT_*`

新的优先级是：显式环境变量或配置器生成的路径优先，其次读取 `config/local/`，最后回退到旧的根目录配置文件。

## 搬到另一台电脑

复制项目时不用复制这些本机文件：

- `.venv/`
- `runtime/.venv/`
- `config/local/`
- 根目录 `key`

在新电脑上安装 Python 3.12+ 后，按推荐顺序运行安装器、配置器、启动器即可。

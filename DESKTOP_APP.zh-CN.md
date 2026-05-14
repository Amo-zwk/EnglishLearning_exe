# Windows 桌面版

桌面版面向普通使用者，只交付一个主程序：

```text
dist/EnglishLearning.exe
```

双击后会打开独立桌面窗口。首次启动会进入设置页，保存 API Key、模型接口和 AnkiConnect 地址后进入工作台。

## 构建

在项目根目录运行：

```bat
build_desktop_app.bat
```

构建完成后可执行文件位于：

```text
dist/EnglishLearning.exe
```

构建时会自动生成并使用桌面图标：

```text
assets/desktop-icon.ico
assets/desktop-icon.png
```

## 用户配置位置

桌面版不会要求用户编辑项目文件。配置保存在：

```text
%APPDATA%\EnglishLearning
```

包含：

- `key`
- `GenerationConfig`
- `AnkiConnect`

## 仍需外部准备

Anki 和 AnkiConnect 仍由用户自行安装。桌面版会通过本机 AnkiConnect 地址读取 deck 并提交卡片。

## 运行前提

`EnglishLearning.exe` 已经包含 Python 运行时和项目依赖，目标电脑不需要安装 Python、uv 或源码文件。

仍需要注意：

- 当前构建面向 64 位 Windows。
- 桌面窗口使用 Microsoft Edge WebView2 Runtime。Windows 10/11 大多数机器已经自带；如果缺少，程序会弹出提示，不会改用浏览器。
- AI 生成功能需要网络和可用 API Key。
- 提交到 Anki 需要用户已经安装 Anki 和 AnkiConnect。

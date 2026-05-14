from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.portable_common import PROJECT_ROOT, print_header, print_key_values
from scripts.create_desktop_icon import ICON_PATH, main as create_icon
from src.app_metadata import APP_COPYRIGHT, APP_DESCRIPTION, APP_NAME, APP_VERSION


def main() -> int:
    print_header("EnglishLearning desktop build")
    if not _module_exists("PyInstaller"):
        print("[error] PyInstaller is not installed in this Python environment.")
        print("Run: python -m pip install pyinstaller")
        return 1
    if not _module_exists("webview"):
        print("[error] pywebview is not installed in this Python environment.")
        print("Run: python -m pip install pywebview")
        return 1

    static_dir = PROJECT_ROOT / "static"
    prompt_file = PROJECT_ROOT / "英语二的备考prompt.txt"
    version_file = PROJECT_ROOT / "build" / f"{APP_NAME}.version.txt"
    create_icon()
    _write_windows_version_file(version_file)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--onefile",
        "--windowed",
        "--icon",
        str(ICON_PATH),
        "--version-file",
        str(version_file),
        "--distpath",
        str(PROJECT_ROOT / "dist"),
        "--workpath",
        str(PROJECT_ROOT / "build" / "pyinstaller"),
        "--specpath",
        str(PROJECT_ROOT / "build"),
        "--add-data",
        f"{static_dir}{os.pathsep}static",
        "--add-data",
        f"{prompt_file}{os.pathsep}.",
        "--hidden-import",
        "webview.platforms.edgechromium",
        str(PROJECT_ROOT / "src" / "desktop_entrypoint.py"),
    ]
    subprocess.run(command, cwd=str(PROJECT_ROOT), check=True)
    print_header("Desktop build complete")
    print_key_values(
        [
            ("Executable", PROJECT_ROOT / "dist" / "EnglishLearning.exe"),
            ("Version", APP_VERSION),
            ("Config directory", "%APPDATA%\\EnglishLearning"),
        ]
    )
    return 0


def _module_exists(module_name: str) -> bool:
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


def _write_windows_version_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    version_tuple = _version_tuple(APP_VERSION)
    version_tuple_text = ", ".join(str(part) for part in version_tuple)
    path.write_text(
        f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple_text}),
    prodvers=({version_tuple_text}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904b0',
        [
          StringStruct('CompanyName', '{APP_NAME}'),
          StringStruct('FileDescription', '{APP_DESCRIPTION}'),
          StringStruct('FileVersion', '{APP_VERSION}'),
          StringStruct('InternalName', '{APP_NAME}'),
          StringStruct('LegalCopyright', '{APP_COPYRIGHT}'),
          StringStruct('OriginalFilename', '{APP_NAME}.exe'),
          StringStruct('ProductName', '{APP_NAME}'),
          StringStruct('ProductVersion', '{APP_VERSION}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".") if part.isdigit()]
    return tuple((parts + [0, 0, 0, 0])[:4])


if __name__ == "__main__":
    raise SystemExit(main())

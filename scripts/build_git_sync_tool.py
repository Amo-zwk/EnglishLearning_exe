from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.create_desktop_icon import ICON_PATH, main as create_icon
from scripts.portable_common import PROJECT_ROOT, print_header, print_key_values
from src.git_sync_tool import APP_DESCRIPTION, APP_NAME, APP_VERSION


def main() -> int:
    print_header("EnglishLearning Git sync tool build")
    if not _module_exists("PyInstaller"):
        print("[error] PyInstaller is not installed in this Python environment.")
        print("Run: python -m pip install pyinstaller")
        return 1
    if not _module_exists("dulwich"):
        print("[error] dulwich is not installed in this Python environment.")
        print("Run: python -m pip install dulwich")
        return 1

    create_icon()
    version_file = PROJECT_ROOT / "build" / f"{APP_NAME}.version.txt"
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
        str(PROJECT_ROOT / "src" / "git_sync_tool.py"),
    ]
    subprocess.run(command, cwd=str(PROJECT_ROOT), check=True)
    print_header("Git sync tool build complete")
    print_key_values(
        [
            ("Executable", PROJECT_ROOT / "dist" / f"{APP_NAME}.exe"),
            ("Version", APP_VERSION),
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
          StringStruct('CompanyName', 'EnglishLearning'),
          StringStruct('FileDescription', '{APP_DESCRIPTION}'),
          StringStruct('FileVersion', '{APP_VERSION}'),
          StringStruct('InternalName', '{APP_NAME}'),
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

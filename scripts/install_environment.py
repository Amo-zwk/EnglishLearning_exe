from __future__ import annotations

import json
from pathlib import Path
import sys
from datetime import datetime, timezone
import venv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.portable_common import (
    INSTALLATION_MARKER_FILE,
    PortableSetupError,
    ensure_portable_directories,
    platform_summary,
    print_header,
    print_key_values,
    read_pyproject_dependencies,
    require_supported_python,
    run_command,
    runtime_paths,
)


def create_runtime_venv() -> Path:
    paths = runtime_paths()
    if paths.python.exists():
        print(f"[ok] Runtime environment already exists: {paths.venv}")
        return paths.python

    print(f"[create] Creating runtime environment: {paths.venv}")
    builder = venv.EnvBuilder(with_pip=True, clear=False, upgrade_deps=False)
    builder.create(paths.venv)
    if not paths.python.exists():
        raise PortableSetupError(f"Runtime Python was not created at {paths.python}.")
    return paths.python


def install_dependencies(runtime_python: Path) -> None:
    dependencies = read_pyproject_dependencies()
    if not dependencies:
        print("[ok] No third-party dependencies are declared in pyproject.toml.")
        return

    run_command([str(runtime_python), "-m", "pip", "install", *dependencies])


def write_installation_marker(runtime_python: Path) -> None:
    payload = {
        "installedAt": datetime.now(timezone.utc).isoformat(),
        "runtimePython": str(runtime_python.resolve()),
        "projectRoot": str(runtime_paths().root.resolve()),
        "platform": platform_summary(),
        "dependencies": read_pyproject_dependencies(),
    }
    INSTALLATION_MARKER_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    print_header("EnglishLearning portable environment installer")
    try:
        require_supported_python()
        ensure_portable_directories()
        runtime_python = create_runtime_venv()
        install_dependencies(runtime_python)
        write_installation_marker(runtime_python)
    except PortableSetupError as error:
        print(f"[error] {error}")
        return 1

    print_header("Installation complete")
    print_key_values(
        [
            ("Runtime Python", runtime_python.resolve()),
            ("Next step", "run configure_environment.bat or configure_environment.sh"),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

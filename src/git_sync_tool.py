from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
from typing import Callable
from urllib.parse import quote, urlsplit, urlunsplit
import webbrowser

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


APP_NAME = "QuickGitSync"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Universal Git push and pull helper"
DEFAULT_BRANCH = "main"
DEFAULT_REMOTE_URL = ""
DEFAULT_USER_NAME = ""
DEFAULT_USER_EMAIL = ""
GITHUB_HELP_URL = "https://github.com/new"

SENSITIVE_EXACT_PATHS = {
    ".env",
    ".env.local",
    ".env.production",
    "key",
    "secret.json",
    "secrets.json",
    "AnkiConnect",
    "GenerationConfig",
}
SENSITIVE_SUFFIXES = (".pem", ".p12", ".pfx", ".key")
SENSITIVE_PREFIXES = (
    ".venv/",
    "venv/",
    "env/",
    "node_modules/",
    "runtime/.venv/",
    "config/local/",
)


class GitSyncError(RuntimeError):
    pass


class GitCommandError(GitSyncError):
    def __init__(self, command: list[str], returncode: int, output: str) -> None:
        self.command = command
        self.returncode = returncode
        self.output = output
        super().__init__(
            f"Git command failed ({returncode}): {' '.join(command)}\n{output}"
        )


@dataclass
class GitSyncConfig:
    repo_path: str
    remote_url: str = DEFAULT_REMOTE_URL
    branch: str = DEFAULT_BRANCH
    git_path: str = ""
    user_name: str = DEFAULT_USER_NAME
    user_email: str = DEFAULT_USER_EMAIL
    auth_username: str = ""
    auth_token: str = ""
    force_include_paths: str = ""
    backend: str = "auto"


def config_file_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / APP_NAME / "config.json"


def default_repo_path() -> Path:
    configured = os.environ.get("QUICK_GIT_SYNC_REPO", "").strip()
    if configured:
        return Path(configured)
    candidates = [Path.cwd(), Path(sys.executable).resolve().parent]
    for candidate in candidates:
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def load_config(path: Path | None = None) -> GitSyncConfig:
    config_path = path or config_file_path()
    defaults = GitSyncConfig(repo_path=str(default_repo_path()))
    if not config_path.exists():
        return defaults
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(payload, dict):
        return defaults
    values = asdict(defaults)
    values.update(
        {
            key: value
            for key, value in payload.items()
            if key in values and isinstance(value, str)
        }
    )
    return GitSyncConfig(**values)


def save_config(config: GitSyncConfig, path: Path | None = None) -> Path:
    config_path = path or config_file_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path


def normalize_repo_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip("/")


def is_sensitive_repo_path(path: str | Path) -> bool:
    normalized = normalize_repo_path(path)
    basename = normalized.rsplit("/", 1)[-1]
    if normalized in SENSITIVE_EXACT_PATHS or basename in SENSITIVE_EXACT_PATHS:
        return True
    if basename.endswith(SENSITIVE_SUFFIXES):
        return True
    return any(normalized.startswith(prefix) for prefix in SENSITIVE_PREFIXES)


def filter_sensitive_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if is_sensitive_repo_path(path)]


def parse_force_include_paths(value: str) -> list[str]:
    return [
        normalize_repo_path(item.strip())
        for item in value.replace(";", "\n").splitlines()
        if item.strip()
    ]


def find_git_executable(configured_git_path: str = "") -> str:
    configured = configured_git_path.strip().strip('"')
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path)
        raise GitSyncError(f"找不到你填写的 Git 路径：{configured}")

    detected = shutil.which("git")
    if detected:
        return detected

    for path in [
        Path("C:/Program Files/Git/bin/git.exe"),
        Path("C:/Program Files/Git/cmd/git.exe"),
        Path("C:/Program Files (x86)/Git/bin/git.exe"),
        Path("C:/Program Files (x86)/Git/cmd/git.exe"),
    ]:
        if path.exists():
            return str(path)

    raise GitSyncError("没有检测到系统 Git。")


def has_builtin_git_backend() -> bool:
    try:
        import dulwich  # noqa: F401
    except Exception:
        return False
    return True


def choose_backend(config: GitSyncConfig) -> str:
    mode = config.backend.strip().lower() or "auto"
    if mode == "system":
        find_git_executable(config.git_path)
        return "system"
    if mode == "builtin":
        if has_builtin_git_backend():
            return "builtin"
        raise GitSyncError("内置 Git 后端不可用。请重新打包，确保 dulwich 已安装。")
    try:
        find_git_executable(config.git_path)
    except GitSyncError:
        if has_builtin_git_backend():
            return "builtin"
        raise GitSyncError(
            "没有检测到 Git，也没有内置 Git 后端。请安装 Git for Windows 或重新打包同步器。"
        )
    return "system"


def authenticated_remote_url(config: GitSyncConfig) -> str:
    remote = config.remote_url.strip()
    token = config.auth_token.strip()
    if not token or not remote.lower().startswith(("http://", "https://")):
        return remote
    parts = urlsplit(remote)
    username = config.auth_username.strip() or config.user_name.strip() or "git"
    userinfo = f"{quote(username, safe='')}:{quote(token, safe='')}"
    return urlunsplit((parts.scheme, f"{userinfo}@{parts.netloc}", parts.path, parts.query, parts.fragment))


def mask_secret(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def run_git(
    config: GitSyncConfig,
    args: list[str],
    log: Callable[[str], None] | None = None,
    check: bool = True,
    display_args: list[str] | None = None,
) -> tuple[int, str]:
    git_executable = find_git_executable(config.git_path)
    repo = Path(config.repo_path)
    cwd = repo if repo.exists() else Path.cwd()
    command = [git_executable, *args]
    printable_args = display_args or args
    if log is not None:
        log("$ git " + " ".join(printable_args))
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    output = mask_secret(completed.stdout.strip(), config.auth_token.strip())
    if output and log is not None:
        log(output)
    if check and completed.returncode != 0:
        raise GitCommandError(command, completed.returncode, output)
    return completed.returncode, output


def ensure_system_repository(config: GitSyncConfig, log: Callable[[str], None]) -> None:
    repo = Path(config.repo_path)
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        log("当前文件夹还不是 Git 仓库，正在初始化。")
        code, _output = run_git(config, ["init", "-b", config.branch], log=log, check=False)
        if code != 0:
            run_git(config, ["init"], log=log)
            run_git(config, ["checkout", "-B", config.branch], log=log)

    if config.user_name.strip():
        run_git(config, ["config", "user.name", config.user_name.strip()], log=log)
    if config.user_email.strip():
        run_git(config, ["config", "user.email", config.user_email.strip()], log=log)

    code, current_remote = run_git(
        config, ["remote", "get-url", "origin"], log=None, check=False
    )
    if code != 0:
        run_git(config, ["remote", "add", "origin", config.remote_url], log=log)
    elif current_remote.strip() != config.remote_url.strip():
        log(f"远程地址已更新：{current_remote.strip()} -> {config.remote_url.strip()}")
        run_git(config, ["remote", "set-url", "origin", config.remote_url], log=log)


def list_git_paths(config: GitSyncConfig, args: list[str]) -> list[str]:
    _code, output = run_git(config, args, log=None)
    return [line.strip() for line in output.splitlines() if line.strip()]


def list_tracked_sensitive_paths(config: GitSyncConfig) -> list[str]:
    return filter_sensitive_paths(list_git_paths(config, ["ls-files"]))


def list_staged_sensitive_paths(config: GitSyncConfig) -> list[str]:
    return filter_sensitive_paths(list_git_paths(config, ["diff", "--cached", "--name-only"]))


def list_root_sensitive_files(repo: Path) -> list[str]:
    found: list[str] = []
    for name in sorted(SENSITIVE_EXACT_PATHS):
        if (repo / name).exists():
            found.append(name)
    for prefix in SENSITIVE_PREFIXES:
        if (repo / prefix).exists():
            found.append(prefix)
    return found


def ensure_no_tracked_sensitive_files(config: GitSyncConfig) -> None:
    sensitive = list_tracked_sensitive_paths(config)
    if sensitive:
        raise GitSyncError(
            "已阻止操作：仓库里已经被 Git 跟踪了本地敏感/环境文件。\n"
            + "\n".join(f"- {path}" for path in sensitive)
            + "\n\n请先从仓库中移除这些文件后再推送。"
        )


def has_staged_changes(config: GitSyncConfig) -> bool:
    return bool(list_git_paths(config, ["diff", "--cached", "--name-only"]))


def system_pull_rebase(
    config: GitSyncConfig, log: Callable[[str], None], allow_empty_remote: bool
) -> None:
    remote = authenticated_remote_url(config)
    args = ["pull", "--rebase", "--autostash", remote, config.branch]
    display_args = ["pull", "--rebase", "--autostash", config.remote_url, config.branch]
    try:
        run_git(config, args, log=log, display_args=display_args)
    except GitCommandError as error:
        text = error.output.lower()
        if allow_empty_remote and (
            "couldn't find remote ref" in text
            or "could not find remote ref" in text
            or "no such ref was fetched" in text
        ):
            log("远程仓库还没有这个分支，跳过拉取，稍后会直接推送。")
            return
        raise


def system_commit_local_changes(
    config: GitSyncConfig, message: str, log: Callable[[str], None]
) -> None:
    run_git(config, ["add", "-A"], log=log)
    force_paths = parse_force_include_paths(config.force_include_paths)
    if force_paths:
        run_git(config, ["add", "-f", *force_paths], log=log)

    sensitive = list_staged_sensitive_paths(config)
    if sensitive:
        run_git(config, ["restore", "--staged", "--", *sensitive], log=log, check=False)
        raise GitSyncError(
            "已阻止提交：暂存区里包含本地敏感/环境文件。\n"
            + "\n".join(f"- {path}" for path in sensitive)
        )

    if not has_staged_changes(config):
        log("没有检测到需要提交的改动。")
        return

    run_git(config, ["commit", "-m", message.strip() or default_commit_message()], log=log)


def system_push_repository(
    config: GitSyncConfig, message: str, log: Callable[[str], None]
) -> None:
    ensure_system_repository(config, log)
    ensure_no_tracked_sensitive_files(config)
    system_commit_local_changes(config, message, log)
    system_pull_rebase(config, log, allow_empty_remote=True)
    remote = authenticated_remote_url(config)
    args = ["push", "-u", remote, f"HEAD:{config.branch}"]
    display_args = ["push", "-u", config.remote_url, f"HEAD:{config.branch}"]
    run_git(config, args, log=log, display_args=display_args)


def system_pull_repository(config: GitSyncConfig, log: Callable[[str], None]) -> None:
    ensure_system_repository(config, log)
    ensure_no_tracked_sensitive_files(config)
    system_pull_rebase(config, log, allow_empty_remote=False)


def builtin_available_or_raise() -> None:
    if not has_builtin_git_backend():
        raise GitSyncError("内置 Git 后端不可用。请重新打包，确保 dulwich 已安装。")


def builtin_author(config: GitSyncConfig) -> bytes:
    name = config.user_name.strip() or "QuickGitSync"
    email = config.user_email.strip() or "quick-git-sync@example.local"
    return f"{name} <{email}>".encode("utf-8")


def builtin_stream(log: Callable[[str], None]):
    class Stream:
        def write(self, data):
            text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
            for line in text.splitlines():
                if line.strip():
                    log(line)

        def flush(self):
            return None

    return Stream()


def builtin_init_repository(config: GitSyncConfig, log: Callable[[str], None]) -> None:
    builtin_available_or_raise()
    from dulwich import porcelain

    repo = Path(config.repo_path)
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        log("当前文件夹还不是 Git 仓库，正在用内置后端初始化。")
        porcelain.init(repo)
    try:
        porcelain.remote_add(repo, "origin", config.remote_url)
    except Exception:
        pass


def builtin_status_paths(config: GitSyncConfig) -> tuple[list[str], list[str], list[str]]:
    from dulwich import porcelain

    status = porcelain.status(config.repo_path)
    staged: list[str] = []
    for values in status.staged.values():
        staged.extend(_decode_path(value) for value in values)
    unstaged = [_decode_path(value) for value in status.unstaged]
    untracked = [_decode_path(value) for value in status.untracked]
    return staged, unstaged, untracked


def _decode_path(value: bytes | str) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def iter_project_files(repo: Path) -> list[str]:
    paths: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        relative = normalize_repo_path(path.relative_to(repo))
        if relative.startswith(".git/") or is_sensitive_repo_path(relative):
            continue
        paths.append(relative)
    return paths


def builtin_commit_local_changes(
    config: GitSyncConfig, message: str, log: Callable[[str], None]
) -> None:
    from dulwich import porcelain

    repo = Path(config.repo_path)
    paths = iter_project_files(repo)
    if paths:
        porcelain.add(repo, paths=paths)
    staged, unstaged, untracked = builtin_status_paths(config)
    sensitive = filter_sensitive_paths(staged + unstaged + untracked)
    if sensitive:
        raise GitSyncError(
            "已阻止提交：检测到本地敏感/环境文件。\n"
            + "\n".join(f"- {path}" for path in sensitive)
        )
    if not (staged or unstaged or untracked):
        log("没有检测到需要提交的改动。")
        return
    commit_id = porcelain.commit(
        repo,
        message=(message.strip() or default_commit_message()).encode("utf-8"),
        author=builtin_author(config),
        committer=builtin_author(config),
    )
    log(f"已创建提交：{commit_id.decode('ascii', errors='replace')[:12]}")


def builtin_push_repository(
    config: GitSyncConfig, message: str, log: Callable[[str], None]
) -> None:
    from dulwich import porcelain

    builtin_init_repository(config, log)
    builtin_commit_local_changes(config, message, log)
    remote = config.remote_url.strip()
    refspec = f"refs/heads/{config.branch}:refs/heads/{config.branch}"
    log(f"$ builtin git push {config.remote_url} {refspec}")
    porcelain.push(
        config.repo_path,
        remote,
        refspecs=refspec,
        outstream=builtin_stream(log),
        errstream=builtin_stream(log),
        username=config.auth_username.strip() or None,
        password=config.auth_token.strip() or None,
    )


def builtin_pull_repository(config: GitSyncConfig, log: Callable[[str], None]) -> None:
    from dulwich import porcelain

    builtin_init_repository(config, log)
    refspec = f"refs/heads/{config.branch}"
    log(f"$ builtin git pull {config.remote_url} {refspec}")
    porcelain.pull(
        config.repo_path,
        config.remote_url.strip(),
        refspecs=refspec,
        outstream=builtin_stream(log),
        errstream=builtin_stream(log),
        ff_only=True,
        username=config.auth_username.strip() or None,
        password=config.auth_token.strip() or None,
    )


def push_repository(config: GitSyncConfig, message: str, log: Callable[[str], None]) -> None:
    validate_config(config)
    backend = choose_backend(config)
    log(f"使用后端：{'系统 Git' if backend == 'system' else '内置 Git'}")
    root_sensitive = list_root_sensitive_files(Path(config.repo_path))
    if root_sensitive:
        log("提示：检测到常见本地配置/环境文件，会避免上传：")
        for path in root_sensitive:
            log(f"- {path}")
    if backend == "system":
        system_push_repository(config, message, log)
    else:
        builtin_push_repository(config, message, log)
    log("推送完成。")


def pull_repository(config: GitSyncConfig, log: Callable[[str], None]) -> None:
    validate_config(config)
    backend = choose_backend(config)
    log(f"使用后端：{'系统 Git' if backend == 'system' else '内置 Git'}")
    if backend == "system":
        system_pull_repository(config, log)
    else:
        builtin_pull_repository(config, log)
    log("拉取完成。")


def detect_environment(config: GitSyncConfig, log: Callable[[str], None]) -> None:
    log("开始检测。")
    log(f"项目目录：{config.repo_path}")
    log(f"远程地址：{config.remote_url or '未填写'}")
    log(f"分支：{config.branch}")
    log(f"后端模式：{config.backend}")
    if has_builtin_git_backend():
        log("内置 Git 后端：可用")
    else:
        log("内置 Git 后端：不可用")
    try:
        git_executable = find_git_executable(config.git_path)
    except Exception as error:
        log(f"系统 Git：未检测到（{error}）")
    else:
        log(f"系统 Git：{git_executable}")
        code, version = run_git(config, ["--version"], log=None, check=False)
        if code == 0:
            log(version)
    repo = Path(config.repo_path)
    if (repo / ".git").exists():
        log("Git 仓库：已存在")
        if choose_backend(config) == "system":
            run_git(config, ["status", "--short", "--branch"], log=log, check=False)
            sensitive = list_tracked_sensitive_paths(config)
            log("敏感文件检查：" + ("通过" if not sensitive else "发现风险"))
            for path in sensitive:
                log(f"- {path}")
        else:
            staged, unstaged, untracked = builtin_status_paths(config)
            log(f"暂存：{len(staged)}，未暂存：{len(unstaged)}，未跟踪：{len(untracked)}")
    else:
        log("Git 仓库：还未初始化，点击推送时会自动初始化。")
    log("检测完成。")


def validate_config(config: GitSyncConfig) -> None:
    if not config.remote_url.strip():
        raise GitSyncError("请先填写 GitHub 仓库地址。")
    if not config.branch.strip():
        raise GitSyncError("请先填写分支名，例如 main。")


def default_commit_message() -> str:
    return "Update project " + datetime.now().strftime("%Y-%m-%d %H:%M")


def friendly_error_message(error: Exception) -> str:
    text = str(error)
    lower = text.lower()
    if "could not read username" in lower or "authentication failed" in lower:
        return (
            text
            + "\n\nGitHub 登录失败：如果弹出登录窗口，请登录 GitHub。"
            "如果没有弹窗，可以在工具里填写 GitHub 用户名和 Token。"
        )
    if "permission denied (publickey)" in lower:
        return text + "\n\nSSH 没有可用密钥。小白建议使用 HTTPS 地址。"
    if "ssl/tls" in lower or "failed to receive handshake" in lower:
        return text + "\n\n网络或 TLS 握手失败。请检查网络，或稍后重试。"
    if "conflict" in lower:
        return text + "\n\n出现合并冲突，需要人工处理冲突后再继续。"
    return text


class GitSyncApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1040x760")
        self.root.minsize(900, 650)
        self.config = load_config()
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self._build_variables()
        self._build_ui()
        self._poll_log_queue()
        self.append_log("准备就绪。选择任意项目文件夹，填 GitHub 地址，然后检测、拉取或推送。")

    def _build_variables(self) -> None:
        self.repo_path = tk.StringVar(value=self.config.repo_path)
        self.remote_url = tk.StringVar(value=self.config.remote_url)
        self.branch = tk.StringVar(value=self.config.branch)
        self.git_path = tk.StringVar(value=self.config.git_path)
        self.user_name = tk.StringVar(value=self.config.user_name)
        self.user_email = tk.StringVar(value=self.config.user_email)
        self.auth_username = tk.StringVar(value=self.config.auth_username)
        self.auth_token = tk.StringVar(value=self.config.auth_token)
        self.force_include_paths = tk.StringVar(value=self.config.force_include_paths)
        self.backend = tk.StringVar(value=self.config.backend)
        self.commit_message = tk.StringVar(value=default_commit_message())
        self.status_text = tk.StringVar(value="空闲")

    def _build_ui(self) -> None:
        self.root.configure(bg="#f4f7f3")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f7f3")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#f4f7f3", foreground="#15221d")
        style.configure("Card.TLabel", background="#ffffff", foreground="#15221d")
        style.configure("Hint.TLabel", background="#ffffff", foreground="#5c6b63")
        style.configure("Primary.TButton", padding=(14, 9), font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=(12, 8))

        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill=tk.BOTH, expand=True)
        ttk.Label(outer, text="QuickGitSync 通用 Git 推送器", font=("Segoe UI", 22, "bold")).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="任意项目都可以用：选择文件夹、填写 GitHub 仓库地址，然后一键 Pull / Push。",
            foreground="#526158",
        ).pack(anchor=tk.W, pady=(6, 14))

        main = ttk.Frame(outer)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        settings = ttk.Frame(main, style="Card.TFrame", padding=16)
        settings.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        settings.columnconfigure(1, weight=1)
        self._entry_row(settings, 0, "项目文件夹", self.repo_path, self.choose_repo_path)
        self._entry_row(settings, 1, "GitHub 地址", self.remote_url)
        self._entry_row(settings, 2, "分支", self.branch)
        self._entry_row(settings, 3, "提交用户名", self.user_name)
        self._entry_row(settings, 4, "提交邮箱", self.user_email)
        self._entry_row(settings, 5, "GitHub 用户名", self.auth_username)
        self._entry_row(settings, 6, "Token/密码", self.auth_token, show="*")
        self._entry_row(settings, 7, "Git 路径", self.git_path, self.choose_git_path)
        self._entry_row(settings, 8, "强制包含", self.force_include_paths)
        self._entry_row(settings, 9, "提交说明", self.commit_message)

        ttk.Label(settings, text="后端", style="Card.TLabel").grid(row=10, column=0, sticky="w", pady=5)
        backend_box = ttk.Combobox(
            settings,
            textvariable=self.backend,
            values=["auto", "system", "builtin"],
            state="readonly",
            width=16,
        )
        backend_box.grid(row=10, column=1, sticky="w", pady=5, padx=(10, 6))

        help_text = (
            "小白说明：\n"
            "1. 项目文件夹可以是任何项目。\n"
            "2. GitHub 地址填你自己建的仓库 HTTPS/SSH 地址。\n"
            "3. auto 会优先用系统 Git；没有 Git 时使用内置后端。\n"
            "4. 私有仓库或首次推送，可能需要 GitHub Token。\n"
            "5. .env、密钥、虚拟环境、node_modules 会被拦截，避免误传。"
        )
        ttk.Label(settings, text=help_text, style="Hint.TLabel", justify=tk.LEFT).grid(
            row=11, column=0, columnspan=3, sticky="ew", pady=(12, 8)
        )

        action_grid = ttk.Frame(settings, style="Card.TFrame")
        action_grid.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        for index in range(2):
            action_grid.columnconfigure(index, weight=1)
        self.buttons: list[ttk.Button] = []
        self._button(action_grid, "检测", self.start_detect, 0, 0)
        self._button(action_grid, "保存配置", self.save_current_config, 0, 1)
        self._button(action_grid, "拉取 Pull", self.start_pull, 1, 0)
        self._button(action_grid, "推送 Push", self.start_push, 1, 1, style="Primary.TButton")
        self._button(action_grid, "打开文件夹", self.open_repo_folder, 2, 0)
        self._button(action_grid, "打开 GitHub", self.open_github, 2, 1)

        log_panel = ttk.Frame(main, style="Card.TFrame", padding=16)
        log_panel.grid(row=0, column=1, sticky="nsew")
        log_panel.rowconfigure(1, weight=1)
        log_panel.columnconfigure(0, weight=1)
        ttk.Label(log_panel, textvariable=self.status_text, style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.log_text = scrolledtext.ScrolledText(
            log_panel,
            height=24,
            wrap=tk.WORD,
            bg="#111c18",
            fg="#eaf5ee",
            insertbackground="#eaf5ee",
            relief=tk.FLAT,
            font=("Consolas", 10),
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.log_text.configure(state=tk.DISABLED)

    def _entry_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        browse_command: Callable[[], None] | None = None,
        show: str | None = None,
    ) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(parent, textvariable=variable, width=44, show=show or "")
        entry.grid(row=row, column=1, sticky="ew", pady=5, padx=(10, 6))
        if browse_command is not None:
            ttk.Button(parent, text="选择", command=browse_command).grid(row=row, column=2, sticky="ew", pady=5)

    def _button(
        self,
        parent: ttk.Frame,
        text: str,
        command: Callable[[], None],
        row: int,
        column: int,
        style: str = "TButton",
    ) -> None:
        button = ttk.Button(parent, text=text, command=command, style=style)
        button.grid(row=row, column=column, sticky="ew", padx=4, pady=5)
        self.buttons.append(button)

    def current_config(self) -> GitSyncConfig:
        return GitSyncConfig(
            repo_path=self.repo_path.get().strip() or str(default_repo_path()),
            remote_url=self.remote_url.get().strip(),
            branch=self.branch.get().strip() or DEFAULT_BRANCH,
            git_path=self.git_path.get().strip(),
            user_name=self.user_name.get().strip(),
            user_email=self.user_email.get().strip(),
            auth_username=self.auth_username.get().strip(),
            auth_token=self.auth_token.get().strip(),
            force_include_paths=self.force_include_paths.get().strip(),
            backend=self.backend.get().strip() or "auto",
        )

    def save_current_config(self) -> None:
        path = save_config(self.current_config())
        self.append_log(f"配置已保存：{path}")

    def choose_repo_path(self) -> None:
        chosen = filedialog.askdirectory(title="选择任意项目文件夹")
        if chosen:
            self.repo_path.set(chosen)

    def choose_git_path(self) -> None:
        chosen = filedialog.askopenfilename(
            title="选择 git.exe",
            filetypes=[("git.exe", "git.exe"), ("All files", "*.*")],
        )
        if chosen:
            self.git_path.set(chosen)

    def open_repo_folder(self) -> None:
        repo = Path(self.current_config().repo_path)
        repo.mkdir(parents=True, exist_ok=True)
        os.startfile(repo) if os.name == "nt" else webbrowser.open(repo.as_uri())

    def open_github(self) -> None:
        webbrowser.open(self.remote_url.get().strip() or GITHUB_HELP_URL)

    def start_detect(self) -> None:
        self.start_worker("检测中", lambda config, log: detect_environment(config, log))

    def start_pull(self) -> None:
        self.start_worker("拉取中", lambda config, log: pull_repository(config, log))

    def start_push(self) -> None:
        if not messagebox.askyesno(
            "确认推送",
            "确认把当前项目推送到远程仓库吗？\n\n同步器会先检查敏感文件，再自动提交和推送。",
        ):
            return
        message = self.commit_message.get()
        self.start_worker("推送中", lambda config, log: push_repository(config, message, log))

    def start_worker(
        self,
        status: str,
        operation: Callable[[GitSyncConfig, Callable[[str], None]], None],
    ) -> None:
        if self.worker is not None and self.worker.is_alive():
            messagebox.showinfo("正在运行", "当前已有任务在运行，请等它完成。")
            return
        config = self.current_config()
        save_config(config)
        self.set_busy(True, status)

        def run() -> None:
            try:
                operation(config, self.queue_log)
            except Exception as error:
                self.queue_log("操作失败：")
                self.queue_log(friendly_error_message(error))
                self.log_queue.put(("status", "失败"))
            else:
                self.log_queue.put(("status", "完成"))
            finally:
                self.log_queue.put(("busy", "0"))

        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def queue_log(self, text: str) -> None:
        self.log_queue.put(("log", text))

    def append_log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def set_busy(self, busy: bool, status: str | None = None) -> None:
        if status is not None:
            self.status_text.set(status)
        for button in self.buttons:
            button.configure(state=tk.DISABLED if busy else tk.NORMAL)

    def _poll_log_queue(self) -> None:
        while True:
            try:
                kind, value = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.append_log(value)
            elif kind == "status":
                self.status_text.set(value)
            elif kind == "busy":
                self.set_busy(False)
        self.root.after(120, self._poll_log_queue)

    def run(self) -> None:
        self.root.mainloop()


def run_self_check() -> int:
    config = load_config()
    payload = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "config": asdict(config),
        "system_git": shutil.which("git") or "",
        "builtin_git": has_builtin_git_backend(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    if "--self-check" in sys.argv:
        return run_self_check()
    if "--version" in sys.argv:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    GitSyncApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

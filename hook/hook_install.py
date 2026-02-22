"""
Claude Code Hook 安装 & 分发工具

- 无参数运行: 打开 Tkinter UI 界面，安装/卸载钩子
- 传入事件名运行: 分发到对应的 hook 脚本执行

用法:
    hook_install.exe                    # 打开 UI 界面
    hook_install.exe SessionStart       # 执行 SessionStart hook
    python hook_install.py              # 打开 UI 界面
    python hook_install.py PreToolUse   # 执行 PreToolUse hook
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 显式 import 所有 hook 模块，确保 PyInstaller 能收集依赖
# ============================================================
import SessionStart
import SessionEnd
import PreToolUse
import PostToolUse
import PermissionRequest
import Notification
import TaskCompleted
import Stop
import UserPromptSubmit

# 事件名 -> 模块映射（用于分发）
DISPATCH = {
    "SessionStart": SessionStart,
    "SessionEnd": SessionEnd,
    "PreToolUse": PreToolUse,
    "PostToolUse": PostToolUse,
    "PermissionRequest": PermissionRequest,
    "Notification": Notification,
    "TaskCompleted": TaskCompleted,
    "Stop": Stop,
    "UserPromptSubmit": UserPromptSubmit,
}

# Hook 事件定义: (事件名, 超时时间)
HOOK_EVENTS = [
    ("SessionStart", 10),
    ("SessionEnd", 10),
    ("PreToolUse", 10),
    ("PostToolUse", 10),
    ("PermissionRequest", 60),
    ("Notification", 10),
    ("TaskCompleted", 10),
    ("Stop", 10),
    ("UserPromptSubmit", 10),
]


# ============================================================
# Hook 分发逻辑
# ============================================================
def dispatch_hook(event_name):
    """根据事件名分发到对应的 hook 模块执行。"""
    module = DISPATCH.get(event_name)
    if module is None:
        print(f"Unknown event: {event_name}")
        sys.exit(1)
    module.run()


# ============================================================
# 安装/卸载逻辑
# ============================================================
def is_frozen():
    """判断当前是否为 PyInstaller 打包的可执行程序。"""
    return getattr(sys, 'frozen', False)


def get_self_path() -> str:
    """获取当前程序自身的路径（exe 或 py 脚本）。"""
    if is_frozen():
        return sys.executable
    else:
        return os.path.abspath(__file__)


def get_claude_global_settings_path() -> Path:
    """获取 Claude Code 全局配置文件路径（跨平台）。"""
    return Path.home() / ".claude" / "settings.json"


def detect_python_executable() -> str:
    """检测当前系统可用的 python 可执行文件名。"""
    current = sys.executable
    if current:
        try:
            subprocess.run(
                [current, "--version"],
                capture_output=True, timeout=5, check=True
            )
            return current
        except Exception:
            pass

    candidates = ["python3", "python", "py"]
    if platform.system() == "Windows":
        candidates = ["python", "py", "python3"]

    for name in candidates:
        try:
            result = subprocess.run(
                [name, "--version"],
                capture_output=True, timeout=5, check=True
            )
            if result.returncode == 0:
                return name
        except Exception:
            continue

    return ""


def build_hook_command(event_name: str) -> str:
    """
    构建单个 hook 的调用命令。
    - 可执行程序: "E:/path/hook_install.exe SessionStart"
    - Python 脚本: "C:/Python39/python.exe" "E:/path/hook_install.py SessionStart"
    """
    self_path = get_self_path().replace("\\", "/")

    if is_frozen():
        return f'"{self_path}" {event_name}'
    else:
        python_exe = detect_python_executable().replace("\\", "/")
        return f'"{python_exe}" "{self_path}" {event_name}'


def build_hooks_config() -> dict:
    """构建完整的 hooks 配置字典。"""
    hooks = {}
    for event_name, timeout in HOOK_EVENTS:
        command = build_hook_command(event_name)
        hooks[event_name] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": timeout,
                    }
                ]
            }
        ]
    return hooks


def backup_settings(settings_path: Path):
    """备份现有配置文件。"""
    if not settings_path.is_file():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = settings_path.with_name(f"settings.json.bak.{timestamp}")
    shutil.copy2(settings_path, backup_path)
    return backup_path


def load_settings(settings_path: Path) -> dict:
    """加载现有配置。"""
    if not settings_path.is_file():
        return {}
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(settings_path: Path, settings: dict):
    """保存配置文件。"""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def install_hooks() -> str:
    """安装 hooks，返回结果信息。"""
    settings_path = get_claude_global_settings_path()

    # 备份
    backup = backup_settings(settings_path)
    backup_msg = f"已备份: {backup.name}" if backup else "无需备份(新配置)"

    # 加载、合并、保存
    settings = load_settings(settings_path)
    new_hooks = build_hooks_config()
    settings["hooks"] = new_hooks
    save_settings(settings_path, settings)

    mode = "可执行程序" if is_frozen() else "Python 脚本"
    lines = [
        f"安装成功! ({mode}模式)",
        f"{backup_msg}",
        f"已注册 {len(new_hooks)} 个 hook 事件",
        f"配置文件: {settings_path}",
        "",
        "示例命令:",
        f"  {build_hook_command('SessionStart')}",
    ]
    return "\n".join(lines)


def uninstall_hooks() -> str:
    """卸载 hooks，返回结果信息。"""
    settings_path = get_claude_global_settings_path()

    if not settings_path.is_file():
        return "配置文件不存在，无需卸载。"

    # 查找最新备份
    backup_files = sorted(
        settings_path.parent.glob("settings.json.bak.*"),
        reverse=True,
    )

    if backup_files:
        latest_backup = backup_files[0]
        shutil.copy2(latest_backup, settings_path)
        return f"卸载成功!\n已从备份恢复: {latest_backup.name}"
    else:
        settings = load_settings(settings_path)
        if "hooks" in settings:
            del settings["hooks"]
            save_settings(settings_path, settings)
            return "卸载成功!\n已从配置中移除 hooks。"
        else:
            return "配置中不存在 hooks，无需卸载。"


# ============================================================
# Tkinter UI 界面
# ============================================================
def show_ui():
    """显示 Tkinter 安装/卸载界面。"""
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title("Claude Code Hook 管理工具")
    root.geometry("520x400")
    root.resizable(False, False)

    # --- 状态信息 ---
    info_frame = tk.LabelFrame(root, text="当前状态", padx=10, pady=5)
    info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

    mode_text = "可执行程序 (exe)" if is_frozen() else "Python 脚本"
    tk.Label(info_frame, text=f"运行模式:  {mode_text}", anchor="w").pack(fill=tk.X)

    self_path = get_self_path().replace("\\", "/")
    tk.Label(info_frame, text=f"程序路径:  {self_path}", anchor="w", wraplength=480).pack(fill=tk.X)

    settings_path = get_claude_global_settings_path()
    settings_exists = settings_path.is_file()
    has_hooks = False
    if settings_exists:
        s = load_settings(settings_path)
        has_hooks = "hooks" in s and len(s["hooks"]) > 0

    status = "已安装" if has_hooks else "未安装"
    tk.Label(info_frame, text=f"Hook 状态: {status}", anchor="w").pack(fill=tk.X)

    # --- 按钮 ---
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill=tk.X, padx=10, pady=5)

    # --- 输出区域 ---
    output_frame = tk.LabelFrame(root, text="输出", padx=5, pady=5)
    output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    output_text = scrolledtext.ScrolledText(output_frame, height=10, state=tk.DISABLED)
    output_text.pack(fill=tk.BOTH, expand=True)

    def append_output(msg):
        output_text.config(state=tk.NORMAL)
        output_text.insert(tk.END, msg + "\n")
        output_text.see(tk.END)
        output_text.config(state=tk.DISABLED)

    def on_install():
        try:
            result = install_hooks()
            append_output(result)
        except Exception as e:
            append_output(f"安装失败: {e}")

    def on_uninstall():
        try:
            result = uninstall_hooks()
            append_output(result)
        except Exception as e:
            append_output(f"卸载失败: {e}")

    tk.Button(btn_frame, text="安装 Hooks", command=on_install,
              width=20, height=2, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=(0, 10))
    tk.Button(btn_frame, text="卸载 Hooks", command=on_uninstall,
              width=20, height=2, bg="#f44336", fg="white").pack(side=tk.LEFT)

    root.mainloop()


# ============================================================
# 入口
# ============================================================
def main():
    args = sys.argv[1:]

    if not args:
        # 无参数 -> 打开 UI 界面
        show_ui()
    elif args[0] in DISPATCH:
        # 参数是 hook 事件名 -> 分发执行
        dispatch_hook(args[0])
    elif args[0] == "--help" or args[0] == "-h":
        print(__doc__)
    else:
        # print(f"未知参数: {args[0]}")
        # print(f"可用事件: {', '.join(DISPATCH.keys())}")
        sys.exit(0)


if __name__ == "__main__":
    main()
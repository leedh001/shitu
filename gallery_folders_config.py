# 图库工作区路径：读写项目根目录下的 gallery_folders.json

import json
from pathlib import Path
from typing import Optional

CONFIG_FILENAME = "gallery_folders.json"


def config_path() -> Path:
    return Path(__file__).resolve().parent / CONFIG_FILENAME


def _read_config_dict() -> dict:
    p = config_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_saved_workspace_root() -> Optional[str]:
    """配置里存在且磁盘上仍有效的路径则返回，否则 None（用于启动时是否自动加载图库）。"""
    data = _read_config_dict()
    path = data.get("last_workspace_root")
    if not path:
        folders = data.get("folders")
        if isinstance(folders, list) and folders:
            path = folders[-1]
    if not path or not isinstance(path, str):
        return None
    path = path.strip()
    if not path:
        return None
    resolved = Path(path)
    if resolved.is_dir():
        return str(resolved.resolve())
    return None


def load_workspace_root(default: str) -> str:
    """读取上次保存的工作区根路径；无效或缺失时返回 default。"""
    saved = get_saved_workspace_root()
    if saved is not None:
        return saved
    return default


def save_last_selected_folder(folder: str) -> None:
    """将当前选中的文件夹写入配置（作为 last_workspace_root，并维护 folders 列表）。"""
    folder = str(Path(folder).resolve())
    p = config_path()
    data: dict = {}
    if p.is_file():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except (OSError, json.JSONDecodeError):
            data = {}
    folders = data.get("folders")
    if not isinstance(folders, list):
        folders = []
    if folder not in folders:
        folders.append(folder)
    data["folders"] = folders
    data["last_workspace_root"] = folder
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

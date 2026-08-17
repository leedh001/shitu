"""按工作区根目录划分 Chroma 持久化路径，互不干扰。"""

from __future__ import annotations

import hashlib
from pathlib import Path


def chroma_db_path_for_workspace_root(workspace_root: str) -> str:
    """同一工作区始终映射到同一子目录；不同路径对应不同库。"""
    key = str(Path(workspace_root).resolve())
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    base = Path(__file__).resolve().parent / "db_data" / "workspaces" / digest
    base.mkdir(parents=True, exist_ok=True)
    return str(base)

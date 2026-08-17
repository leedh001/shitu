# 内容区侧栏「工作区」：仅文件夹树 + 打开根目录

import os
from pathlib import Path

from qt_core import *

from gallery_folders_config import load_workspace_root, save_last_selected_folder


def _paths_equal(a: str, b: str) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return os.path.normcase(a) == os.path.normcase(b)


class WorkspacePanel(QWidget):
    workspace_folder_chosen = Signal(str)

    def __init__(
        self,
        parent,
        app_parent,
        dark_one: str,
        bg_color: str,
        btn_color_hover: str,
        context_color: str,
        text_title_color: str,
    ):
        super().__init__(parent)
        self._parent = parent
        self._app_parent = app_parent
        self._dark_one = dark_one
        self._bg_color = bg_color
        self._btn_color_hover = btn_color_hover
        self._context_color = context_color
        self._text_title_color = text_title_color
        self._workspace_root: str = ""
        # 使用「父目录为根」模式时，用于 directoryLoaded 后再次隐藏同级
        self._workspace_parent: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.workspace_open_btn = QPushButton("打开文件夹…")
        self.workspace_open_btn.setCursor(Qt.PointingHandCursor)
        self.workspace_open_btn.setMaximumHeight(34)
        self.workspace_open_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self._dark_one};
                color: {self._text_title_color};
                border: 1px solid {self._bg_color};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {self._btn_color_hover};
            }}
            """
        )
        self.workspace_open_btn.clicked.connect(self._on_open_workspace_folder)

        self._fs_model = QFileSystemModel(self)
        self._fs_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self._fs_model.directoryLoaded.connect(self._on_fs_directory_loaded)

        root = load_workspace_root(QDir.homePath())

        self.workspace_tree = QTreeView(self)
        self.workspace_tree.setModel(self._fs_model)
        self._apply_workspace_root(root)
        self.workspace_tree.setHeaderHidden(True)
        for col in (1, 2, 3):
            self.workspace_tree.hideColumn(col)
        self.workspace_tree.setAnimated(True)
        self.workspace_tree.setIndentation(12)
        self.workspace_tree.setExpandsOnDoubleClick(False)
        self.workspace_tree.clicked.connect(self._on_workspace_tree_clicked)
        self.workspace_tree.setStyleSheet(
            f"""
            QTreeView {{
                background-color: {self._dark_one};
                color: {self._text_title_color};
                border: none;
                outline: none;
            }}
            QTreeView::item {{
                padding: 2px 0;
            }}
            QTreeView::item:selected {{
                background-color: {self._context_color};
                color: #f5f6f9;
            }}
            QTreeView::item:hover {{
                background-color: {self._btn_color_hover};
            }}
            """
        )
        self.workspace_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.workspace_open_btn)
        layout.addWidget(self.workspace_tree, 1)

    def _sync_workspace_sibling_visibility(self) -> None:
        """在父目录索引下只显示工作区文件夹一行（其余同级隐藏）。依赖模型已加载子行。"""
        if not self._workspace_parent or not self._workspace_root:
            return
        parent_index = self._fs_model.index(self._workspace_parent)
        if not parent_index.isValid():
            return
        ws = self._workspace_root
        for row in range(self._fs_model.rowCount(parent_index)):
            child = self._fs_model.index(row, 0, parent_index)
            fp = self._fs_model.filePath(child)
            if _paths_equal(fp, ws):
                self.workspace_tree.setRowHidden(row, parent_index, False)
                self.workspace_tree.expand(child)
            else:
                self.workspace_tree.setRowHidden(row, parent_index, True)

    def _on_fs_directory_loaded(self, path: str) -> None:
        if self._workspace_parent is None:
            return
        if not _paths_equal(path, self._workspace_parent):
            return
        self._sync_workspace_sibling_visibility()

    def _apply_workspace_root(self, workspace: str):
        """仅显示该目录及其子目录；树顶显示「当前目录」一行（父为根并隐藏同级）。"""
        workspace = str(Path(workspace).resolve())
        if not Path(workspace).is_dir():
            return

        self._workspace_root = workspace
        parent = str(Path(workspace).parent)

        if _paths_equal(workspace, parent):
            self._workspace_parent = None
            idx = self._fs_model.setRootPath(workspace)
            self.workspace_tree.setRootIndex(idx)
            return

        self._workspace_parent = parent
        parent_index = self._fs_model.setRootPath(parent)
        self.workspace_tree.setRootIndex(parent_index)

        # 子项可能尚未异步载入，立即同步一次 + 下一事件循环再同步 + directoryLoaded 再同步
        self._sync_workspace_sibling_visibility()
        QTimer.singleShot(0, self._sync_workspace_sibling_visibility)

    def _on_open_workspace_folder(self):
        start = self._workspace_root or self._fs_model.rootPath() or QDir.homePath()
        path = QFileDialog.getExistingDirectory(
            self._parent,
            "选择工作区文件夹",
            start,
        )
        if not path:
            return
        save_last_selected_folder(path)
        self._apply_workspace_root(path)
        # 与点击树中目录一致，通知主窗口刷新相册
        self.workspace_folder_chosen.emit(str(Path(path).resolve()))

    def _on_workspace_tree_clicked(self, index):
        if not index.isValid():
            return
        path = self._fs_model.filePath(index)
        save_last_selected_folder(path)
        self.workspace_folder_chosen.emit(path)

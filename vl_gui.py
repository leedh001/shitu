# ///////////////////////////////////////////////////////////////

#

# BY: WANDERSON M.PIMENTA

# PROJECT MADE WITH: Qt Designer and PySide6

# V: 1.0.0

#

# This project can be used freely for all uses, as long as they maintain the

# respective credits only in the Python scripts, any information in the visual

# interface (GUI) can be modified without any implication.

#

# There are limitations on Qt licenses if you want to use your products

# commercially, I recommend reading them on the official website:

# https://doc.qt.io/qtforpython/licenses.html

#

# ///////////////////////////////////////////////////////////////



# IMPORT PACKAGES AND MODULES

# ///////////////////////////////////////////////////////////////

from gui.uis.windows.main_window.functions_main_window import *

from gui.core.functions import Functions

import sys

import os

import threading

from pathlib import Path



# IMPORT QT CORE

# ///////////////////////////////////////////////////////////////

from qt_core import *



# IMPORT SETTINGS

# ///////////////////////////////////////////////////////////////

from gui.core.json_settings import Settings



# IMPORT PY ONE DARK WINDOWS

# ///////////////////////////////////////////////////////////////

# MAIN WINDOW

from gui.uis.windows.main_window import *



# IMPORT PY ONE DARK WIDGETS

# ///////////////////////////////////////////////////////////////

from gui.widgets import *



from vl_image_util import list_image_paths, list_subdirs_recursive
from vl_image_util import IMAGE_EXTS

from thumbnail_async import ThumbnailListModel, ThumbnailLoader, visible_and_prefetch_rows

from gallery_folders_config import get_saved_workspace_root

from vl_db import DbConfig

from vl_indexer import IndexConfig

from vl_tasks import IndexTaskQueue

from vl_workspace_db import chroma_db_path_for_workspace_root
from vl_db import VectorDb

from vl_llama_local import embed_text


class _SemanticSearchSignals(QObject):
    ready = Signal(int, list)
    failed = Signal(int, str)


# ADJUST QT FONT DPI FOR HIGHT SCALE AN 4K MONITOR

# ///////////////////////////////////////////////////////////////

# os.environ["QT_FONT_DPI"] = "96"

# IF IS 4K MONITOR ENABLE 'os.environ["QT_SCALE_FACTOR"] = "2"'



# MAIN WINDOW

# ///////////////////////////////////////////////////////////////

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.dragPos = QPoint()



        self.image_list = []

        self._index_queue = None

        self._semantic_total = 0

        self._semantic_indexed_ok = 0

        self._semantic_indexed_err = 0

        self._semantic_in_db_baseline = 0

        self._workspace_root = None
        self._img_sig_map = {}

        self._fs_watcher = QFileSystemWatcher(self)
        self._fs_watcher.directoryChanged.connect(self._on_workspace_dir_changed)
        self._fs_debounce = QTimer(self)
        self._fs_debounce.setSingleShot(True)
        self._fs_debounce.setInterval(600)
        self._fs_debounce.timeout.connect(self._refresh_workspace_dir_images)

        self._semantic_search_gen = 0

        self._semantic_search_bridge = _SemanticSearchSignals()

        self._semantic_search_bridge.ready.connect(self._on_semantic_search_ready)

        self._semantic_search_bridge.failed.connect(self._on_semantic_search_failed)

        self._semantic_index_timer = QTimer(self)

        self._semantic_index_timer.setInterval(400)

        self._semantic_index_timer.timeout.connect(self._poll_semantic_index_progress)

        self._semantic_index_timer.start()

        self._thumb_schedule_timer = QTimer(self)

        self._thumb_schedule_timer.setSingleShot(True)

        self._thumb_schedule_timer.setInterval(40)

        self._thumb_schedule_timer.timeout.connect(

            self._schedule_thumbnail_range_immediate

        )

        # SETUP MAIN WINDOw

        # Load widgets from "gui\uis\main_window\ui_main.py"

        # ///////////////////////////////////////////////////////////////

        self.ui = UI_MainWindow()

        self.ui.setup_ui(self)

        thumb_view = self.ui.load_pages.thumbnail_list

        isz = thumb_view.iconSize()

        thumb_px = max(1, isz.width(), isz.height())

        self._thumb_model = ThumbnailListModel(self, thumb_px=thumb_px)

        self._thumb_loader = ThumbnailLoader(max_side=thumb_px, parent=self)

        self._thumb_loader.thumbnail_ready.connect(self._on_thumbnail_ready)

        thumb_view.setModel(self._thumb_model)

        sb = thumb_view.verticalScrollBar()

        sb.valueChanged.connect(self._schedule_thumbnail_range_debounced)



        # LOAD SETTINGS

        # ///////////////////////////////////////////////////////////////

        settings = Settings()

        self.settings = settings.items



        # SETUP MAIN WINDOW

        # ///////////////////////////////////////////////////////////////

        self.hide_grips = True # Show/Hide resize grips

        SetupMainWindow.setup_gui(self)

        self.ui.title_bar.semantic_search.connect(self._request_semantic_search)

        self.ui.title_bar.set_gallery_count(0)

        self.ui.title_bar.set_semantic_index_counts(0, 0)

        saved = get_saved_workspace_root()
        if saved:
            QTimer.singleShot(0, lambda p=saved: self.load_images_from_directory(p))

        # SHOW MAIN WINDOW

        # ///////////////////////////////////////////////////////////////

        self.show()

    @staticmethod
    def _stat_sig(p: str):
        try:
            st = os.stat(p)
            mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
            size = int(st.st_size)
            return (mtime_ns, size)
        except Exception:
            return (None, None)

    def _sig_map_for_paths(self, paths: list[str]) -> dict:
        out = {}
        for p in paths:
            out[p] = self._stat_sig(p)
        return out

    @staticmethod
    def _norm_watch_path(path: str) -> str:
        try:
            return str(Path(path).resolve())
        except OSError:
            return os.path.normcase(os.path.abspath(path))

    def _clear_fs_watcher_paths(self) -> None:
        for p in list(self._fs_watcher.directories()):
            try:
                self._fs_watcher.removePath(p)
            except Exception:
                pass

    def _sync_workspace_watcher(self, root: str | None = None) -> None:
        """Register QFileSystemWatcher on workspace root and all subdirectories."""
        root = root or self._workspace_root
        if not root or not os.path.isdir(root):
            return
        root = self._norm_watch_path(root)
        wanted = {self._norm_watch_path(d) for d in list_subdirs_recursive(root)}
        current = {self._norm_watch_path(d) for d in self._fs_watcher.directories()}
        for p in sorted(wanted - current):
            if os.path.isdir(p):
                try:
                    self._fs_watcher.addPath(p)
                except Exception:
                    pass
        for p in sorted(current - wanted):
            try:
                self._fs_watcher.removePath(p)
            except Exception:
                pass

    def _set_watched_directory(self, directory: str | None) -> None:
        self._clear_fs_watcher_paths()
        if directory:
            self._sync_workspace_watcher(directory)

    def _on_workspace_dir_changed(self, _path: str) -> None:
        # New subdirs are not watched until we sync; then debounce image list refresh.
        self._sync_workspace_watcher()
        self._fs_debounce.start()

    def _refresh_workspace_dir_images(self) -> None:
        root = self._workspace_root
        if not root or not os.path.isdir(root):
            return

        new_paths = list_image_paths(root)
        old_paths = list(self.image_list or [])

        old_set = set(old_paths)
        new_set = set(new_paths)
        added = new_set - old_set
        removed = old_set - new_set

        # Detect updated files among kept paths via (mtime_ns, size).
        updated = set()
        kept = old_set & new_set
        for p in kept:
            old_sig = self._img_sig_map.get(p)
            cur_sig = self._stat_sig(p)
            if old_sig is None:
                continue
            if cur_sig != old_sig:
                updated.add(p)

        if not added and not removed and not updated:
            return

        # If the dir changed but image set didn't (e.g. non-image file edits), no-op.
        # However, some editors update mtime/size for images without changing file name;
        # updated handles that.

        # First, delete removed image ids from vector db.
        if removed:
            db_path = chroma_db_path_for_workspace_root(root)
            vdb = VectorDb(DbConfig(path=db_path, collection="images"))
            chunk = 256
            removed_list = list(removed)
            for i in range(0, len(removed_list), chunk):
                vdb.delete_ids(ids=removed_list[i : i + chunk])

        # Reset semantic search filter state to full gallery (avoid stale filtered model).
        self._semantic_search_gen += 1
        si = getattr(self.ui.title_bar, "search_input", None)
        if si is not None:
            si.blockSignals(True)
            si.clear()
            si.blockSignals(False)

        # Update gallery UI.
        self.image_list = new_paths
        self._img_sig_map = self._sig_map_for_paths(new_paths)
        self._thumb_loader.clear_inflight()
        self._thumb_model.set_paths(new_paths)
        self.ui.title_bar.set_gallery_count(len(new_paths))
        QTimer.singleShot(0, self._schedule_thumbnail_range_immediate)

        # Recompute pending/baseline and submit new/changed tasks.
        self._rebuild_workspace_semantic_index(root)



    # LEFT MENU BTN IS CLICKED

    # Run function when btn is clicked

    # Check funtion by object name / btn_id

    # ///////////////////////////////////////////////////////////////

    def btn_clicked(self, btn=None):

        # Title bar / left column signals pass the emitting button as first arg (Signal(object)).
        if btn is None:
            btn = self.sender()
        if btn is None:
            return



        btn_workspace = MainFunctions.get_title_bar_btn(self, "btn_workspace")

        if btn_workspace is not None and btn.objectName() != "btn_workspace":

            btn_workspace.set_active(False)

        top_bar_settings = MainFunctions.get_title_bar_btn(self, "btn_top_settings")

        if top_bar_settings is not None and btn.objectName() != "btn_top_settings":

            top_bar_settings.set_active(False)



        # Left column close

        if btn.objectName() == "btn_close_left_column":

            MainFunctions.toggle_left_column(self)

            print(f"Button {btn.objectName()}, clicked!")

            return



        rc_menus = self.ui.right_column.menus

        # TITLE BAR: 工作区 — toggle_right_column，内容在 menu_1（布局上在内容区左侧）

        if btn.objectName() == "btn_workspace":

            if not MainFunctions.right_column_is_visible(self):

                btn.set_active(True)

                if top_bar_settings is not None:

                    top_bar_settings.set_active(False)

                MainFunctions.set_right_column_menu(self, self.ui.right_column.menu_1)

                MainFunctions.toggle_right_column(self)

            else:

                if rc_menus.currentWidget() == self.ui.right_column.menu_1:

                    btn.set_active(False)

                    MainFunctions.toggle_right_column(self)

                else:

                    btn.set_active(True)

                    if top_bar_settings is not None:

                        top_bar_settings.set_active(False)

                    MainFunctions.set_right_column_menu(self, self.ui.right_column.menu_1)

            print(f"Button {btn.objectName()}, clicked!")

            return



        if btn.objectName() == "btn_top_settings":

            if not MainFunctions.right_column_is_visible(self):

                btn.set_active(True)

                if btn_workspace is not None:

                    btn_workspace.set_active(False)

                MainFunctions.set_right_column_menu(self, self.ui.right_column.menu_2)

                MainFunctions.toggle_right_column(self)

            else:

                if rc_menus.currentWidget() == self.ui.right_column.menu_2:

                    btn.set_active(False)

                    MainFunctions.toggle_right_column(self)

                else:

                    btn.set_active(True)

                    if btn_workspace is not None:

                        btn_workspace.set_active(False)

                    MainFunctions.set_right_column_menu(self, self.ui.right_column.menu_2)

        if btn.objectName() == "btn_search":
            print(f"Button {btn.objectName()}, clicked!")
            return



        # DEBUG

        print(f"Button {btn.objectName()}, clicked!")



    # LEFT MENU BTN IS RELEASED

    # Run function when btn is released

    # Check funtion by object name / btn_id

    # ///////////////////////////////////////////////////////////////

    def btn_released(self, btn=None):

        if btn is None:
            btn = self.sender()
        if btn is None:
            return

        # DEBUG

        print(f"Button {btn.objectName()}, released!")



    # RESIZE EVENT

    # ///////////////////////////////////////////////////////////////

    def resizeEvent(self, event):

        SetupMainWindow.resize_grips(self)

        super().resizeEvent(event)

        self._schedule_thumbnail_range_debounced()



    # MOUSE CLICK EVENTS

    # ///////////////////////////////////////////////////////////////

    def mousePressEvent(self, event):

        # SET DRAG POS WINDOW

        self.dragPos = event.globalPosition().toPoint()



    def load_images_from_directory(self, directory):

        MainFunctions.set_page(self, self.ui.load_pages.page_3)

        self._semantic_search_gen += 1

        self._workspace_root = str(Path(directory).resolve())
        self._set_watched_directory(self._workspace_root)

        self.image_list = list_image_paths(self._workspace_root)
        self._img_sig_map = self._sig_map_for_paths(self.image_list)

        self._thumb_loader.clear_inflight()

        self._thumb_model.set_paths(self.image_list)

        self.ui.title_bar.set_gallery_count(len(self.image_list))

        si = getattr(self.ui.title_bar, "search_input", None)
        if si is not None:
            si.blockSignals(True)
            si.clear()
            si.blockSignals(False)

        if self.image_list:
            self.current_index = 0

        QTimer.singleShot(0, self._schedule_thumbnail_range_immediate)

        self._rebuild_workspace_semantic_index(directory)



    def _update_semantic_index_labels(self) -> None:
        pending = self._semantic_total - self._semantic_indexed_ok - self._semantic_indexed_err
        if pending < 0:
            pending = 0
        in_db = self._semantic_in_db_baseline + self._semantic_indexed_ok
        self.ui.title_bar.set_semantic_index_counts(pending, in_db)



    def _poll_semantic_index_progress(self) -> None:
        if self._index_queue is None:
            return
        for ev in self._index_queue.poll_events(max_items=200):
            if ev.status == "done":
                self._semantic_indexed_ok += 1
            elif ev.status == "error":
                self._semantic_indexed_err += 1
        self._update_semantic_index_labels()



    def _rebuild_workspace_semantic_index(self, directory: str) -> None:
        """关闭旧索引队列，按工作区目录使用独立 Chroma 库并提交当前相册图片任务。"""
        root = str(Path(directory).resolve())
        if self._index_queue is not None:
            self._index_queue.close(timeout_s=120)
            self._index_queue = None

        # Filter: skip already-indexed & unchanged; reindex if file changed.
        db_path = chroma_db_path_for_workspace_root(root)
        vdb = VectorDb(DbConfig(path=db_path, collection="images"))

        def _stat_sig(p: str):
            try:
                st = os.stat(p)
                mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
                size = int(st.st_size)
                return (mtime_ns, size)
            except Exception:
                return (None, None)

        to_index: list[str] = []
        skipped_unchanged = 0
        reindex_changed = 0

        CHUNK = 256
        paths = list(self.image_list or [])
        for i in range(0, len(paths), CHUNK):
            chunk = paths[i : i + CHUNK]
            metas = vdb.get_metadatas(ids=chunk)
            for p in chunk:
                md = metas.get(p)
                if md is None:
                    to_index.append(p)
                    continue
                # Old records may not have version fields -> reindex once to backfill.
                if not isinstance(md, dict):
                    to_index.append(p)
                    reindex_changed += 1
                    continue

                old_m = md.get("src_mtime_ns")
                old_s = md.get("src_size")
                if old_m is None or old_s is None:
                    to_index.append(p)
                    reindex_changed += 1
                    continue

                cur_m, cur_s = _stat_sig(p)
                if cur_m == int(old_m) and cur_s == int(old_s):
                    skipped_unchanged += 1
                else:
                    to_index.append(p)
                    reindex_changed += 1

        self._semantic_in_db_baseline = skipped_unchanged
        self._semantic_total = len(to_index)
        self._semantic_indexed_ok = 0
        self._semantic_indexed_err = 0
        self._update_semantic_index_labels()
        if not to_index:
            return
        cfg = IndexConfig(db=DbConfig(path=db_path, collection="images"))
        self._index_queue = IndexTaskQueue(cfg=cfg, workers=1)
        self._index_queue.start()
        self._index_queue.submit(to_index)



    def _schedule_thumbnail_range_debounced(self):

        self._thumb_schedule_timer.start()



    def _schedule_thumbnail_range_immediate(self) -> None:

        view = self.ui.load_pages.thumbnail_list

        model = self._thumb_model

        gen = model.generation

        for row in visible_and_prefetch_rows(view, model):

            self._thumb_loader.request(row, gen, model.path_at(row))



    def _on_thumbnail_ready(self, row: int, gen: int, image) -> None:

        self._thumb_model.set_thumbnail(row, image, gen)



    def _apply_semantic_search_results(self, gen: int, paths: list) -> None:

        if gen != self._semantic_search_gen:

            return

        self._thumb_model.set_paths(paths)

        self._thumb_loader.clear_inflight()

        self.ui.title_bar.set_gallery_count(len(paths))

        QTimer.singleShot(0, self._schedule_thumbnail_range_immediate)



    def _on_semantic_search_ready(self, gen: int, paths: list) -> None:

        self._apply_semantic_search_results(gen, paths)



    def _on_semantic_search_failed(self, gen: int, msg: str) -> None:

        if gen != self._semantic_search_gen:

            return

        print(f"semantic search failed: {msg}")



    def _request_semantic_search(self, text: str) -> None:

        text = (text or "").strip()

        if not text:

            self._semantic_search_gen += 1

            gen = self._semantic_search_gen

            self._apply_semantic_search_results(gen, list(self.image_list))

            return

        if not self._workspace_root or not self.image_list:

            return

        self._semantic_search_gen += 1

        gen = self._semantic_search_gen

        root = self._workspace_root

        gallery = list(self.image_list)

        def work() -> None:

            try:

                db_path = chroma_db_path_for_workspace_root(root)

                cfg = IndexConfig(db=DbConfig(path=db_path, collection="images"))

                vdb = VectorDb(cfg.db)

                print("vl_gui.py text: ", text)
                vec = embed_text(text, model=cfg.embed_model)

                n_results = min(120, max(10, len(gallery)))

                res = vdb.query(embedding=vec, n_results=n_results)

                raw_ids = (res.get("ids") or [[]])[0]

                gallery_set = set(gallery)

                ordered = [p for p in raw_ids if p in gallery_set]

                self._semantic_search_bridge.ready.emit(gen, ordered)

            except Exception as e:

                self._semantic_search_bridge.failed.emit(gen, str(e))

        threading.Thread(target=work, daemon=True).start()





# SETTINGS WHEN TO START

# Set the initial class and also additional parameters of the "QApplication" class

# ///////////////////////////////////////////////////////////////

if __name__ == "__main__":

    # APPLICATION

    # ///////////////////////////////////////////////////////////////

    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon("icon.ico"))

    window = MainWindow()



    # EXEC APP

    # ///////////////////////////////////////////////////////////////

    sys.exit(app.exec())


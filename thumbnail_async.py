"""Async thumbnail pipeline: QAbstractListModel + QThreadPool + cache + visible-first scheduling."""

from __future__ import annotations

import os
from collections import OrderedDict

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QPoint,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    Signal,
)
from PySide6.QtGui import QIcon, QImage, QImageReader, QPixmap
from PySide6.QtWidgets import QListView

from vl_image_util import load_thumbnail_pil


def _thumbnail_qimage_pil(path: str, max_side: int) -> QImage | None:
    try:
        pil_img = load_thumbnail_pil(path, (max_side, max_side))
        w, h = pil_img.size
        data = pil_img.tobytes("raw", "RGBA")
        # Explicit bytesPerLine to avoid stride-related cropping on some platforms.
        q = QImage(data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        # q.setDevicePixelRatio(1.0)
        return q
    except Exception:
        return None


def read_thumbnail_qimage(path: str, max_side: int) -> QImage | None:
    """QImageReader (EXIF + scaled read); PIL fallback for unsupported formats."""
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    if reader.canRead():
        sz = reader.size()
        if sz.isValid() and sz.width() > 0 and sz.height() > 0:
            w, h = sz.width(), sz.height()
            if w >= h:
                tw = max_side
                th = max(1, int(round(h * max_side / w)))
            else:
                th = max_side
                tw = max(1, int(round(w * max_side / h)))
            reader.setScaledSize(QSize(w, h))
        img = reader.read()
        if not img.isNull():
            # Normalize format/ownership to make icon rendering deterministic.
            img = img.convertToFormat(QImage.Format.Format_RGBA8888).copy()
            # img.setDevicePixelRatio(1.0)
            return img
    pil = _thumbnail_qimage_pil(path, max_side)
    # if pil is not None and not pil.isNull():
        # pil.setDevicePixelRatio(1.0)
    return pil


class ThumbnailCache:
    def __init__(self, max_entries: int = 400):
        self._max = max_entries
        self._data: OrderedDict[tuple, QImage] = OrderedDict()

    @staticmethod
    def make_key(path: str, max_side: int) -> tuple:
        try:
            m = int(os.path.getmtime(path))
        except OSError:
            m = 0
        return (os.path.normcase(os.path.abspath(path)), m, max_side)

    def get(self, key: tuple) -> QImage | None:
        img = self._data.get(key)
        if img is not None:
            self._data.move_to_end(key)
        return img

    def put(self, key: tuple, image: QImage) -> None:
        self._data[key] = image
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)


class _RunnableSignals(QObject):
    done = Signal(int, int, object, object)  # row, generation, QImage|None, path


class _ThumbnailRunnable(QRunnable):
    def __init__(
        self,
        row: int,
        generation: int,
        path: str,
        max_side: int,
        sigs: _RunnableSignals,
    ):
        super().__init__()
        self.setAutoDelete(True)
        self._row = row
        self._generation = generation
        self._path = path
        self._max_side = max_side
        self._sigs = sigs

    def run(self) -> None:
        img = read_thumbnail_qimage(self._path, self._max_side)
        self._sigs.done.emit(self._row, self._generation, img, self._path)


class ThumbnailLoader(QObject):
    """
    QThreadPool-backed loads; emits thumbnail_ready(row, generation, QImage) on GUI thread.
    """

    thumbnail_ready = Signal(int, int, QImage)

    def __init__(self, max_side: int = 200, parent: QObject | None = None):
        super().__init__(parent)
        self._max_side = max_side
        self._pool = QThreadPool.globalInstance()
        self._cache = ThumbnailCache()
        self._inflight: set[tuple[int, int]] = set()
        self._sigs = _RunnableSignals()
        self._sigs.done.connect(self._on_worker_done)

    def set_max_side(self, max_side: int) -> None:
        self._max_side = max_side

    def clear_inflight(self) -> None:
        self._inflight.clear()

    def request(self, row: int, generation: int, path: str) -> None:
        if not path:
            return
        key = ThumbnailCache.make_key(path, self._max_side)
        hit = self._cache.get(key)
        if hit is not None and not hit.isNull():
            self.thumbnail_ready.emit(row, generation, hit)
            return
        t = (generation, row)
        if t in self._inflight:
            return
        self._inflight.add(t)
        self._pool.start(
            _ThumbnailRunnable(row, generation, path, self._max_side, self._sigs)
        )

    def _on_worker_done(self, row: int, generation: int, img: object, path: object) -> None:
        self._inflight.discard((generation, row))
        if not isinstance(path, str) or img is None or not isinstance(img, QImage) or img.isNull():
            return
        key = ThumbnailCache.make_key(path, self._max_side)
        self._cache.put(key, img)
        self.thumbnail_ready.emit(row, generation, img)


FilePathRole = Qt.ItemDataRole.UserRole + 1


class ThumbnailListModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None, thumb_px: int = 200):
        super().__init__(parent)
        self._thumb_px = max(1, int(thumb_px))
        self._paths: list[str] = []
        self._icons: list[QIcon] = []
        self.generation = 0

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._paths)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._paths):
            return None
        row = index.row()
        if role == Qt.ItemDataRole.DisplayRole:
            return os.path.basename(self._paths[row])
        if role == Qt.ItemDataRole.DecorationRole:
            if row < len(self._icons):
                return self._icons[row]
            return QIcon()
        if role == FilePathRole:
            return self._paths[row]
        if role == Qt.ItemDataRole.SizeHintRole:
            return QSize(200, 220)
        return None

    def path_at(self, row: int) -> str:
        if 0 <= row < len(self._paths):
            return self._paths[row]
        return ""

    def set_paths(self, paths: list[str]) -> None:
        self.beginResetModel()
        self.generation += 1
        self._paths = list(paths)
        self._icons = [QIcon() for _ in self._paths]
        self.endResetModel()

    def set_thumbnail(self, row: int, image: QImage, gen: int) -> bool:
        if gen != self.generation:
            return False
        if row < 0 or row >= len(self._paths):
            return False
        # image.setDevicePixelRatio(1.0)
        pm = QPixmap.fromImage(image)
        # pm.setDevicePixelRatio(1.0)
        tp = self._thumb_px
        if pm.width() != tp or pm.height() != tp:
            pm = pm.scaled(
                tp,
                tp,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            # pm.setDevicePixelRatio(1.0)
        self._icons[row] = QIcon(pm)
        idx = self.index(row, 0)
        self.dataChanged.emit(
            idx,
            idx,
            [Qt.ItemDataRole.DecorationRole],
        )
        return True


def visible_and_prefetch_rows(
    view: QListView,
    model: ThumbnailListModel,
    prefetch_extra: int = 24,
    max_rows_per_tick: int = 500,
) -> list[int]:
    n = model.rowCount(QModelIndex())
    if n <= 0:
        return []

    vp = view.viewport()
    rect = vp.rect()
    grid_h = max(1, view.gridSize().height())
    pad = grid_h * 3
    rect = rect.adjusted(0, -pad, 0, pad)

    rows: set[int] = set()
    step_x = max(60, view.gridSize().width() // 2)
    step_y = max(40, grid_h // 2)
    for y in range(rect.top(), rect.bottom(), step_y):
        for x in range(rect.left(), rect.right(), step_x):
            idx = view.indexAt(QPoint(x, y))
            if idx.isValid():
                rows.add(idx.row())

    if not rows:
        cap = min(n, max(48, (rect.width() // max(1, view.gridSize().width()) + 2) * 6))
        for r in range(cap):
            rows.add(r)

    expanded: set[int] = set()
    for r in rows:
        lo = max(0, r - prefetch_extra)
        hi = min(n - 1, r + prefetch_extra)
        for rr in range(lo, hi + 1):
            expanded.add(rr)

    vis_ordered = sorted(rows)
    rest = sorted(expanded - rows)
    ordered = vis_ordered + rest
    if len(ordered) > max_rows_per_tick:
        ordered = ordered[:max_rows_per_tick]
    return ordered

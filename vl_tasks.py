from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set, Tuple

from vl_indexer import ImageIndexer, IndexConfig, IndexResult


@dataclass(frozen=True)
class TaskEvent:
    image_path: str
    status: str  # "queued" | "running" | "done" | "error"
    result: Optional[IndexResult] = None


class IndexTaskQueue:
    """
    Background priority queue for indexing tasks.
    priority: smaller number = higher priority (0 is highest).
    """

    def __init__(self, *, cfg: IndexConfig = IndexConfig(), workers: int = 1):
        self.indexer = ImageIndexer(cfg)
        self._q: "queue.PriorityQueue[Tuple[int, str]]" = queue.PriorityQueue()
        self._events: "queue.Queue[TaskEvent]" = queue.Queue()
        self._stop = threading.Event()
        self._workers = max(1, int(workers))
        self._threads: list[threading.Thread] = []

        self._seen: Set[str] = set()
        self._running: Set[str] = set()
        self._lock = threading.Lock()

    def start(self) -> None:
        if any(t.is_alive() for t in self._threads):
            return
        self._stop.clear()
        self._threads = []
        for _ in range(self._workers):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        """
        Request workers to stop after the current task finishes.
        Note: this does not interrupt an in-flight index_one() call.
        """
        self._stop.set()

    def abort_pending(self) -> None:
        """丢弃队列中尚未开始执行的任务（已取出的仍会跑完）。"""
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def wait(self, timeout_s: Optional[float] = None) -> bool:
        """
        Wait for all worker threads to exit.
        Returns True if all workers stopped; False if timed out.
        """
        # Use monotonic for timeout accounting.
        end_t: Optional[float] = None
        if timeout_s is not None:
            import time

            end_t = time.monotonic() + float(timeout_s)

        for t in list(self._threads):
            if end_t is None:
                t.join()
            else:
                import time

                remaining = end_t - time.monotonic()
                if remaining <= 0:
                    return False
                t.join(timeout=remaining)
                if t.is_alive():
                    return False
        return True

    def close(self, timeout_s: Optional[float] = None) -> bool:
        """
        清空待处理队列后停止 worker，并等待结束（进行中的 index_one 仍会写完）。
        """
        self.abort_pending()
        self.stop()
        return self.wait(timeout_s=timeout_s)

    def submit(self, image_paths: Iterable[str], *, priority: int = 10) -> int:
        """
        Submit tasks, with de-duplication by image_path.
        Returns how many were newly queued.
        """
        added = 0
        for p in image_paths:
            if not p:
                continue
            with self._lock:
                if p in self._seen or p in self._running:
                    continue
                self._seen.add(p)
            self._q.put((int(priority), p))
            self._events.put(TaskEvent(image_path=p, status="queued"))
            added += 1
        return added

    def poll_events(self, *, max_items: int = 50) -> list[TaskEvent]:
        out: list[TaskEvent] = []
        for _ in range(max_items):
            try:
                out.append(self._events.get_nowait())
            except queue.Empty:
                break
        return out

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                _prio, path = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            if self._stop.is_set():
                break

            with self._lock:
                self._running.add(path)

            self._events.put(TaskEvent(image_path=path, status="running"))
            res = self.indexer.index_one(path)
            self._events.put(
                TaskEvent(image_path=path, status="done" if res.ok else "error", result=res)
            )

            with self._lock:
                self._running.discard(path)


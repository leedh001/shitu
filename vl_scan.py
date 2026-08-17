import os
from typing import Iterable, List, Sequence, Tuple


DEFAULT_EXTS: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def list_images_recursive(folder: str, exts: Sequence[str] = DEFAULT_EXTS) -> List[str]:
    """
    Recursively walk a folder and return sorted image paths.
    """
    out: List[str] = []
    for root, _, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(tuple(exts)):
                out.append(os.path.join(root, name))
    out.sort()
    return out


def iter_images_recursive(folder: str, exts: Sequence[str] = DEFAULT_EXTS) -> Iterable[str]:
    """
    Generator variant (no sorting). Useful for streaming/large folders.
    """
    for root, _, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(tuple(exts)):
                yield os.path.join(root, name)


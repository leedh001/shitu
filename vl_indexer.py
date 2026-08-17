from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from vl_image_util import get_image_data
from vl_llama_local import DEFAULT_EMBED_MODEL, DEFAULT_VLM_MODEL, describe_image_base64, embed_text
from vl_db import DbConfig, VectorDb


@dataclass(frozen=True)
class IndexConfig:
    db: DbConfig = DbConfig()
    vlm_model: str = DEFAULT_VLM_MODEL
    embed_model: str = DEFAULT_EMBED_MODEL
    prompt: str = "用连贯的中文，严格控制在200字以内（包括空格，标点符号），详细描述这张图片的内容，包括主要物体、场景、颜色、文字信息以及整体氛围。/no_think"


@dataclass(frozen=True)
class IndexResult:
    image_path: str
    ok: bool
    desc: Optional[str] = None
    embedding_dim: Optional[int] = None
    error: Optional[str] = None
    elapsed_s: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ImageIndexer:
    def __init__(self, cfg: IndexConfig = IndexConfig()):
        self.cfg = cfg
        self.db = VectorDb(cfg.db)

    def index_one(self, image_path: str) -> IndexResult:
        t0 = time.time()
        t1 = time.time()
        try:
            try:
                st = os.stat(image_path)
                src_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
                src_size = int(st.st_size)
            except Exception:
                src_mtime_ns = None
                src_size = None

            img_meta_data = get_image_data(image_path)
            t1 = time.time()
            try:
                data = json.loads(img_meta_data)
            except json.JSONDecodeError:
                return IndexResult(
                    image_path=image_path,
                    ok=False,
                    error=f"invalid_json_from_get_image_data: {img_meta_data}",
                    elapsed_s=time.time() - t0,
                )

            if not data.get("ok"):
                return IndexResult(
                    image_path=image_path,
                    ok=False,
                    error=str(data.get("error") or "get_image_data_failed"),
                    elapsed_s=time.time() - t0,
                    metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
                )

            b64 = data.get("base64")
            if not isinstance(b64, str) or not b64:
                return IndexResult(
                    image_path=image_path,
                    ok=False,
                    error="missing_base64",
                    elapsed_s=time.time() - t0,
                    metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
                )
            t1 = time.time()
            desc, metrics, _raw = describe_image_base64(
                b64,
                model=self.cfg.vlm_model,
                prompt=self.cfg.prompt,
                think=False,
            )
            print(f"耗时定位............001>>: {time.time() - t1}")
            t1 = time.time()
            vec = embed_text(desc, model=self.cfg.embed_model)
            print(f"耗时定位............002>>: {time.time() - t1}")
            raw_meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else None
            # Chroma metadata values must be str/int/float/bool/None (no nested dict).
            image_meta_json: Optional[str] = None
            if raw_meta:
                try:
                    image_meta_json = json.dumps(raw_meta, ensure_ascii=False)
                except (TypeError, ValueError):
                    image_meta_json = None
            db_meta: Dict[str, Any] = {
                "image_path": image_path,
                "src_mtime_ns": src_mtime_ns,
                "src_size": src_size,
                "image_meta_json": image_meta_json,
                "indexed_at_s": time.time(),
                "embed_model": self.cfg.embed_model,
                "vlm_model": self.cfg.vlm_model,
            }
            self.db.upsert(id=image_path, embedding=vec, document=desc, metadata=db_meta)

            print(f"image_path: {image_path}")
            print(f"耗时定位............003>>: {time.time() - t1}")

            return IndexResult(
                image_path=image_path,
                ok=True,
                desc=desc,
                embedding_dim=len(vec) if hasattr(vec, "__len__") else None,
                elapsed_s=time.time() - t0,
                metadata={
                    "image": raw_meta,
                    "metrics": {
                        "total_duration_s": metrics.total_duration_s,
                        "prompt_eval_count": metrics.prompt_eval_count,
                        "eval_count": metrics.eval_count,
                    },
                },
            )
        except Exception as e:
            print(f"{e}")
            return IndexResult(
                image_path=image_path,
                ok=False,
                error=str(e),
                elapsed_s=time.time() - t0,
            )


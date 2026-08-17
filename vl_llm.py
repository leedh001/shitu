from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import ollama


DEFAULT_VLM_MODEL = "qwen3.5:2b"
DEFAULT_EMBED_MODEL = "embeddinggemma"


@dataclass(frozen=True)
class DescribeMetrics:
    total_duration_s: Optional[float] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


def describe_image_base64(
    image_b64: str,
    *,
    model: str = DEFAULT_VLM_MODEL,
    prompt: str = "用连贯的中文，严格控制在200字以内（包括空格，标点符号），详细描述这张图片的内容，包括主要物体、场景、颜色、文字信息以及整体氛围。/no_think",
    think: bool = False,
) -> tuple[str, DescribeMetrics, Dict[str, Any]]:
    """
    Call a VLM via Ollama chat API with a single base64 image.
    Returns (description, metrics, raw_response).
    """
    response = ollama.chat(
        model=model,
        stream=False,
        think=think,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
    )
    content = response["message"]["content"]
    metrics = DescribeMetrics(
        total_duration_s=(response.get("total_duration") / 1e9) if response.get("total_duration") else None,
        prompt_eval_count=response.get("prompt_eval_count"),
        eval_count=response.get("eval_count"),
    )
    return content, metrics, response


def embed_text(
    text: str,
    *,
    model: str = DEFAULT_EMBED_MODEL,
) -> List[float]:
    """
    Generate an embedding vector for a single text input.
    """
    res = ollama.embed(model=model, input=text)
    return res["embeddings"][0]


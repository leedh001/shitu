from __future__ import annotations
from dataclasses import dataclass
import sys
import os
from typing import Any, Dict, List, Optional
from llama_cpp import Llama
from llama_cpp.llama_chat_format import MTMDChatHandler, Qwen35ChatHandler  # 引入多模态对话处理器
from llama_cpp.llama_embedding import LlamaEmbedding, LLAMA_POOLING_TYPE_NONE
from llama_cpp.llama_embedding import (
  LLAMA_POOLING_TYPE_NONE,
  NORM_MODE_MAX_INT16,
  NORM_MODE_TAXICAB,
  NORM_MODE_EUCLIDEAN
)

DEFAULT_VLM_MODEL = "Qwen3.5-2B-Q8_0.gguf"
DEFAULT_EMBED_MODEL = "embeddinggemma-300M-BF16.gguf"

def resource_path(relative_path):
    """获取资源绝对路径，兼容开发环境和打包环境"""
    try:
        # PyInstaller 打包后会创建临时文件夹，路径存在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# chat_handler = Qwen3VLChatHandler(
#     clip_model_path=resource_path( os.path.join("model", "mmproj-F16.gguf") ),
#     verbose=False
# )

# 1. 加载模型
# 请将路径替换为你本地 .gguf 模型文件的实际路径
# llm = Llama(
#     model_path=resource_path( os.path.join("model", "Qwen3.5-2B-Q8_0.gguf") ),
#     # chat_handler=chat_handler,
#     n_gpu_layers=-1,  # -1 表示将所有层都加载到 GPU (如果有)，以加速推理
#     n_ctx=10240,       # 上下文窗口大小，可根据你的内存调整
#     verbose=False,     # 关闭加载时的详细日志
#     swa_full=True
# )

llm = Llama(
    model_path=resource_path( os.path.join("model", "Qwen3.5-2B-Q8_0.gguf") ),
    chat_handler=MTMDChatHandler(clip_model_path=resource_path( os.path.join("model", "mmproj-F16.gguf") ),verbose=False),
    n_ctx=4096,
    enable_thinking=False,
    verbose=False,
    ctx_checkpoints=0  # <-- SET THIS TO 0 TO ENABLE ZERO-LATENCY FAST PATH
)

# embed_llm = Llama(
#     model_path=resource_path( os.path.join("model", "embeddinggemma-300M-BF16.gguf") ),
#     n_gpu_layers=-1,  # -1 表示将所有层都加载到 GPU (如果有)，以加速推理
#     n_ctx=4096,       # 上下文窗口大小，可根据你的内存调整
#     verbose=False,     # 关闭加载时的详细日志
#     embeddings=True
# )

embed_llm = LlamaEmbedding(
    model_path=resource_path( os.path.join("model", "bge-m3-Q2_K.gguf") ), 
    n_gpu_layers=-1, 
    verbose=False,
    pooling_type=LLAMA_POOLING_TYPE_NONE
)


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
    response = llm.create_chat_completion(
        stream=False,
        temperature=0.9,    # 控制生成的随机性
        max_tokens=1024,     # 限制生成的最大 token 数
        messages = [
            {"role": "system", "content": "你是一个能够完美描述图片的助手。"},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}" }},
                    {"type" : "text", "text": prompt}
                ]
            }
        ],
    )
    # print("vl_llama_local.py response: ", response)
    content = response['choices'][0]['message']['content']
    metrics = DescribeMetrics(
        # total_duration_s=(response.get("total_duration") / 1e9) if response.get("total_duration") else None,
        # prompt_eval_count=response.get("prompt_eval_count"),
        # eval_count=response.get("eval_count"),
        total_duration_s=2,
        prompt_eval_count=0,
        eval_count=0,
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
    print("vl_llama_local.py embed_text text: ", text)
    # response = embed_llm.create_embedding(text, output_format="array")
    response = embed_llm.embed(text, normalize=NORM_MODE_EUCLIDEAN)
    print("vl_llama_local.py embed_text len(response[0]): ", len(response[0]))
    return response[0]
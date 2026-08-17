import os
import json
import asyncio
import time
import ollama
import chromadb

from vl_image_util import get_image_data

DB_PATH = "./db_data" 

dir_path = "E:/BaiduNetdiskDownload/C1878/0图标切图"

def retrieval(image_path: str) -> None:
    t0 = time.time()
    print(f"retrieving {image_path}")
    img_meta_data = get_image_data(image_path)
    try:
        data = json.loads(img_meta_data)
    except json.JSONDecodeError:
        data = {"error": img_meta_data}
    
    b64 = data.get("base64")
    response = ollama.chat(
        model="qwen3.5:0.8b",
        stream=False,
        think=False,
        messages=[
            {
                "role": "user", 
                "content": "用连贯的中文，严格控制在200字以内（包括空格，标点符号），详细描述这张图片的内容，包括主要物体、场景、颜色、文字信息以及整体氛围。/no_think",
                "images": [b64],
            }
        ],
    )
    assistant_message = response['message']['content']
    print(f"\n=== 模型描述 ===\n{assistant_message}")
    print(f"\n=== 性能指标 ===")
    # print(f"总耗时: {response.get('total_duration') / 1e9:.2f} 秒")
    print(f"总耗时: {time.time() - t0} 秒")
    print(f"评估提示词 Token 数: {response.get('prompt_eval_count')}")
    print(f"生成 Token 数: {response.get('eval_count')}")
    print(len(assistant_message))
    single = ollama.embed(
        # model='all-minilm',
        model='embeddinggemma',
        input=assistant_message
    )
    # print(single)
    vector = single['embeddings'][0]
    print(len(vector))

    collection.upsert(
        ids=[image_path], 
        embeddings=[vector], 
        documents=[assistant_message], 
        metadatas=[data.get("metadata", "")]
    )


# 1. 初始化 ChromaDB
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="images")


def process_image(image_path: str) -> None:
    """
    异步包装的图片处理函数，将同步的 retrieval 放入线程池执行，
    以便在多张图片之间并发处理读取、推理和写库。
    """
    # loop = asyncio.get_running_loop()
    # await loop.run_in_executor(None, retrieval, image_path)
    retrieval(image_path)


def main() -> None:
    """
    并发处理指定目录下的所有图片文件。
    """
    tasks = []
    for file in os.listdir(dir_path):
        if file.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            image_path = os.path.join(dir_path, file)
            # tasks.append(asyncio.create_task(process_image(image_path)))
            process_image(image_path)

    # if tasks:
    #     await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        # asyncio.run(main())
        main()
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，中断任务，正在退出...")
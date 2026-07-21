"""
qwen-image-3.0-pro 文生图测试脚本
=================================
使用 DashScope 原生接口（非 OpenAI 兼容模式）调用千问文生图模型。
接口：POST /api/v1/services/aigc/multimodal-generation/generation
"""

import os
import json
import time
import requests
from pathlib import Path

# 手动加载 .env
def load_env(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip())

load_env(Path(__file__).resolve().parent.parent.parent.parent / ".env")

# 节点配置（逐个尝试）
CONFIGS = [
    ("CN-TEST", "DASHSCOPE_API_KEY_CN_TEST", "https://llm-7ufq8xadyf99jlbp.cn-beijing.maas.aliyuncs.com/api/v1"),
    ("SGP-Spicy", "DASHSCOPE_API_KEY_SCG_Spicy", "https://ws-3gnkuvufgzvrftws.ap-southeast-1.maas.aliyuncs.com/api/v1"),
    ("SGP", "DASHSCOPE_API_KEY_SGP", "https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com/api/v1"),
]

prompt = "一只戴着宇航员头盔的橘猫，漂浮在太空中，背景是蔚蓝地球和璀璨星空，电影级光影，超写实风格"
MODEL = "qwen-image-3.0-pro"

payload = {
    "model": MODEL,
    "input": {
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
    },
    "parameters": {
        "size": "1024*1024",
        "n": 1,
        "prompt_extend": True,
        "watermark": False,
        "negative_prompt": "低分辨率，低画质，肢体畸形，画面过饱和，蜡像感"
    }
}

print(f"模型: {MODEL}")
print(f"Prompt: {prompt}")
print(f"尺寸: 1024*1024")
print("=" * 60)

success = False
for label, key_name, base_url in CONFIGS:
    api_key = os.getenv(key_name)
    if not api_key or not base_url:
        continue

    endpoint = f"{base_url}/services/aigc/multimodal-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    print(f"\n尝试节点: {label}")
    print(f"  端点: {endpoint}")

    start = time.time()
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    except Exception as e:
        print(f"  连接失败: {e}")
        continue
    elapsed = time.time() - start
    print(f"  HTTP {resp.status_code} | {elapsed:.2f}s")

    if resp.status_code == 200:
        data = resp.json()
        try:
            image_url = data["output"]["choices"][0]["message"]["content"][0]["image"]
            print(f"  生成成功！")
            print(f"  图片URL: {image_url[:100]}...")

            # 下载图片到本地
            output_dir = Path(__file__).resolve().parent / "output"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "qwen_image_3_pro_test.png"

            img_resp = requests.get(image_url, timeout=60)
            if img_resp.status_code == 200:
                output_path.write_bytes(img_resp.content)
                print(f"  已保存至: {output_path}")
            else:
                print(f"  图片下载失败: {img_resp.status_code}")
        except (KeyError, IndexError) as e:
            print(f"  解析响应失败: {e}")
            print(json.dumps(data, ensure_ascii=False, indent=2))

        if "usage" in data:
            print(f"  Usage: {json.dumps(data['usage'], ensure_ascii=False)}")
        print(f"  Request ID: {data.get('request_id', 'N/A')}")
        success = True
        break
    else:
        err = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
        print(f"  失败: {err.get('code', 'Unknown')} - {err.get('message', resp.text[:200])}")

if not success:
    print("\n所有节点均失败，请确认 qwen-image-3.0-pro 已在百炼控制台开通。")

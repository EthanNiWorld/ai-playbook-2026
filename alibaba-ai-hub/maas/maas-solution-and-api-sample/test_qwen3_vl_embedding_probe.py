"""
qwen3-vl-embedding 各节点可用性探测
==================================
目标：确认 qwen3-vl-embedding（多模态向量模型）在国际站新加坡 / 国际站北京 / 中国站是否可调用。
接口：
  1) DashScope 原生：POST /api/v1/services/embeddings/multimodal-embedding/multimodal-embedding
  2) OpenAI 兼容：POST /compatible-mode/v1/embeddings（纯文本输入）
"""

import os
import json
import requests
from pathlib import Path


def load_env(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


load_env(Path(__file__).resolve().parent.parent.parent.parent / ".env")

MODEL = "qwen3-vl-embedding"

NODES = [
    ("INTL-SG", os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST"),
     "https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com"),
    ("INTL-BJ", os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST"),
     "https://llm-kvw0aiysjfv4g6fh.cn-beijing.maas.aliyuncs.com"),
    ("CN-TEST", os.getenv("DASHSCOPE_API_KEY_CN_TEST"),
     "https://llm-7ufq8xadyf99jlbp.cn-beijing.maas.aliyuncs.com"),
]


def show(resp):
    ct = resp.headers.get("content-type", "")
    print(f"    HTTP {resp.status_code}")
    if "json" not in ct:
        print(f"    body: {resp.text[:300]}")
        return
    data = resp.json()
    if resp.status_code != 200:
        print(f"    code={data.get('code')} | msg={str(data.get('message'))[:200]}")
        print(f"    raw: {json.dumps(data, ensure_ascii=False)[:300]}")
        return
    out = data.get("output", data)
    emb = out.get("embeddings") or out.get("data")
    if isinstance(emb, list) and emb:
        e0 = emb[0]
        vec = e0.get("embedding") if isinstance(e0, dict) else None
        print(f"    OK 条数={len(emb)} 维度={len(vec) if vec else 'N/A'}")
    else:
        print(f"    OK 但未识别向量结构: {list(out)[:6]}")
    usage = data.get("usage")
    print(f"    usage={json.dumps(usage, ensure_ascii=False) if usage else 'N/A'}")


for label, key, host in NODES:
    if not key:
        print(f"[{label}] 缺少 key，跳过")
        continue
    print(f"\n=== {label} ({host.split('//')[1].split('.')[0]}) ===")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # 1) 原生多模态 embedding
    url1 = f"{host}/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
    p1 = {
        "model": MODEL,
        "input": {"contents": [{"text": "一只橘猫躺在窗台上晒太阳"}]},
        "parameters": {"dimension": 1024},
    }
    try:
        r = requests.post(url1, headers=headers, json=p1, timeout=60)
        print("  [原生 multimodal-embedding]")
        show(r)
    except Exception as e:
        print(f"  [原生] 异常 {e}")

    # 2) OpenAI 兼容 /embeddings（纯文本）
    url2 = f"{host}/compatible-mode/v1/embeddings"
    p2 = {"model": MODEL, "input": "今天天气不错"}
    try:
        r = requests.post(url2, headers=headers, json=p2, timeout=60)
        print("  [compatible-mode /embeddings]")
        show(r)
    except Exception as e:
        print(f"  [compatible] 异常 {e}")

    # 3) 对照组：同 key 调文本向量模型，验证 key/向量服务本身是否正常
    url3 = f"{host}/compatible-mode/v1/embeddings"
    p3 = {"model": "qwen3.7-text-embedding", "input": "今天天气不错"}
    try:
        r = requests.post(url3, headers=headers, json=p3, timeout=60)
        print("  [对照 qwen3.7-text-embedding]")
        show(r)
    except Exception as e:
        print(f"  [对照] 异常 {e}")

    # 4) 模型列表（若该端点支持 GET /api/v1/models）
    url4 = f"{host}/api/v1/models"
    try:
        r = requests.get(url4, headers=headers, timeout=30)
        print(f"  [GET /api/v1/models] HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            names = [m.get("model") or m.get("id") or m.get("name") for m in
                     (data.get("data") or data.get("models") or data.get("output", {}).get("models", []) or [])]
            hit = [n for n in names if n and "embed" in str(n)]
            print(f"    模型总数={len(names)} 含 embed 关键字: {hit[:20]}")
        else:
            print(f"    raw: {r.text[:200]}")
    except Exception as e:
        print(f"  [models] 异常 {e}")

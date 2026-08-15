#!/usr/bin/env python3
"""
通过 RDS Copilot Post 兼容模式端点调用 qwen3.8-max 测试
"""
import os
import sys
import json

from dotenv import load_dotenv
import requests

# 加载 .env 文件（从项目根目录向上查找）
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

API_KEY = os.getenv("RDS_COPILOT_API_KEY", "")
BASE_URL = os.getenv("RDS_COPILOT_BASE_URL", "")

if not API_KEY or not BASE_URL:
    print("Error: 请在 .env 文件中配置 RDS_COPILOT_API_KEY 和 RDS_COPILOT_BASE_URL")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen3.8-max",
    "messages": [
        {"role": "user", "content": "Hello! Please introduce yourself briefly, including your model name, capabilities, and knowledge cutoff date."}
    ],
    "max_tokens": 512
}

print(f"Calling {BASE_URL}/chat/completions with model=qwen3.8-max...")
print("-" * 60)

try:
    resp = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print("-" * 60)
    
    if resp.status_code == 200:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"Response:\n{content}")
        print("-" * 60)
        print(f"Usage: {json.dumps(usage, indent=2)}")
    else:
        print(f"Error body:\n{resp.text}")
except Exception as e:
    print(f"Exception: {e}")
    sys.exit(1)
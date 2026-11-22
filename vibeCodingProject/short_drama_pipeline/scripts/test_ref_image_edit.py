"""探测 qwen-image-edit 参考图生图（多图输入）可用性。

用途：女主角替换链路的前置验证——
- 图1 = 角色参考（org_file/female_lead_tina.png，定人物面容发型）
- 图2 = 原客户图（定场景构图光影服饰）
- prompt 指示仅把场景中女主角替换为参考人物

验证点：
1. 北京 workspace 端点是否开通 qwen-image-edit（模型名候选逐一探测）
2. multimodal-generation 同步接口是否接受本地图片 data URI（base64）
3. 多图参考 + 文字指令能否输出符合预期的换人结果

用法：python3 scripts/test_ref_image_edit.py [照片路径] [场景图路径]
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient, QWEN_IMAGE_SYNC_PATH, ModelNotAvailableError
from llm_client import Qwen4MaxClient

# 探测通道与模型候选：逐条尝试，任一通即止
# - sync 多模态：qwen-image 系走 multimodal-generation，探测是否接受图像输入（编辑形态）
# - async 图编辑：wan 系走 image2image/image-synthesis 异步路径（input.base_image_url）
SYNC_EDIT_CANDIDATES = ["qwen-image-edit", "qwen-image-3.0-pro", "qwen-image-2.1-pro"]
ASYNC_EDIT_CANDIDATES = ["wanx2.1-imageedit", "wan2.7-imageedit"]
IMAGE2IMAGE_PATH = "/services/aigc/image2image/image-synthesis"

# 探测用例：火锅夜市自拍场景，女主角替换为参考照片人物
PROBE_PROMPT = (
    "把第二张图场景中的女主角替换为第一张参考照片中的女士："
    "面容与发型完全采用参考照片人物（黑色长直发中分、鹅蛋脸、清透自然妆容），"
    "保留第二张图的场景构图、灯光氛围、动作姿态（自拍回头甜笑、拉行李箱）"
    "与服饰（红色CHONGQING卫衣）；其余人物以外元素一律保持不变。"
    "写实摄影风格，3:4 竖构图。"
)


def main():
    photo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        config.PROJECT_DIR, "org_file", "female_lead_tina.png")
    scene = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        config.PROJECT_DIR, "output", "run_012_20261121_225209", "custom_01.png")
    out_path = os.path.join(config.PROJECT_DIR, "org_file", "probe_edit_result.png")

    if not config.check_credentials():
        sys.exit(1)

    llm = Qwen4MaxClient()
    gen = BailianAsyncClient()

    # 本地图转 data URI（与 qwen4-max 视觉链路同款降采样通道）
    b64, mime = llm._encode_image(photo)
    photo_uri = f"data:{mime};base64,{b64}"
    b64s, mimes = llm._encode_image(scene)
    scene_uri = f"data:{mimes};base64,{b64s}"
    print(f"参考图 data URI 就绪：photo {len(photo_uri) // 1024}KB / scene {len(scene_uri) // 1024}KB")

    last_err = None

    def _try_sync(model):
        """同步 multimodal-generation 通道：图像输入 + 文字指令。"""
        body = {
            "model": model,
            "input": {"messages": [{"role": "user", "content": [
                {"image": photo_uri},
                {"image": scene_uri},
                {"text": PROBE_PROMPT},
            ]}]},
            "parameters": {"size": "1728*2368", "n": 1},
        }
        t0 = time.time()
        try:
            resp = gen.session.post(
                gen.base_url + QWEN_IMAGE_SYNC_PATH,
                headers=gen._headers(async_mode=False), json=body, timeout=300)
            data = gen._parse(resp)
            if resp.status_code == 200:
                content = data["output"]["choices"][0]["message"]["content"]
                url = next((c.get("image") for c in content if c.get("image")), None)
                if not url:
                    print(f"❌ {model} 响应无图片 URL: {json.dumps(data, ensure_ascii=False)[:300]}")
                    return None
                gen.download(url, out_path)
                print(f"✅ {model} 同步多模态编辑成功（{time.time() - t0:.0f}s）→ {out_path}")
                print(f"   模型回复文本: {next((c.get('text', '')[:120] for c in content if c.get('text')), '')}")
                return model
            code = data.get("code", "")
            print(f"❌ {model} HTTP {resp.status_code} {code}: {data.get('message', '')[:160]}")
            if code in ("Throttling", "Throttling.RateQuota"):
                print("   限流，稍后人工重试即可")
                return "THROTTLED"
        except Exception as e:
            print(f"❌ {model} 异常: {type(e).__name__}: {str(e)[:200]}")
        return None

    def _try_async(model):
        """异步 image2image 通道：input.base_image_url 多图参考 + prompt。"""
        body = {
            "model": model,
            "input": {"prompt": PROBE_PROMPT,
                      "base_image_url": [photo_uri, scene_uri]},
            "parameters": {"size": "1728*2368", "n": 1},
        }
        t0 = time.time()
        try:
            resp = gen.session.post(
                gen.base_url + IMAGE2IMAGE_PATH,
                headers=gen._headers(async_mode=True), json=body, timeout=60)
            data = gen._parse(resp)
            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                print(f"❌ {model} 无 task_id: {data.get('message', '')[:160]}")
                return None
            print(f"  {model} 任务已提交 {task_id}，轮询…")
            info = gen.wait_task(task_id, poll_interval=5, max_wait=300)
            if info.get("output", {}).get("task_status") != "SUCCEEDED":
                print(f"❌ {model} 任务失败: {json.dumps(info.get('output', {}), ensure_ascii=False)[:200]}")
                return None
            urls = gen.extract_image_urls(info)
            if not urls:
                print(f"❌ {model} 成功但无 URL")
                return None
            gen.download(urls[0], out_path)
            print(f"✅ {model} 异步图编辑成功（{time.time() - t0:.0f}s）→ {out_path}")
            return model
        except Exception as e:
            print(f"❌ {model} 异常: {type(e).__name__}: {str(e)[:200]}")
        return None

    for model in SYNC_EDIT_CANDIDATES:
        r = _try_sync(model)
        if r == "THROTTLED":
            return 1
        if r:
            return 0
    for model in ASYNC_EDIT_CANDIDATES:
        if _try_async(model):
            return 0
    print("\n全部候选通道失败。")
    return 1


if __name__ == "__main__":
    sys.exit(main())

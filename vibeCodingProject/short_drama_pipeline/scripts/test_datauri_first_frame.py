"""探测：wan 图生视频是否接受 base64 data URI 作为首帧（客户图库功能的可行性前提）。

客户上传的图没有公网 URL，视频步要么 data URI 直传、要么走公网托管。
wan 官方文档声称图像支持 Base64 编码数据，实测确认（用 run_009 剧照 +
duration=2 最小计费档，参数被拒则秒级 FAILED 零费用）。

运行：.venv/bin/python -u scripts/test_datauri_first_frame.py
"""
import base64
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from bailian_client import BailianAsyncClient  # noqa: E402


def main():
    img = os.path.join(config.OUTPUT_DIR, "run_009_20261120_210920", "scene_1_shot1_still.png")
    # 降采样到 1024px JPEG（与 qwen4-max 验收同规格：控制请求体大小）
    from PIL import Image
    im = Image.open(img)
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=85)
    data_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    print(f"data URI 长度: {len(data_uri) / 1024:.0f} KB")

    gen = BailianAsyncClient()
    task_id, model = gen.image2video(
        "固定机位，手指在键盘上敲击，节奏安静", data_uri,
        [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
        resolution="480P", duration=2,
    )
    print(f"✅ 提交成功: {task_id}（{model}）")
    time.sleep(10)
    info = gen.query_task(task_id)
    status = info.get("output", {}).get("task_status", "UNKNOWN")
    print(f"10s 后状态: {status}")
    if status == "FAILED":
        print(json.dumps(info.get("output", {}), ensure_ascii=False)[:400])
        sys.exit(1)
    print("✅ data URI 首帧被接受（校验通过，任务正常执行中）")


if __name__ == "__main__":
    main()
"""prime 默认模型 + 修复后首帧写法端到端验证。

验证点：
1. wan3.0-video-prime + input.media first_frame（修复后格式）任务可提交且首帧生效
2. duration=5 真实生效（此前 2s 问题的回归验证）
3. 记录 prime 实际出片耗时（与标准版对照）

运行：.venv/bin/python -u scripts/verify_prime.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient


def main():
    if not config.check_credentials():
        sys.exit(1)
    gen = BailianAsyncClient(timeout=120)

    print("[1] 生成竖版剧照（3:4）", flush=True)
    still_url, _ = gen.text2image(
        "竖版3:4构图，豪华宴会厅中一位穿黑色西装的年轻男子将刻有麒麟纹的黑金令牌拍在桌上，"
        "电影级打光，超写实质感",
        [config.IMAGE_MODEL], size="1728*2368",
    )
    print(f"  剧照 URL: {still_url[:70]}...", flush=True)

    print(f"\n[2] 图生视频（默认模型 {config.VIDEO_MODEL}，正确首帧写法，480P/5s）", flush=True)
    t0 = time.time()
    task_id, model = gen.image2video(
        "男子拍下令牌后缓缓环视全场，镜头缓慢推近他的面部特写",
        still_url,
        [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
        resolution="480P", duration=5,
    )
    print(f"  已提交 {model} task={task_id}", flush=True)

    while True:
        info = gen.query_task(task_id)
        status = info.get("output", {}).get("task_status", "MISSING")
        elapsed = int(time.time() - t0)
        if gen.is_terminal(info):
            break
        if elapsed % 60 < 15:
            print(f"  [{elapsed}s] {status}", flush=True)
        if elapsed > 1500:
            print("  ❌ 超时", flush=True)
            sys.exit(2)
        time.sleep(15)

    print(f"  终态 {status}（耗时 {time.time() - t0:.0f}s）", flush=True)
    usage = info.get("usage", {})
    print(f"  usage: {json.dumps(usage, ensure_ascii=False)}", flush=True)
    if status != "SUCCEEDED":
        out = info.get("output", {})
        print(f"  ❌ 失败: {out.get('code')} {str(out.get('message', ''))[:200]}", flush=True)
        sys.exit(2)

    url = gen.extract_video_url(info)
    runs = sorted(d for d in os.listdir(config.OUTPUT_DIR) if d.startswith("run_"))
    local = os.path.join(config.OUTPUT_DIR, runs[-1], f"verify_prime_{model}.mp4")
    gen.download(url, local)
    print(f"\n✅ 已下载 {local}（{os.path.getsize(local)} bytes）", flush=True)
    print(f"   验证结论: model={model}, 输出 {usage.get('output_video_duration')}s, "
          f"ratio={usage.get('ratio')}(首帧生效应为竖版), 耗时 {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

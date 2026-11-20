"""wan3.0-video-prime 时长行为对照（第二轮）。

首轮验证发现 prime + first_frame + duration=5 输出仅 2.0s（标准版同参数 5.0s），
排除偶发并探明 prime 的 duration 行为：
- P1: prime 480P + duration=10 —— 若仍输出 2s，则 prime（480P）duration 不生效/强制 2s
- P2: prime 480P + duration=-1（智能时长）—— 观察智能模式输出

运行：.venv/bin/python -u scripts/exp_prime_duration2.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient

VIDEO_PATH = "/services/aigc/video-generation/video-synthesis"


def submit(gen, body):
    resp = gen.session.post(gen.base_url + VIDEO_PATH, headers=gen._headers(async_mode=True),
                            json=body, timeout=120)
    data = gen._parse(resp)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:300]}")
    return data["output"]["task_id"]


def main():
    if not config.check_credentials():
        sys.exit(1)
    gen = BailianAsyncClient(timeout=120)

    print("[0] 生成竖版剧照", flush=True)
    still_url, _ = gen.text2image(
        "竖版3:4构图，穿黑色西装的男子在宴会厅举起红酒杯，电影感光影",
        [config.IMAGE_MODEL], size="1728*2368",
    )
    print(f"  剧照 URL: {still_url[:70]}...", flush=True)

    base_input = {"prompt": "男子放下酒杯，缓缓环视全场，镜头推近面部特写",
                 "media": [{"type": "first_frame", "url": still_url}]}
    tasks = {}
    for label, dur in [("P1_dur10", 10), ("P2_smart", -1)]:
        body = {
            "model": "wan3.0-video-prime",
            "input": base_input,
            "parameters": {"resolution": "480P", "ratio": "adaptive", "duration": dur},
        }
        tasks[label] = submit(gen, body)
        print(f"[{label}] task={tasks[label]}", flush=True)

    results = {}
    t0 = time.time()
    while len(results) < len(tasks) and time.time() - t0 < 1200:
        for label, tid in tasks.items():
            if label in results:
                continue
            info = gen.query_task(tid)
            if gen.is_terminal(info):
                results[label] = info
                u = info.get("usage", {})
                st = info.get("output", {}).get("task_status")
                print(f"[{label}] {st}（{time.time() - t0:.0f}s）: "
                      f"输出 {u.get('output_video_duration')}s, ratio={u.get('ratio')}", flush=True)
                if st != "SUCCEEDED":
                    print(f"  错误: {info.get('output', {}).get('message', '')[:200]}", flush=True)
        time.sleep(20)

    run_dir = sorted(os.path.join(config.OUTPUT_DIR, d) for d in os.listdir(config.OUTPUT_DIR)
                     if d.startswith("run_"))[-1]
    for label, info in results.items():
        url = gen.extract_video_url(info)
        if url:
            local = os.path.join(run_dir, f"exp2_{label}.mp4")
            gen.download(url, local)
            print(f"[{label}] 已下载 {local}", flush=True)

    print("\n=== 结论 ===", flush=True)
    for label, info in results.items():
        u = info.get("usage", {})
        print(f"  {label}: 输出 {u.get('output_video_duration')}s", flush=True)


if __name__ == "__main__":
    main()

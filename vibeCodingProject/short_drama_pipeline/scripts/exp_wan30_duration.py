"""wan3.0-video 时长与输入格式对照实验。

目的：解答「为什么 run_001_20261120_113905 的视频只有 2 秒」。
假设：按 wan2.7-I2V 写法传 input.images，被 wan3.0 静默忽略 → 退化为纯 T2V；
且 duration=5 未按文档生效（输出 2s）。

对照任务：
A. 纯 T2V + duration=5   —— 验证 duration 参数是否生效
B. 正确首帧写法（input.media type=first_frame）+ duration=5 —— 验证首帧是否生效、时长

运行：.venv/bin/python -u scripts/exp_wan30_duration.py
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
    resp = gen.session.post(
        gen.base_url + VIDEO_PATH, headers=gen._headers(async_mode=True),
        json=body, timeout=120,
    )
    data = gen._parse(resp)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:300]}")
    return data["output"]["task_id"]


def wait(gen, task_id, max_wait=1500):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        info = gen.query_task(task_id)
        if gen.is_terminal(info):
            return info
        time.sleep(15)
    raise TimeoutError(task_id)


def main():
    if not config.check_credentials():
        sys.exit(1)
    gen = BailianAsyncClient(timeout=120)

    # 准备一张竖版剧照（首帧用，3:4 → 预期 adaptive 输出应为竖版）
    print("[0] 生成竖版测试剧照（1728*2368）", flush=True)
    still_url, _ = gen.text2image(
        "竖版3:4构图，一位穿黑色西装的年轻男子在豪华宴会厅举起红酒杯，电影感光影",
        [config.IMAGE_MODEL], size="1728*2368",
    )
    print(f"  剧照 URL: {still_url[:80]}...", flush=True)

    tasks = {}

    # A. 纯 T2V，duration=5（对照组：duration 是否生效）
    print("\n[A] T2V + duration=5", flush=True)
    body_a = {
        "model": "wan3.0-video",
        "input": {"prompt": "一只橘猫在窗台上晒太阳，镜头缓慢推近，电影感"},
        "parameters": {"resolution": "480P", "duration": 5},
    }
    tasks["A_t2v_dur5"] = submit(gen, body_a)
    print(f"  task={tasks['A_t2v_dur5']}", flush=True)

    # B. 正确首帧写法 media.first_frame + duration=5
    print("\n[B] 首帧 I2V（input.media first_frame）+ duration=5", flush=True)
    body_b = {
        "model": "wan3.0-video",
        "input": {
            "prompt": "男子缓缓放下酒杯，环视全场，嘴角微微上扬",
            "media": [{"type": "first_frame", "url": still_url}],
        },
        "parameters": {"resolution": "480P", "ratio": "adaptive", "duration": 5},
    }
    tasks["B_i2v_first_frame_dur5"] = submit(gen, body_b)
    print(f"  task={tasks['B_i2v_first_frame_dur5']}", flush=True)

    print("\n等待任务完成（每 60s 心跳）...", flush=True)
    results = {}
    t0 = time.time()
    while len(results) < len(tasks) and time.time() - t0 < 1500:
        for label, tid in tasks.items():
            if label in results:
                continue
            info = gen.query_task(tid)
            if gen.is_terminal(info):
                results[label] = info
                out = info.get("output", {})
                print(f"\n[{label}] 终态 {out.get('task_status')}（{time.time() - t0:.0f}s）", flush=True)
                print(f"  usage: {json.dumps(info.get('usage', {}), ensure_ascii=False)}", flush=True)
                if out.get("task_status") != "SUCCEEDED":
                    print(f"  错误: {out.get('code')} {out.get('message', '')[:200]}", flush=True)
        time.sleep(30)

    # 下载成片供人工核对
    run_dir = sorted(
        os.path.join(config.OUTPUT_DIR, d) for d in os.listdir(config.OUTPUT_DIR) if d.startswith("run_")
    )[-1]
    for label, info in results.items():
        url = gen.extract_video_url(info)
        if url:
            local = os.path.join(run_dir, f"exp_{label}.mp4")
            gen.download(url, local)
            print(f"[{label}] 已下载 {local}（{os.path.getsize(local)} bytes）", flush=True)

    print("\n=== 实验结论 ===", flush=True)
    for label, info in results.items():
        u = info.get("usage", {})
        print(f"  {label}: 输出 {u.get('output_video_duration')}s / ratio={u.get('ratio')} / SR={u.get('SR')}", flush=True)


if __name__ == "__main__":
    main()

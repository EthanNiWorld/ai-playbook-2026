"""视频链路收尾：复用已成功的 wan3.0-video 任务，完成生成式编辑 + 状态查询压测。

背景：query_task 曾因误带 X-DashScope-Async 头返回 403，导致轮询看不到真实状态；
实际视频任务 b74660a2 已 SUCCEEDED。本脚本从该任务直接继续：
1. 取回视频 URL 并下载 scene_1_raw.mp4
2. 提交 wan2.7-videoedit 生成式编辑（雷雨夜替换 + 粒子特效指令）
3. 轮询至终态并下载 scene_1_edited.mp4
4. 对任务做 20s 状态查询压测（对应 500 QPS 申请验证）

运行：.venv/bin/python -u scripts/finish_video_edit.py 2>&1 | tee output/finish_video.log
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient
from task_manager import TaskManager

VIDEO_TASK = "b74660a2-c456-426e-8b41-95212aa07ad1"  # 已 SUCCEEDED 的图生视频任务


def find_latest_run_dir():
    runs = sorted(d for d in os.listdir(config.OUTPUT_DIR) if d.startswith("run_"))
    return os.path.join(config.OUTPUT_DIR, runs[-1])


def heartbeat(gen, task_id, label, max_wait=1800):
    t0, last_beat = time.time(), 0
    while True:
        info = gen.query_task(task_id)
        status = info.get("output", {}).get("task_status", "MISSING")
        if gen.is_terminal(info):
            return info
        elapsed = int(time.time() - t0)
        if elapsed - last_beat >= 60:
            print(f"    [{elapsed}s] {label}: {status}", flush=True)
            last_beat = elapsed
        if elapsed > max_wait:
            raise TimeoutError(f"{label} 超过 {max_wait}s 未完成")
        time.sleep(10)


def main():
    if not config.check_credentials():
        sys.exit(1)
    run_dir = find_latest_run_dir()
    print(f"产物目录: {run_dir}", flush=True)
    with open(os.path.join(run_dir, "storyboard.json")) as f:
        sc = json.load(f)["scenes"][0]
    gen = BailianAsyncClient(timeout=120)

    # 1) 取回已完成的视频
    print("\n[1] 取回 wan3.0-video 成片", flush=True)
    info = gen.query_task(VIDEO_TASK)
    status = info.get("output", {}).get("task_status")
    print(f"  task_status: {status}", flush=True)
    if status != "SUCCEEDED":
        print(f"  ❌ 意外状态: {json.dumps(info, ensure_ascii=False)[:300]}")
        sys.exit(2)
    usage = info.get("usage", {})
    print(f"  usage: {json.dumps(usage, ensure_ascii=False)}", flush=True)
    video_url = gen.extract_video_url(info)
    raw_local = os.path.join(run_dir, "scene_1_raw.mp4")
    gen.download(video_url, raw_local)
    print(f"  ✅ 视频已下载: {raw_local}（{os.path.getsize(raw_local)} bytes）", flush=True)

    # 2) 生成式编辑
    print(f"\n[2] 生成式视频编辑（wan2.7-videoedit）", flush=True)
    edit_instruction = sc.get("edit_instruction") or "把背景替换为雨夜霓虹街头"
    print(f"  编辑指令: {edit_instruction[:80]}", flush=True)
    edit_task, e_model = gen.video_edit(edit_instruction, video_url, [config.VIDEOEDIT_MODEL], resolution="720P")
    print(f"  已提交 {e_model} task={edit_task}", flush=True)
    t0 = time.time()
    info2 = heartbeat(gen, edit_task, "生成式编辑")
    status2 = info2.get("output", {}).get("task_status")
    print(f"  终态 {status2}（耗时 {time.time() - t0:.0f}s）", flush=True)
    if status2 == "SUCCEEDED":
        edited_local = os.path.join(run_dir, "scene_1_edited.mp4")
        gen.download(gen.extract_video_url(info2), edited_local)
        print(f"  ✅ 成片已下载: {edited_local}（{os.path.getsize(edited_local)} bytes）", flush=True)
    else:
        print(f"  ❌ 编辑失败: {json.dumps(info2.get('output', {}), ensure_ascii=False)[:300]}")

    # 3) 状态查询压测
    print(f"\n[3] 状态查询压测（目标 50 QPS，20s）", flush=True)
    tm = TaskManager(gen, target_qps=50)
    tm.add_bailian_task(edit_task, "bailian_video", "压测锚点")
    tm.tasks[0].status = "PENDING"
    tm.pressure_test(duration_s=20)

    print("\n=== 收尾完成 ===", flush=True)


if __name__ == "__main__":
    main()

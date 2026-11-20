"""视频链路专项复测：文生图 → 图生视频 → 生成式编辑 → 状态查询压测。

背景：首轮 demo 中 wan3.0-video 任务在 20 分钟轮询窗口内未完成（首帧图生视频
耗时较长），且管道缓冲丢失了 task_id。本脚本：
1. 用 storyboard.json 中的 image_prompt 重新生成剧照（同步接口，直接拿 URL）
2. 提交 wan3.0-video 图生视频（480P/5s），轮询至多 30 分钟（带心跳输出）
3. 成片下载后提交 wan2.7-videoedit 生成式编辑，轮询并下载成片
4. 对已完成任务做 20 秒状态查询压测（验证查询面可持续 QPS，对应 500 QPS 申请）

运行（无缓冲输出直写日志）：
  .venv/bin/python -u scripts/retest_video.py 2>&1 | tee output/retest_video.log
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient
from task_manager import TaskManager

RUN_DIR = None


def find_latest_run_dir():
    base = config.OUTPUT_DIR
    runs = sorted(d for d in os.listdir(base) if d.startswith("run_"))
    if not runs:
        raise RuntimeError("未找到历史 run 目录")
    return os.path.join(base, runs[-1])


def heartbeat(gen, task_id, label, max_wait=1800):
    """带心跳的轮询：每 60s 输出一次任务状态。"""
    t0 = time.time()
    last_beat = 0
    while True:
        info = gen.query_task(task_id)
        status = info.get("output", {}).get("task_status", "UNKNOWN")
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
    global RUN_DIR
    if not config.check_credentials():
        sys.exit(1)
    RUN_DIR = find_latest_run_dir()
    print(f"复用分镜: {RUN_DIR}", flush=True)
    with open(os.path.join(RUN_DIR, "storyboard.json")) as f:
        board = json.load(f)
    sc = board["scenes"][0]
    gen = BailianAsyncClient(timeout=120)

    # 1) 重新生成剧照（拿 24h 有效 URL）
    print("\n[1] 重新生成剧照（qwen-image-3.0-pro，同步接口）", flush=True)
    still_url, img_model = gen.text2image(
        sc["image_prompt"], [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
        size="1728*2368",
    )
    still_local = os.path.join(RUN_DIR, "scene_1_still.png")
    gen.download(still_url, still_local)
    print(f"  ✅ {img_model} 剧照已更新: {still_local}", flush=True)

    # 2) 图生视频
    print(f"\n[2] 图生视频（wan3.0-video，480P/5s，最长等 30 分钟）", flush=True)
    t0 = time.time()
    task_id, v_model = gen.image2video(
        sc["video_prompt"], still_url,
        [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
        resolution="480P", duration=5,
    )
    print(f"  已提交 {v_model} task={task_id}", flush=True)
    info = heartbeat(gen, task_id, "图生视频", max_wait=1800)
    status = info.get("output", {}).get("task_status")
    print(f"  终态 {status}（耗时 {time.time() - t0:.0f}s）", flush=True)
    if status != "SUCCEEDED":
        print(f"  ❌ 任务失败: {json.dumps(info.get('output', {}), ensure_ascii=False)[:300]}")
        sys.exit(2)
    video_url = gen.extract_video_url(info)
    raw_local = os.path.join(RUN_DIR, "scene_1_raw.mp4")
    gen.download(video_url, raw_local)
    print(f"  ✅ 视频已下载: {raw_local}（{os.path.getsize(raw_local)} bytes）", flush=True)

    # 3) 生成式编辑
    print(f"\n[3] 生成式视频编辑（wan2.7-videoedit）", flush=True)
    edit_task, e_model = gen.video_edit(
        sc.get("edit_instruction") or "把背景替换为雨夜霓虹街头",
        video_url, [config.VIDEOEDIT_MODEL], resolution="480P",
    )
    print(f"  已提交 {e_model} task={edit_task}", flush=True)
    t0 = time.time()
    info2 = heartbeat(gen, edit_task, "生成式编辑", max_wait=1800)
    status2 = info2.get("output", {}).get("task_status")
    print(f"  终态 {status2}（耗时 {time.time() - t0:.0f}s）", flush=True)
    if status2 == "SUCCEEDED":
        edited_local = os.path.join(RUN_DIR, "scene_1_edited.mp4")
        gen.download(gen.extract_video_url(info2), edited_local)
        print(f"  ✅ 成片已下载: {edited_local}（{os.path.getsize(edited_local)} bytes）", flush=True)

    # 4) 状态查询压测（对已完成任务高频查询）
    print(f"\n[4] 状态查询压测（目标 50 QPS 爬坡，20s）", flush=True)
    tm = TaskManager(gen, target_qps=50)
    tm.add_bailian_task(edit_task, "bailian_video", "压测锚点任务")
    tm.tasks[0].status = "PENDING"  # 防止被视为终态跳过
    tm.pressure_test(duration_s=20)

    print("\n=== 复测完成 ===", flush=True)


if __name__ == "__main__":
    main()

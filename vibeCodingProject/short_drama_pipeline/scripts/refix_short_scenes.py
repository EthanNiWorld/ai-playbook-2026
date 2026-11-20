"""场景 1/3 视频重提修复 2s 偶发 + 成片替换 + 重拼 final_cut。

背景：run_008 续跑时场景 1（请求 5s）与场景 3（请求 7s）实际输出均 2s，
属服务端偶发（正确参数复测不重现，重提任务即可）。本脚本：
1. 从 checkpoint 读剧照 URL 与分镜（video_prompt/video_duration/edit_instruction）
2. 重提 wan3.0-video-prime 图生视频，轮询至完成，校验实际时长（±1s 容差）
3. 提交 wan2.7-videoedit 生成编辑成片，替换 scene_N_raw/edited.mp4
4. ffmpeg concat 重拼 final_cut.mp4

运行：.venv/bin/python -u scripts/refix_short_scenes.py 2>&1 | tee -a output/refix.log
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient

if not config.check_credentials():
    sys.exit(1)

RUN_DIR = os.path.join(config.OUTPUT_DIR, "run_008_20261120_180542")
SCENES = [1, 3]  # 2s 偶发受害者；场景 2 输出 8s 正常不动
TOL = 1.0        # 时长容差：请求 5s → 接受 [4,6]


def heartbeat(gen, task_id, label, max_wait=900):
    t0 = last = time.time()
    while True:
        info = gen.query_task(task_id)
        status = info.get("output", {}).get("task_status", "UNKNOWN")
        if gen.is_terminal(info):
            return info
        if time.time() - last >= 60:
            print(f"    [{time.time() - t0:.0f}s] {label}: {status}", flush=True)
            last = time.time()
        if time.time() - t0 > max_wait:
            raise TimeoutError(f"{label} 超时")
        time.sleep(8)


def duration_of(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(out.stdout.strip())


def main():
    ckpt = json.load(open(os.path.join(RUN_DIR, "checkpoint.json")))
    board = ckpt["storyboard"]
    stills = {s["scene"]["id"]: s for s in ckpt["images"]["stills"]}
    gen = BailianAsyncClient(timeout=120)

    for sid in SCENES:
        sc = next(s for s in board["scenes"] if s["id"] == sid)
        still_url = stills[sid]["url"]
        want = sc["video_duration"]
        print(f"\n=== 场景 {sid}：重提图生视频（want {want}s）===", flush=True)

        raw_local = os.path.join(RUN_DIR, f"scene_{sid}_raw.mp4")
        ok = False
        for attempt in (1, 2):  # 偶发兜底：最多两次
            task_id, model = gen.image2video(
                sc["video_prompt"], still_url,
                [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
                resolution="480P", duration=want,
            )
            print(f"  提交 {model} task={task_id}（第 {attempt} 次）", flush=True)
            info = heartbeat(gen, task_id, f"场景{sid}-视频")
            if info.get("output", {}).get("task_status") != "SUCCEEDED":
                print(f"  ❌ 任务失败，重试", flush=True)
                continue
            gen.download(gen.extract_video_url(info), raw_local)
            got = duration_of(raw_local)
            print(f"  实际时长 {got:.1f}s（请求 {want}s）", flush=True)
            if abs(got - want) <= TOL:
                ok = True
                break
            print(f"  ⚠️ 又中 2s 偶发，重提", flush=True)
        if not ok:
            print(f"  ❌ 场景 {sid} 两次重提仍不符，保留旧片段退出", flush=True)
            sys.exit(2)

        # 编辑成片
        print(f"  提交生成式编辑（wan2.7-videoedit）…", flush=True)
        edit_task, e_model = gen.video_edit(
            sc.get("edit_instruction") or "把背景替换为雨夜霓虹街头",
            gen.extract_video_url(info), [config.VIDEOEDIT_MODEL], resolution="720P",
        )
        print(f"  编辑任务 {e_model} task={edit_task}", flush=True)
        info2 = heartbeat(gen, edit_task, f"场景{sid}-编辑")
        if info2.get("output", {}).get("task_status") == "SUCCEEDED":
            edited = os.path.join(RUN_DIR, f"scene_{sid}_edited.mp4")
            gen.download(gen.extract_video_url(info2), edited)
            print(f"  ✅ 场景 {sid} 成片已替换: {os.path.basename(edited)}"
                  f"（{duration_of(edited):.1f}s）", flush=True)

    # 重拼 final_cut
    print(f"\n=== 重拼 final_cut ===", flush=True)
    concat_final(RUN_DIR)
    print("✅ 全部完成")


def concat_final(run_dir):
    board_ids = sorted(json.load(open(os.path.join(run_dir, "checkpoint.json")))
                       ["storyboard"]["scenes"], key=lambda s: s["id"])
    names = [f"scene_{s['id']}_edited.mp4" for s in board_ids
             if os.path.isfile(os.path.join(run_dir, f"scene_{s['id']}_edited.mp4"))]
    if len(names) < 2:
        print("成片不足 2 段，跳过拼接", flush=True)
        return
    lst = os.path.join(run_dir, "concat.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{n}'\n" for n in names)
    out = os.path.join(run_dir, "final_cut.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out],
                   capture_output=True, check=True)
    print(f"  ✅ final_cut.mp4: {duration_of(out):.1f}s（{len(names)} 段拼接）", flush=True)


if __name__ == "__main__":
    main()

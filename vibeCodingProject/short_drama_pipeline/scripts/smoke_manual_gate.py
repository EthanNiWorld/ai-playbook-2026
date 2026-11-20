"""打磨模式（人工确认）SSE 冒烟：不点开始按钮即可全链路验证 HITL 四动作中的关键路径。

流程：
1. manual=true 启动流水线（SSE 流式读事件）
2. 等到分镜确认点 → 模拟人工编辑分镜（title 加后缀）→ continue 带编辑 JSON
   → 校验 checkpoint 里 storyboard.title 已更新、后续按新分镜走
3. 等到图像确认点 → abort 终止
   → 校验收到 paused 事件、checkpoint 无 finished（可续跑）

成本：1 次 qwen4-max 分镜 + 海报/剧照图像调用（1 场景 2 次），之后即终止。

用法：
    .venv/bin/python scripts/smoke_manual_gate.py
"""
import json
import os
import queue
import sys
import threading
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

BASE = "http://127.0.0.1:7861"
SUFFIX = "（人工已打磨）"


def sse_reader(resp, q):
    """SSE 事件读取线程：解析 data: {...} 推入队列。"""
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            q.put(json.loads(line[6:]))
        except json.JSONDecodeError:
            pass
    q.put(None)  # 流结束


def post_confirm(action, storyboard=None):
    body = {"action": action, "storyboard": storyboard}
    r = requests.post(f"{BASE}/api/run/confirm", json=body, timeout=10)
    return r.json()


def wait_event(q, want_type, timeout_s):
    """等到目标事件（中途 log/asset 直接略过打印一行摘要）。"""
    t0 = time.time()
    logs = []
    while time.time() - t0 < timeout_s:
        try:
            ev = q.get(timeout=2)
        except queue.Empty:
            continue
        if ev is None:
            raise RuntimeError("SSE 流意外结束")
        if ev["type"] == want_type:
            return ev, logs
        if ev["type"] == "log":
            logs.append(ev["text"])
            print(f"    [log] {ev['text'][:90]}")
        elif ev["type"] in ("error",):
            raise RuntimeError(f"收到 error 事件: {ev}")
    raise TimeoutError(f"{timeout_s}s 内未等到 {want_type} 事件")


def main():
    print("== 打磨模式冒烟：启动流水线（manual=true） ==")
    # timeout=(连接超时, 读超时)：SSE 流式响应的读超时是「两次字节间的最大间隔」，
    # 图像生成静默期可达数分钟无输出，读超时需放宽（requests 的 timeout=30 会误杀）
    resp = requests.post(f"{BASE}/api/run",
                         json={"theme": "打磨模式冒烟：悬疑反转短剧", "scenes": 1,
                               "manual": True},
                         stream=True, timeout=(10, 600))
    assert resp.ok, f"HTTP {resp.status_code}"
    q = queue.Queue()
    threading.Thread(target=sse_reader, args=(resp, q), daemon=True).start()

    # ── 确认点1：分镜（编辑后继续） ──
    print("\n[1/3] 等待分镜确认点（qwen4-max 生成中，约 30-60s）…")
    ev, _ = wait_event(q, "confirm", timeout_s=180)
    assert ev["step"] == "storyboard", f"首个确认点应为 storyboard，实际 {ev['step']}"
    print(f"  ✅ 收到确认点: {ev['title']} / tip={ev['tip'][:40]}")
    board = ev["payload"]["board"]
    edited = dict(board)
    edited["title"] = board["title"] + SUFFIX  # 模拟人工打磨：改剧名
    edited_json = json.dumps(edited, ensure_ascii=False)
    r = post_confirm("continue", storyboard=edited_json)
    assert r.get("ok"), f"确认失败: {r}"
    print(f"  ✅ 已带编辑分镜继续（新剧名: {edited['title']}）")

    # ── 确认点2：图像（终止） ──
    print("\n[2/3] 等待图像确认点（海报+剧照生成中，约 1-3min）…")
    ev, _ = wait_event(q, "confirm", timeout_s=300)
    assert ev["step"] == "images", f"第二个确认点应为 images，实际 {ev['step']}"
    print(f"  ✅ 收到确认点: {ev['title']}，预览海报={ev['payload']['poster']}")
    for f in ("poster.png", f"scene_{board['scenes'][0]['id']}_still.png"):
        rel = ev["payload"]["poster"].rsplit("/", 1)[0]
        url = f"{BASE}/files/{rel}/{f}"
        head = requests.head(url, timeout=10)
        print(f"    预览 {f}: HTTP {head.status_code}")
    r = post_confirm("abort")
    assert r.get("ok"), f"终止失败: {r}"
    print("  ✅ 已选择终止（保留进度）")

    # ── 终态校验 ──
    print("\n[3/3] 等待 paused 事件…")
    ev, _ = wait_event(q, "paused", timeout_s=30)
    run_dir_name = ev["report"]["run_dir"].split("/")[-1]
    print(f"  ✅ 收到 paused 事件，run_dir={run_dir_name}")

    ckpt_path = os.path.join(config.OUTPUT_DIR, run_dir_name, "checkpoint.json")
    with open(ckpt_path) as f:
        ckpt = json.load(f)
    assert SUFFIX in ckpt["storyboard"]["title"], \
        f"编辑后的分镜未落盘: {ckpt['storyboard']['title']}"
    assert "images" in ckpt, "图像产物未归档"
    assert not ckpt.get("finished"), "终止后不应标记 finished"
    # 确认点终止后不应有视频任务（未走到图生视频）
    assert not ckpt.get("video_tasks"), "终止前不应提交视频任务"
    print(f"  ✅ 分镜编辑已落盘: {ckpt['storyboard']['title']}")
    print("  ✅ 图像已归档、未标记 finished、无视频任务 → 可续跑")
    print("\n✅ 打磨模式冒烟全部通过")


if __name__ == "__main__":
    main()

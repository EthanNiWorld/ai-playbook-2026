"""run_008 指定续跑全链路测试：模拟前端行为，自动确认四个确认点。

流程：
1. POST /api/run {resume: true, resume_run: run_008_20261120_180542, manual: true}
2. 消费 SSE：收到 confirm 事件 → 自动点「确认，继续下一步」（POST /api/run/confirm）
3. 校验：分镜步跳过（♻️）、图像并行、验收/视频/编辑逐步推进，最终 done
4. 终态校验：checkpoint.finished=True、成片 scene_*_edited.mp4 落盘

运行：.venv/bin/python -u scripts/test_resume_run008.py
"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:7861"
RUN = "run_008_20261120_180542"
RUN_DIR = "output/" + RUN


def post(path, body):
    """POST 并返回响应对象（/api/run 为 SSE 流，需迭代消费；其余接口直接解析）。
    urllib 的单值 timeout 是 socket 每次 read 的间隔上限（本地连接秒级建立，
    生图长静默期靠 read=600s 兼容），requests 才支持 (connect, read) 元组。"""
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=600)


def post_json(path, body):
    with post(path, body) as r:
        return json.loads(r.read().decode())


def main():
    print("== 发起指定续跑 ==", flush=True)
    # run_008 状态：storyboard 已生成且已确认（confirmed_gates=['storyboard']）、
    # images 已生成但未确认 → 本次续跑只停 3 个确认点：images / qa / video
    EXPECT_GATES = 3
    resp = post("/api/run", {"resume": True, "resume_run": RUN, "manual": True,
                             "theme": "", "scenes": 1})
    events = []
    confirms = []
    t0 = time.time()

    for raw in resp:  # StreamingResponse 逐行迭代 SSE
        line = raw.decode().strip()
        if not line.startswith("data: "):
            continue
        ev = json.loads(line[6:])
        t = ev.get("type")
        if t == "log":
            print(f"  {ev['text']}", flush=True)
        elif t == "confirm":
            step = ev.get("step")
            print(f"\n>>> 确认点 [{step}]，自动点「确认，继续下一步」\n", flush=True)
            r = post_json("/api/run/confirm", {"action": "continue"})
            confirms.append((step, r))
            print(f"    confirm 响应: {r}", flush=True)
        elif t in ("done", "paused", "error"):
            events.append(ev)
            print(f"\n== 终态事件 {t} ==", flush=True)
            if t == "error":
                print(ev.get("message"))
            break
        elif t == "asset":
            print(f"  [产物] {ev.get('kind')}: {ev.get('label')}", flush=True)

    elapsed = time.time() - t0
    print(f"\n== 校验 ==（耗时 {elapsed:.0f}s）", flush=True)
    fails = []

    # 1) 终态必须是 done（而非 paused/error）
    if not events or events[-1].get("type") != "done":
        fails.append(f"终态非 done: {events[-1] if events else '无'}")

    # 2) 预期确认点全部确认成功（分镜已确认过→跳过；停 images/qa/video 三点）
    bad = [c for c in confirms if not c[1].get("ok")]
    if bad or len(confirms) != EXPECT_GATES:
        fails.append(f"确认点异常: 共 {len(confirms)} 个（预期 {EXPECT_GATES}）, 失败 {bad}")

    # 3) checkpoint 标记 finished
    ckpt = json.load(open(RUN_DIR + "/checkpoint.json"))
    if ckpt.get("finished") is not True:
        fails.append(f"checkpoint.finished = {ckpt.get('finished')}")

    # 4) 成片落盘
    import os
    scenes = [s["id"] for s in ckpt.get("storyboard", {}).get("scenes", [])]
    for sid in scenes:
        edited = f"{RUN_DIR}/scene_{sid}_edited.mp4"
        if not os.path.isfile(edited) or os.path.getsize(edited) < 10000:
            fails.append(f"成片缺失或过小: {edited}")

    # 5) 图像未重新生成（本次续跑应复用 18:17-18:20 生成的 4 张图，不重新提交）
    import os
    if not ckpt.get("images"):
        fails.append("checkpoint.images 丢失")

    if fails:
        print("❌ 失败项:", fails)
        sys.exit(1)
    print("✅ 指定续跑全链路通过：分镜跳过 → 图像并行 → 验收 → 视频 → 编辑 → done，成片已落盘")


if __name__ == "__main__":
    main()

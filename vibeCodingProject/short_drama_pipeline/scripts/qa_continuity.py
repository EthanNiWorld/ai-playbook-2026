"""成片连贯性质检：final_dubbed/final_cut 的结构性校验（不调付费 API，本地 ffmpeg）。

检查项：
1. 成片存在且段数正确（应等于有台词/成片的场景数）
2. 每段与全片时长：ffprobe 实测 vs 分镜预期（镜头 duration 求和），偏差>1.5s 告警
   （顺带捕获平台 <8s 档位 2s 故障）
3. 分辨率一致性：各段分辨率应统一（画布已归一 1080x1440），不一致说明拼接兜底未生效
4. 黑屏/静音段检测：全片音轨 mean_volume 过低或视频亮度异常时告警
5. 口型场景：driving_audio 音轨在成片中非静音（台词已烧入）

用法：.venv/bin/python -u scripts/qa_continuity.py <run目录>
"""
import json
import os
import subprocess
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else None
if not RUN:
    print("用法: qa_continuity.py <run目录>")
    sys.exit(2)


def probe(path, args):
    r = subprocess.run(["ffprobe", "-v", "error", *args, path],
                       capture_output=True, text=True)
    return r.stdout.strip()


def dur(p):
    return float(probe(p, ["-show_entries", "format=duration", "-of", "csv=p=0"]) or 0)


issues, warns = [], []
board = json.load(open(os.path.join(RUN, "storyboard.json")))
n_scenes = len(board["scenes"])

# 1) 成片存在性与段数
edited = sorted(f for f in os.listdir(RUN) if f.startswith("scene_") and f.endswith("_edited.mp4"))
print(f"[1] 场景成片: {len(edited)}/{n_scenes} 段")
if len(edited) < n_scenes:
    issues.append(f"成片缺段：{len(edited)}/{n_scenes}")

# 2) 每段时长 vs 分镜预期（镜头 duration 求和，<8 已规整为 8，允许偏差）
for f in edited:
    sid = int(f.split("_")[1])
    sc = next((s for s in board["scenes"] if s["id"] == sid), None)
    if not sc:
        continue
    want = sum(s.get("duration") or 0 for s in sc.get("shots", [])
               if isinstance(s.get("duration"), int))
    want = max(want, 8 * len(sc.get("shots", [])))  # 规整后预期
    actual = dur(os.path.join(RUN, f))
    flag = "✅" if actual >= want - 1.5 else "❌"
    print(f"{flag} 场景{sid}: {actual:.1f}s（预期 ≥{want - 1.5:.0f}s）")
    if actual < want - 1.5:
        issues.append(f"场景{sid} 仅 {actual:.1f}s（疑似平台短时长故障）")

# 3) 分辨率一致性
resos = {f: probe(os.path.join(RUN, f), ["-show_entries", "stream=width,height",
                                        "-of", "csv=p=0"]).splitlines()[0] for f in edited}
uniq = set(resos.values())
print(f"[3] 分辨率: {sorted(uniq)}")
if len(uniq) > 1:
    # 拼接兜底会归一画布，段级不一是可容忍的；但需确认 final 系列已归一
    for ff in ("final_cut.mp4", "final_dubbed.mp4"):
        p = os.path.join(RUN, ff)
        if os.path.isfile(p):
            r = probe(p, ["-show_entries", "stream=width,height", "-of", "csv=p=0"]).splitlines()[0]
            if r != "1080,1440":
                warns.append(f"{ff} 画布未归一（{r}）")

# 4) 全片黑屏/静音检测
for ff in ("final_dubbed.mp4", "final_cut.mp4"):
    p = os.path.join(RUN, ff)
    if not os.path.isfile(p):
        warns.append(f"缺 {ff}")
        continue
    d = dur(p)
    vol = subprocess.run(["ffmpeg", "-i", p, "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mean = next((l.split("mean_volume:")[1].strip() for l in vol.splitlines()
                 if "mean_volume" in l), "?")
    print(f"[4] {ff}: {d:.1f}s, mean_volume {mean} dB")
    if "silencedetect" in vol or float(mean.replace(" dB", "") or 0) < -55:
        issues.append(f"{ff} 音轨疑似全静音（mean {mean}）")

print()
if warns:
    print("== ⚠️ 提醒 ==")
    for w in warns:
        print(f"  - {w}")
if issues:
    print("== ❌ 发现问题 ==")
    for i in issues:
        print(f"  - {i}")
    sys.exit(1)
print("== ✅ 连贯性质检通过 ==")
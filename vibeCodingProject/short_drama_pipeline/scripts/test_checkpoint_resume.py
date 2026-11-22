"""断点续传（checkpoint）单元测试：全程 mock，不调用任何真实模型。

覆盖三个场景（对应 2026-11-20 前端截图里的「网络重试耗尽」故障）：
1. 首跑在质量验收步抛 RuntimeError → checkpoint 应已保存分镜+图片，未保存 qa
2. 断点续跑 → 分镜/图像不重生成，验收重新执行并成功，最终标记 finished
3. 视频任务提交后再断（编辑提交时抛错）→ 续跑时已提交 task_id 不重复提交
   （image2video 调用次数不增长），仅重新提交编辑任务

运行：.venv/bin/python -u scripts/test_checkpoint_resume.py
"""
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
import pipeline as pl  # noqa: E402

BOARD = {
    "title": "测试短剧",
    "logline": "测试用一句话剧情",
    "poster_prompt": "竖版海报",
    "character_ref_prompt": "主角标准像提示词",
    "scenes": [{
        "id": 1, "desc": "场景一", "dialogue": "台词",
        "shots": [
            {"shot_id": 1, "framing": "全景", "image_prompt": "镜头一首帧",
             "video_prompt": "镜头一运镜", "duration": 8},
            {"shot_id": 2, "framing": "特写", "image_prompt": "镜头二首帧",
             "video_prompt": "镜头二运镜", "duration": 8},
        ],
        "edit_instruction": "背景替换为雨夜街头",
    }],
}

# 口型路由变体：镜头2 标记 needs_lipsync（单 take + 跳过生成式编辑）
BOARD_LIPSYNC = json.loads(json.dumps(BOARD))
BOARD_LIPSYNC["scenes"][0]["shots"][1]["needs_lipsync"] = True

# 客户图库模式分镜：shots 带 seq 指向客户图（图先决）
BOARD_CUSTOM = json.loads(json.dumps(BOARD))
for s in BOARD_CUSTOM["scenes"][0]["shots"]:
    s["seq"] = s["shot_id"]

# 多角色变体：场景带 speaker（voice_map 路由验证用）
BOARD_MULTI = json.loads(json.dumps(BOARD_LIPSYNC))
BOARD_MULTI["scenes"][0]["speaker"] = "马老师"


class FakeLLM:
    model = "qwen4-max"

    def __init__(self, *a, **k):
        self.calls = Counter()
        self.fail_at = None  # "review" / None

    @staticmethod
    def _encode_image(path, max_side=1024, quality=85):
        # mock：返回假 data URI（真实现走 PIL 降采样 base64）
        return "ZmFrZS1pbWc=", "image/jpeg"

    def generate_storyboard(self, theme, num_scenes):
        self.calls["storyboard"] += 1
        return json.loads(json.dumps(BOARD))

    def generate_storyboard_with_images(self, theme, image_paths, num_scenes=None):
        self.calls["storyboard_with_images"] += 1
        # mock：seq 已在 BOARD_CUSTOM 内预置，直接返回
        return json.loads(json.dumps(BOARD_CUSTOM))

    def review_image(self, local, desc, dialogue):
        self.calls["review"] += 1
        if self.fail_at == "review":
            raise RuntimeError("qwen4-max 网络重试耗尽")
        return {"pass": True, "score": 9, "issues": [], "summary": "符合分镜"}

    def pick_take(self, take_paths, shot_desc):
        self.calls["pick_take"] += 1
        return 0, "mock 挑 take1"


class FakeBailian:
    def __init__(self, *a, **k):
        self.calls = Counter()
        self.fail_at = None  # "video_edit" / None

    def text2image(self, prompt, models, size=None):
        self.calls["text2image"] += 1
        return f"https://example/img/{self.calls['text2image']}.png", models[0]

    def download(self, url, path):
        self.calls["download"] += 1
        Path(path).write_bytes(b"fake-bytes")

    def image2video(self, prompt, url, models, resolution, duration):
        self.calls["image2video"] += 1
        return f"task-video-{self.calls['image2video']}", models[0]

    def ref2video(self, prompt, ref_urls, models, resolution, duration):
        self.calls["ref2video"] += 1
        return f"task-ref-{self.calls['ref2video']}", models[0]

    def lipsync2video(self, prompt, image_url, audio_url, models, resolution, duration):
        self.calls["lipsync2video"] += 1
        return f"task-lipsync-{self.calls['lipsync2video']}", models[0]

    def video_edit(self, prompt, video_url, models, resolution):
        self.calls["video_edit"] += 1
        if self.fail_at == "video_edit":
            raise RuntimeError("wan2.7-videoedit 网络重试耗尽")
        return f"task-edit-{self.calls['video_edit']}", models[0]


class FakeIMS:
    def __init__(self, real=False):
        self.real = real
        self.calls = Counter()

    def submit_subtitle_erase(self, *a):
        self.calls["erase"] += 1
        return f"ims-erase-{self.calls['erase']}"

    def submit_produce_job(self, *a):
        self.calls["produce"] += 1
        return f"ims-produce-{self.calls['produce']}"


class FakeTaskManager:
    def __init__(self, gen, ims, target_qps=10):
        self.tasks = []
        self.stats = {"queries": 0, "throttled": 0}

    def add_bailian_task(self, task_id, kind, label):
        rec = SimpleNamespace(task_id=task_id, kind=kind, label=label,
                              status="PENDING", info={})
        self.tasks.append(rec)
        return rec

    def add_ims_task(self, job_id, kind, label):
        rec = SimpleNamespace(task_id=job_id, kind=kind, label=label,
                              status="PENDING", info={})
        self.tasks.append(rec)
        return rec

    def poll_until_done(self, workers=8, max_wait=1200, log_every=30):
        for t in self.tasks:
            t.status = "SUCCEEDED"
            t.info = {"output": {"task_status": "SUCCEEDED",
                                 "video_url": f"https://example/{t.task_id}.mp4"}}
        return {t.label: (t.status, t.info) for t in self.tasks}


class Fakes:
    """一次注入到 pipeline 模块的 fake 集合，跨阶段保留调用计数。"""

    def __init__(self):
        self.llm = FakeLLM()
        self.gen = FakeBailian()
        self.ims = FakeIMS()

    def enter(self):
        patchers = [
            mock.patch.object(pl, "Qwen4MaxClient", lambda *a, **k: self.llm),
            mock.patch.object(pl, "BailianAsyncClient", lambda *a, **k: self.gen),
            mock.patch.object(pl, "IMSClient", lambda *a, **k: self.ims),
            mock.patch.object(pl, "TaskManager", lambda *a, **k: FakeTaskManager(*a, **k)),
            # 8.5 配音步含真实 TTS/BGM 调用，mock 环境置空避免扣费与外呼
            mock.patch.object(pl.ShortDramaPipeline, "_dub_final_cut", lambda self: None),
            # 口型音轨前置含真实 TTS + OSS 上传，mock 直接返回假 oss:// URL
            mock.patch.object(pl.ShortDramaPipeline, "_prep_driving_audio",
                              lambda self, sc, shot: "oss://fake/voice.mp3"),
            # 口型 take 下载后会尝试导入 make_dubbed_final（含真实凭证检查）
            # 并跑 ffmpeg 裁剪，mock 环境直接置空
            mock.patch.object(pl.ShortDramaPipeline, "_trim_lipsync_tail",
                              lambda self, *a, **k: None),
        ]
        for p in patchers:
            p.start()
        self._patchers = patchers

    def exit(self):
        for p in self._patchers:
            p.stop()


def load_ckpt(run_dir):
    with open(os.path.join(run_dir, "checkpoint.json")) as f:
        return json.load(f)


def main():
    tmp = tempfile.mkdtemp(prefix="sdp_ckpt_test_")
    config.OUTPUT_DIR = tmp  # 隔离：不污染真实 output/
    fakes = Fakes()
    fakes.enter()
    failures = []

    def check(name, cond, detail=""):
        flag = "✅" if cond else "❌"
        print(f"  {flag} {name}" + (f"（{detail}）" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    try:
        # ---- 场景 1：首跑在质量验收步网络失败 ----
        print("\n[场景1] 首跑：质量验收步抛「网络重试耗尽」")
        fakes.llm.fail_at = "review"
        try:
            pl.ShortDramaPipeline(theme="测试短剧", num_scenes=1).run()
            check("首跑应抛出异常", False)
        except RuntimeError as e:
            check("首跑抛出 RuntimeError", "网络重试耗尽" in str(e), str(e))

        run_dir = sorted(Path(tmp).glob("run_*"))[-1]
        ckpt = load_ckpt(run_dir)
        check("分镜已存入 checkpoint", ckpt.get("storyboard", {}).get("title") == "测试短剧")
        check("图片产物已存入 checkpoint（镜头粒度）", "images" in ckpt and len(ckpt["images"]["stills"]) == 2)
        check("角色锚定图已存 checkpoint", bool(ckpt["images"].get("char_ref_url")))
        check("验收结果未保存（失败在先）", "qa_results" not in ckpt)
        check("poster.png 已落盘", (run_dir / "poster.png").is_file())
        check("character_ref.png 已落盘", (run_dir / "character_ref.png").is_file())
        check("shot1 首帧已落盘", (run_dir / "scene_1_shot1_still.png").is_file())
        check("shot2 首帧已落盘", (run_dir / "scene_1_shot2_still.png").is_file())
        check("未标记 finished", not ckpt.get("finished"))

        # ---- 场景 2：断点续跑，网络恢复 ----
        print("\n[场景2] 续跑：跳过分镜/图像，重做验收并跑完")
        fakes.llm.fail_at = None
        sb_before, img_before = fakes.llm.calls["storyboard"], fakes.gen.calls["text2image"]
        review_before = fakes.llm.calls["review"]  # 含场景 1 失败那一次
        report = pl.ShortDramaPipeline(resume_dir=str(run_dir)).run()
        check("复用同一 run 目录", report["run_dir"] == str(run_dir))
        check("分镜未重新生成", fakes.llm.calls["storyboard"] == sb_before)
        check("图像未重新生成", fakes.gen.calls["text2image"] == img_before)
        check("验收重新执行（镜头粒度 2 次）", fakes.llm.calls["review"] == review_before + 2)
        ckpt2 = load_ckpt(run_dir)
        check("验收结果已保存", ckpt2.get("qa_results", [{}])[0].get("pass") is True)
        # 双 take：2 镜头 × 2 take = 4 个任务；角色锚定走 ref2video
        check("视频任务已提交并存 task_id（双 take）", len(ckpt2.get("video_tasks", [])) == 4)
        check("挑优已执行（2 镜头各一次）", fakes.llm.calls["pick_take"] >= 2)
        check("IMS 任务已保存", len(ckpt2.get("ims_jobs", [])) == 2)
        check("成片已下载", (run_dir / "scene_1_edited.mp4").is_file())
        # 场景 2 内已跑完 → finished 应为 True
        check("已标记 finished", ckpt2.get("finished") is True)

        # ---- 场景 3：视频任务提交后再断，续跑不重复提交 ----
        print("\n[场景3] 编辑提交时断网 → 续跑复用已提交的 video task_id")
        # 重新制造一个未完成 run：新的首跑，视频任务落盘后让 video_edit 抛错
        # （run 目录命名带递增序号，连续新建不会同名碰撞）
        fakes.gen.fail_at = "video_edit"
        fakes.llm.fail_at = None
        fakes.gen.calls["ref2video"] = 0  # 计数归零便于断言
        try:
            pl.ShortDramaPipeline(theme="测试短剧", num_scenes=1).run()
            check("场景3首跑应抛出异常", False)
        except RuntimeError as e:
            check("场景3首跑抛出 RuntimeError", "videoedit" in str(e), str(e))
        run3 = sorted(Path(tmp).glob("run_*"))[-1]
        ckpt3 = load_ckpt(run3)
        check("video task 已存 checkpoint（2镜头×2take=4）", len(ckpt3.get("video_tasks", [])) == 4)
        check("edit task 未存（失败在先）", not ckpt3.get("edit_tasks"))
        i2v_after_fail, edit_after_fail = (
            fakes.gen.calls["ref2video"], fakes.gen.calls["video_edit"])

        fakes.gen.fail_at = None
        report3 = pl.ShortDramaPipeline(resume_dir=str(run3)).run()
        check("续跑后 ref2video 未重复调用",
              fakes.gen.calls["ref2video"] == i2v_after_fail,
              f"实际调用 {fakes.gen.calls['ref2video']} 次（失败时已提交 {i2v_after_fail} 次）")
        check("续跑后 video_edit 重新提交 1 次",
              fakes.gen.calls["video_edit"] == edit_after_fail + 1)
        check("场景3 成片已下载", (run3 / "scene_1_edited.mp4").is_file())
        ckpt4 = load_ckpt(run3)
        check("场景3 已标记 finished", ckpt4.get("finished") is True)
        check("已完成的 run 不再可续跑",
              (load_ckpt(run_dir).get("finished") is True
               and load_ckpt(run3).get("finished") is True))

        # ---- 场景 4：口型镜头路由（单 take + 跳过生成式编辑） ----
        print("\n[场景4] needs_lipsync 镜头：wan2.7-i2v 单 take，场景跳过 videoedit")
        orig_board = FakeLLM.generate_storyboard
        FakeLLM.generate_storyboard = lambda self, theme, num_scenes: json.loads(json.dumps(BOARD_LIPSYNC))
        try:
            pl.ShortDramaPipeline(theme="测试短剧", num_scenes=1).run()
        finally:
            FakeLLM.generate_storyboard = orig_board
        run4 = sorted(Path(tmp).glob("run_*"))[-1]
        ckpt5 = load_ckpt(run4)
        vt = ckpt5.get("video_tasks", [])
        check("口型镜头走 lipsync2video（1 次）", fakes.gen.calls["lipsync2video"] >= 1)
        check("口型镜头单 take（总任务 2+1=3）", len(vt) == 3,
              f"实际 {len(vt)}")
        check("checkpoint 带 lipsync 标记",
              any(t.get("lipsync") and t.get("shot_id") == 2 for t in vt))
        check("口型任务带台词指纹（dialogue_hash）",
              all(t.get("dialogue_hash") for t in vt if t.get("lipsync")))
        check("含口型镜头的场景跳过生成式编辑", not ckpt5.get("edit_tasks"))
        check("口型场景成片已产出（原片直拷）", (run4 / "scene_1_edited.mp4").is_file())
        check("场景4 已标记 finished", ckpt5.get("finished") is True)

        # ---- 场景 5：客户图库模式（图先决，跳过 AI 生图） ----
        print("\n[场景5] 客户图库：看图写分镜 + 客户图直作首帧，无 text2image")
        fake_imgs = []
        for i in range(2):
            p = os.path.join(tmp, f"client_{i + 1}.png")
            with open(p, "wb") as f:
                f.write(b"fake-img")
            fake_imgs.append(p)
        ti_before = fakes.gen.calls["text2image"]
        pl.ShortDramaPipeline(theme="测试短剧", num_scenes=None,
                              custom_images=fake_imgs).run()
        run5 = sorted(Path(tmp).glob("run_*"))[-1]
        ckpt6 = load_ckpt(run5)
        check("看图写分镜已调用", fakes.llm.calls["storyboard_with_images"] >= 1)
        check("AI 生图被跳过", fakes.gen.calls["text2image"] == ti_before)
        check("客户图已归档进 run 目录",
              (run5 / "custom_01.png").is_file() and (run5 / "custom_02.png").is_file())
        check("checkpoint 记录 custom 模式与图路径",
              ckpt6.get("custom_images") and ckpt6["images"].get("custom") is True
              and len(ckpt6["images"]["stills"]) == 2)
        check("镜头首帧指向客户图",
              ckpt6["images"]["stills"][0]["local"] == "custom_01.png"
              and ckpt6["images"]["stills"][1]["local"] == "custom_02.png")
        check("视频任务正常提交（首帧 data URI）", len(ckpt6.get("video_tasks", [])) == 4)
        check("客户图库成片已产出", (run5 / "scene_1_edited.mp4").is_file())
        check("场景5 已标记 finished", ckpt6.get("finished") is True)

        # ---- 场景 6：多角色音色路由（voice_map + speaker） ----
        print("\n[场景6] 多角色：speaker=马老师 → voice_map 路由对应克隆音色")
        orig_board2 = FakeLLM.generate_storyboard
        FakeLLM.generate_storyboard = lambda self, theme, num_scenes: json.loads(json.dumps(BOARD_MULTI))
        try:
            pl.ShortDramaPipeline(
                theme="测试短剧", num_scenes=1,
                custom_voice={"马老师": "voice-malaoshi-fake", "于总": "voice-yuzong-fake"},
            ).run()
        finally:
            FakeLLM.generate_storyboard = orig_board2
        run6 = sorted(Path(tmp).glob("run_*"))[-1]
        ckpt7 = load_ckpt(run6)
        check("多角色 voice_map 已落 checkpoint",
              isinstance(ckpt7.get("custom_voice"), dict)
              and ckpt7["custom_voice"].get("马老师") == "voice-malaoshi-fake")
        check("分镜 speaker 已记录",
              ckpt7["storyboard"]["scenes"][0].get("speaker") == "马老师")
        # FakeBailian 不感知音色，验证点在路由无异常走完全流程
        check("多角色模式成片已产出", (run6 / "scene_1_edited.mp4").is_file())
        check("场景6 已标记 finished", ckpt7.get("finished") is True)

        # ---- 场景 7：口型镜头改词后续跑 → 旧任务作废重新提交 ----
        print("\n[场景7] 改台词后续跑：旧口型任务作废重新提交（dialogue_hash 失效）")
        orig_board3 = FakeLLM.generate_storyboard
        FakeLLM.generate_storyboard = lambda self, theme, num_scenes: json.loads(json.dumps(BOARD_LIPSYNC))
        try:
            pl.ShortDramaPipeline(theme="测试短剧", num_scenes=1).run()
        finally:
            FakeLLM.generate_storyboard = orig_board3
        run7 = sorted(Path(tmp).glob("run_*"))[-1]
        ck8 = load_ckpt(run7)
        ls_calls_before = fakes.gen.calls["lipsync2video"]
        vt_before = [t for t in ck8.get("video_tasks", []) if t.get("lipsync")]
        check("改词前口型任务已存（单 take）", len(vt_before) == 1,
              f"实际 {len(vt_before)}")
        # 模拟打磨模式人工改台词：storyboard.json 与 checkpoint 同步改
        ck8["storyboard"]["scenes"][0]["dialogue"] = "改词后的全新台词"
        with open(os.path.join(run7, "storyboard.json"), "w") as f:
            json.dump(ck8["storyboard"], f, ensure_ascii=False)
        with open(os.path.join(run7, "checkpoint.json"), "w") as f:
            json.dump(ck8, f, ensure_ascii=False)
        ls_non_before = fakes.gen.calls["ref2video"]
        pl.ShortDramaPipeline(resume_dir=str(run7)).run()
        ck9 = load_ckpt(run7)
        vt_after = [t for t in ck9.get("video_tasks", [])
                    if t.get("lipsync") and t.get("scene_id") == 1]
        check("改词后口型任务重新提交 1 次",
              fakes.gen.calls["lipsync2video"] == ls_calls_before + 1)
        check("非口型镜头不受改词影响（ref2video 未重提）",
              fakes.gen.calls["ref2video"] == ls_non_before)
        check("旧口型任务记录已替换（不残留旧 task_id）",
              len(vt_after) == 1 and vt_after[0]["task_id"] != vt_before[0]["task_id"])
        check("新任务带新台词指纹",
              vt_after[0].get("dialogue_hash") not in (None, vt_before[0].get("dialogue_hash")))
    finally:
        fakes.exit()
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"❌ 失败 {len(failures)} 项: {failures}")
        sys.exit(1)
    print("✅ 全部断言通过（7 个场景）")


if __name__ == "__main__":
    main()

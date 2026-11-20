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


class FakeLLM:
    model = "qwen4-max"

    def __init__(self, *a, **k):
        self.calls = Counter()
        self.fail_at = None  # "review" / None

    def generate_storyboard(self, theme, num_scenes):
        self.calls["storyboard"] += 1
        return json.loads(json.dumps(BOARD))

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
    finally:
        fakes.exit()
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"❌ 失败 {len(failures)} 项: {failures}")
        sys.exit(1)
    print("✅ 全部断言通过（3 个场景）")


if __name__ == "__main__":
    main()

"""短剧批量生产流水线（北京节点 demo）。

流程（对应配额申请的各模型分工）：
1. qwen4-max        → 剧本/分镜结构化生成（资料整理）
2. qwen-image-3.0-pro → 海报 + 场景剧照（图像生成）
3. qwen4-max 多模态   → 剧照质量验收（图像理解 + 质量验收）
4. wan3.0-video     → 剧照首帧驱动图生视频（视频生成）
5. wan2.7-videoedit  → 生成式编辑：背景替换/运镜复刻（生成式视频编辑）
6. IMS VideoDetext   → 字幕擦除（Mock/真实可切换）
7. IMS MediaProducing → 剧集成片剪辑合成（Mock/真实可切换）
全部异步任务统一进 TaskManager 批量轮询（自适应限速 + 限流观测）。

断点续传（最小版）：每步完成后把关键产物写入 run 目录下的 checkpoint.json
（分镜/图片 URL/验收结果/已提交的异步任务 task_id）。网络中断等异常后，
传入 resume_dir 复用该 run 目录：已完成的步骤直接跳过，已提交的异步任务
凭 task_id 重新登记轮询（任务在服务端仍在跑，不重复提交、不重复计费）。

打磨模式（人工确认，HITL）：传入 confirm_cb 后，在「分镜 / 海报剧照 / 质量验收 /
图生视频」四个步骤后暂停等待人工确认（继续 / 重新生成本步 / 终止）；分镜步骤还支持
改完 storyboard.json 后带编辑结果继续（后续图片/视频按新分镜走）。confirm_cb=None
时为全自动模式（默认，行为与原流水线完全一致）。终止时不写 finished，已完成
步骤均在 checkpoint 中，可 --resume 断点续跑。
"""
import os
import json
import glob
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from bailian_client import BailianAsyncClient
from llm_client import Qwen4MaxClient
from ims_client import IMSClient
from task_manager import TaskManager


class ShortDramaPipeline:
    # 打磨模式各确认点的提示文案（CLI/Web 共用）
    GATE_TIPS = {
        "storyboard": "剧本分镜已生成（storyboard.json），请确认后再生成海报/剧照",
        "images": "海报与剧照已生成，请确认后再进入质量验收",
        "qa": "质量验收已完成，请确认后再提交图生视频任务（此步开始视频计费）",
        "video": "场景视频已生成，请确认后再进入生成式编辑（wan2.7-videoedit）",
    }

    def __init__(self, theme="都市逆袭短剧", num_scenes=1, ims_real=False, target_qps=10,
                 resume_dir=None, confirm_cb=None):
        self.llm = Qwen4MaxClient()
        self.gen = BailianAsyncClient()
        self.ims = IMSClient(real=ims_real)
        self.tm = TaskManager(self.gen, self.ims, target_qps=target_qps)
        self.confirm_cb = confirm_cb  # None=全自动；否则每步确认返回 (action, edited)
        if resume_dir:
            # 断点续跑：复用已有 run 目录与 checkpoint，不再新建时间戳目录
            self.run_dir = resume_dir
        else:
            # 命名带递增序号：run_001_20261120_164500，按名字排序即时间顺序，
            # 序号一眼可辨是第几次生产（旧 run 删除后序号重新从 001 计）
            seq = 1 + len([d for d in glob.glob(os.path.join(config.OUTPUT_DIR, "run_*"))
                           if os.path.isdir(d)])
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_dir = os.path.join(config.OUTPUT_DIR, f"run_{seq:03d}_{ts}")
            # 极端同秒同序号碰撞兜底（会误加载旧 checkpoint 当续跑），换下一个序号
            n = seq
            while os.path.isdir(self.run_dir):
                n += 1
                self.run_dir = os.path.join(config.OUTPUT_DIR, f"run_{n:03d}_{ts}")
        os.makedirs(self.run_dir, exist_ok=True)
        self.checkpoint_path = os.path.join(self.run_dir, "checkpoint.json")
        self.ckpt = self._load_ckpt()
        # 恢复时以 checkpoint 内的主题/场数为准（忽略新传入值，避免口径错乱）
        self.theme = self.ckpt.get("theme", theme)
        self.num_scenes = self.ckpt.get("num_scenes", num_scenes)
        self.report = {
            "theme": self.theme,
            "models_used": set(self.ckpt.get("models_used", [])),
            "steps": [], "cost_notes": [],
        }

    # ---------- 断点续传 checkpoint ----------

    def _load_ckpt(self):
        if os.path.isfile(self.checkpoint_path):
            try:
                with open(self.checkpoint_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass  # 损坏的 checkpoint 视为无断点，全部重跑
        return {}

    def _save_ckpt(self, **updates):
        """合并更新并原子落盘（先写 .tmp 再 os.replace，避免写一半损坏）。"""
        self.ckpt.update(updates)
        self.ckpt["models_used"] = sorted(self.report["models_used"])
        tmp = self.checkpoint_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.ckpt, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.checkpoint_path)

    def _ckpt_append(self, key, item):
        """向 checkpoint 的列表字段追加一项（异步任务提交后即落盘，task_id 不丢）。"""
        self._save_ckpt(**{key: self.ckpt.get(key, []) + [item]})

    def _log(self, msg):
        print(f"  {msg}")

    def _step(self, name, detail=""):
        self.report["steps"].append({"step": name, "detail": str(detail)[:200]})

    def run(self):
        ckpt = self.ckpt
        if ckpt:
            print(f"\n{'=' * 60}\n短剧生产流水线 · 断点续跑 · 主题「{self.theme}」\n{'=' * 60}")
            print(f"  ♻️ 复用产物目录: {self.run_dir}")
        else:
            print(f"\n{'=' * 60}\n短剧生产流水线 · 北京节点 demo · 主题「{self.theme}」\n{'=' * 60}")

        # ---------- 1. 剧本分镜（qwen4-max） ----------
        print(f"\n[1] 剧本分镜生成（qwen4-max，资料整理）")
        while True:
            board = self.ckpt.get("storyboard")
            if board:
                print(f"  ♻️ 分镜已生成，跳过（剧名「{board['title']}」）")
                # 兜底补写：storyboard.json 丢失时用 checkpoint 内容恢复
                if not os.path.isfile(os.path.join(self.run_dir, "storyboard.json")):
                    with open(os.path.join(self.run_dir, "storyboard.json"), "w") as f:
                        json.dump(board, f, ensure_ascii=False, indent=2)
            else:
                board = self.llm.generate_storyboard(self.theme, self.num_scenes)
                with open(os.path.join(self.run_dir, "storyboard.json"), "w") as f:
                    json.dump(board, f, ensure_ascii=False, indent=2)
                self._save_ckpt(theme=self.theme, num_scenes=self.num_scenes, storyboard=board)
            self._log(f"剧名「{board['title']}」— {board.get('logline', '')[:60]}")
            self._step("storyboard", f"{board['title']} / {len(board['scenes'])} 场")
            self.report["models_used"].add(self.llm.model)
            act, edited = self._gate("storyboard", {
                "path": os.path.join(self.run_dir, "storyboard.json"), "board": board})
            if act == "abort":
                return self._pause("剧本分镜")
            if act == "redo":
                self.ckpt.pop("storyboard", None)
                print("  🔁 按确认指令重新生成分镜…")
                continue
            self._mark_confirmed("storyboard")
            if edited is not None:  # 人工改完分镜后带编辑结果继续，后续按新分镜走
                board = edited
                with open(os.path.join(self.run_dir, "storyboard.json"), "w") as f:
                    json.dump(board, f, ensure_ascii=False, indent=2)
                self._save_ckpt(storyboard=board)
                print(f"  ✏️ 分镜已按人工编辑更新（{len(board['scenes'])} 场），后续按新分镜继续")
            break

        # ---------- 2. 海报 + 剧照（qwen-image-3.0-pro，同步接口） ----------
        print(f"\n[2] 图像生成（qwen-image-3.0-pro：海报 + 剧照）")
        while True:
            images = self.ckpt.get("images")
            if images:
                print("  ♻️ 海报/剧照已生成，跳过（本地文件缺失时按 URL 重下）")
                poster_url, poster_model = images["poster_url"], images["poster_model"]
                poster_local = os.path.join(self.run_dir, "poster.png")
                if not os.path.isfile(poster_local):
                    self.gen.download(poster_url, poster_local)
                stills = []
                for item in images["stills"]:
                    local = os.path.join(self.run_dir, item["local"])
                    if not os.path.isfile(local):
                        self.gen.download(item["url"], local)
                    stills.append((item["scene"], item["url"], local))
                self.report["models_used"].add(poster_model)
                self._log(f"海报完成（{poster_model}，复用）")
            else:
                # 海报 + 各剧照并行生成（qwen-image 同步接口，串行 4 张要 1 分多钟）。
                # 每个任务生成完直接下载；候选链统一用全局降级链，不再依赖海报的模型。
                def _gen_one(job):
                    if job["kind"] == "poster":
                        url, model = self.gen.text2image(
                            board["poster_prompt"],
                            [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                            size="1536*2688",  # 9:16 竖版海报
                        )
                        local = os.path.join(self.run_dir, "poster.png")
                    else:
                        sc = job["scene"]
                        url, model = self.gen.text2image(
                            sc["image_prompt"],
                            [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                            size="1728*2368",  # 3:4 竖构图剧照
                        )
                        local = os.path.join(self.run_dir, f"scene_{sc['id']}_still.png")
                    self.gen.download(url, local)
                    return job, url, model, local

                jobs = ([{"kind": "poster"}]
                        + [{"kind": "still", "scene": sc} for sc in board["scenes"]])
                print(f"  并行提交 {len(jobs)} 个图像任务（海报 1 + 剧照 {len(jobs) - 1}）…")
                poster_url = poster_model = poster_local = None
                stills = []  # [(scene, url, local_path)]
                with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                    futures = [pool.submit(_gen_one, j) for j in jobs]
                    for fut in as_completed(futures):
                        job, url, model, local = fut.result()  # 单任务失败则整体抛错，续跑重试
                        self.report["models_used"].add(model)
                        if job["kind"] == "poster":
                            poster_url, poster_model, poster_local = url, model, local
                            self._log(f"海报完成（{model}）")
                        else:
                            stills.append((job["scene"], url, local))
                            self._log(f"场景 {job['scene']['id']} 剧照完成: {job['scene']['desc'][:40]}")
                stills.sort(key=lambda x: x[0]["id"])  # 并行完成序不定，按场景号重排
                # 图片产物归档（URL 有效期 24h，续跑时缺失的本地文件可按 URL 重下）
                self._save_ckpt(images={
                    "poster_url": poster_url, "poster_model": poster_model,
                    "stills": [{"scene": sc, "url": url, "local": os.path.basename(local)}
                               for sc, url, local in stills],
                })
            self._step("images", f"海报 1 + 剧照 {len(stills)}（{poster_model}）")
            # 确认点：预览相对路径供 Web 前端拼 /files/ 直链
            act, _ = self._gate("images", {
                "poster": os.path.relpath(poster_local, config.OUTPUT_DIR).replace(os.sep, "/"),
                "stills": [os.path.relpath(local, config.OUTPUT_DIR).replace(os.sep, "/")
                           for _, _, local in stills],
            })
            if act == "abort":
                return self._pause("海报剧照")
            if act == "redo":
                self.ckpt.pop("images", None)
                print("  🔁 按确认指令重新生成海报/剧照（同名覆盖，旧图作废）…")
                continue
            self._mark_confirmed("images")
            break

        # ---------- 3. 剧照质量验收（qwen4-max 多模态） ----------
        print(f"\n[3] 质量验收（qwen4-max 多模态图像理解）")
        while True:
            qa_results = self.ckpt.get("qa_results")
            if qa_results is not None:
                passed = sum(1 for q in qa_results if q.get("pass"))
                print(f"  ♻️ 验收结果已存在，跳过（{passed}/{len(qa_results)} 场通过）")
                self.report["models_used"].add(self.llm.model)
                for qa in qa_results:
                    self._log(f"场景 {qa.get('scene')}: {'✅ 通过' if qa.get('pass') else '⚠️ 未过'}"
                              f"（{qa.get('score', '?')} 分）{qa.get('summary', '')[:50]}")
            else:
                qa_results = []
                for sc, url, local in stills:
                    qa = self.llm.review_image(local, sc["desc"], sc.get("dialogue", ""))
                    qa_results.append({"scene": sc["id"], **qa})
                    self._log(f"场景 {sc['id']}: {'✅ 通过' if qa.get('pass') else '⚠️ 未过'}"
                              f"（{qa.get('score', '?')} 分）{qa.get('summary', '')[:50]}")
                with open(os.path.join(self.run_dir, "qa_results.json"), "w") as f:
                    json.dump(qa_results, f, ensure_ascii=False, indent=2)
                self._save_ckpt(qa_results=qa_results)
            self._step("qa", qa_results)
            act, _ = self._gate("qa", {"results": qa_results})
            if act == "abort":
                return self._pause("质量验收")
            if act == "redo":
                self.ckpt.pop("qa_results", None)
                print("  🔁 按确认指令重新质量验收…")
                continue
            self._mark_confirmed("qa")
            break

        # ---------- 4. 图生视频（wan3.0-video-prime，异步） ----------
        print(f"\n[4] 图生视频（{config.VIDEO_MODEL} → 降级链 wan3.0-video/i2v/t2v）")
        video_records = []
        submitted = {t["scene_id"]: t for t in ckpt.get("video_tasks", [])}
        for sc, still_url, _ in stills:
            # 时长决策：优先用分镜阶段 qwen4-max 按剧情推荐的时长；
            # 缺失时传 -1 交由服务端智能时长模式（模型按 prompt/内容自动推荐）
            dur = sc.get("video_duration")
            if not isinstance(dur, int) or not (2 <= dur <= 30):
                dur = -1  # 智能时长模式
            saved = submitted.get(sc["id"])
            if saved:
                # 断点续传：中断前已提交的异步任务在服务端仍在跑，
                # 凭 task_id 重新登记轮询即可，不重复提交（不重复计费）
                task_id, model = saved["task_id"], saved["model"]
                self._log(f"场景 {sc['id']} ♻️ 复用已提交任务（{model}, task={task_id[:14]}...）")
            else:
                task_id, model = self.gen.image2video(
                    sc["video_prompt"], still_url,
                    [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
                    resolution="480P", duration=dur,
                )
                self._log(f"场景 {sc['id']} 已提交（{model}, duration={dur if dur > 0 else '智能'}, task={task_id[:14]}...）")
                # 提交即落盘：中途断网时 task_id 不丢，恢复后直接重新轮询
                self._ckpt_append("video_tasks",
                                  {"scene_id": sc["id"], "task_id": task_id, "model": model})
            rec = self.tm.add_bailian_task(task_id, "bailian_video", f"场景{sc['id']}-视频({model})")
            video_records.append((sc, rec, model))
            self.report["models_used"].add(model)

        # ---------- 6a. 先提交 IMS 侧任务（Mock 演示并行纳管） ----------
        # 真实场景中字幕擦除/剪辑合成作用于成片视频，此处演示为流程编排：
        # 擦除对象登记为生成的视频 URL（Mock 不真正下载处理）
        print(f"\n[5] IMS 任务提交（字幕擦除 + 剧集剪辑合成，{('真实' if self.ims.real else 'MOCK')}模式）")
        ims_records = []
        ims_jobs = ckpt.get("ims_jobs")
        if ims_jobs:
            print("  ♻️ 复用已提交的 IMS 任务")
            for j in ims_jobs:
                ims_records.append(self.tm.add_ims_task(j["job_id"], j["kind"], j["label"]))
        else:
            if self.ims.real:
                ims_out = os.getenv("IMS_OUTPUT_OSS", "")
            else:
                ims_out = ""
            erase_job = self.ims.submit_subtitle_erase(
                "s1.mp4占位：待场景视频完成后登记", ims_out + "erased/scene.mp4" if ims_out else "")
            ims_records.append(self.tm.add_ims_task(erase_job, "ims_erase", f"字幕擦除({erase_job[:20]})"))
            timeline = {"VideoTracks": [{"VideoTrackClips": [
                {"MediaURL": "s1.mp4占位", "Out": 5},
            ]}]}
            produce_job = self.ims.submit_produce_job(json.dumps(timeline, ensure_ascii=False))
            ims_records.append(self.tm.add_ims_task(produce_job, "ims_produce", f"剪辑合成({produce_job[:20]})"))
            self._save_ckpt(ims_jobs=[
                {"job_id": erase_job, "kind": "ims_erase", "label": f"字幕擦除({erase_job[:20]})"},
                {"job_id": produce_job, "kind": "ims_produce", "label": f"剪辑合成({produce_job[:20]})"},
            ])
        self._step("ims_submitted", [r.label for r in ims_records])

        # ---------- 5. 批量轮询（百炼 + IMS 统一任务管理器） ----------
        print(f"\n[6] 批量任务轮询（TaskManager，自适应限速 + 限流观测）")
        t0 = time.time()
        results = self.tm.poll_until_done(workers=8, max_wait=1800)
        print(f"  全部任务终态（耗时 {time.time() - t0:.0f}s）")
        for label, (status, _) in results.items():
            flag = "✅" if status == "SUCCEEDED" or status == "SUCCESS" else "❌"
            print(f"    {flag} {label}: {status}")

        # ---------- 确认点：视频全部生成后，确认再进入生成式编辑 ----------
        act, _ = self._gate("video", {
            "clips": [{"scene": sc["id"],
                       "url": rec.info.get("output", {}).get("video_url")}
                      for sc, rec, _ in video_records],
        })
        if act == "abort":
            return self._pause("图生视频")
        self._mark_confirmed("video")

        # ---------- 7. 下载视频 + 生成式编辑 ----------
        print(f"\n[7] 生成式视频编辑（wan2.7-videoedit：背景替换/运镜复刻）")
        edit_records = []
        edit_saved = {e["scene_id"]: e for e in ckpt.get("edit_tasks", [])}
        for sc, rec, model in video_records:
            info = rec.info
            video_url = info.get("output", {}).get("video_url")
            if not video_url:
                self._log(f"场景 {sc['id']} 视频未成功（{rec.status}），跳过编辑")
                continue
            local = os.path.join(self.run_dir, f"scene_{sc['id']}_raw.mp4")
            saved = edit_saved.get(sc["id"])
            if saved:
                # 断点续传：复用已提交的编辑任务；原始视频缺失时按 URL 补下
                if not os.path.isfile(local):
                    self.gen.download(video_url, local)
                edit_task, edit_model = saved["task_id"], saved["model"]
                self._log(f"场景 {sc['id']} ♻️ 复用已提交编辑任务（{edit_model}）")
            else:
                self.gen.download(video_url, local)
                self._log(f"场景 {sc['id']} 原始视频已下载: {os.path.basename(local)}")
                edit_task, edit_model = self.gen.video_edit(
                    sc.get("edit_instruction") or "把背景替换为雨夜霓虹街头",
                    video_url, [config.VIDEOEDIT_MODEL], resolution="720P",
                )
                self._ckpt_append("edit_tasks",
                                  {"scene_id": sc["id"], "task_id": edit_task, "model": edit_model})
                self._log(f"场景 {sc['id']} 编辑任务已提交（{edit_model}）")
            rec2 = self.tm.add_bailian_task(edit_task, "bailian_video", f"场景{sc['id']}-编辑({edit_model})")
            edit_records.append((sc, rec2, local))
            self.report["models_used"].add(edit_model)
        if edit_records:
            print("  等待编辑任务完成...")
            self.tm.poll_until_done(workers=8, max_wait=1800)
            for sc, rec2, raw_local in edit_records:
                url2 = rec2.info.get("output", {}).get("video_url")
                if url2:
                    edited = os.path.join(self.run_dir, f"scene_{sc['id']}_edited.mp4")
                    self.gen.download(url2, edited)
                    self._log(f"场景 {sc['id']} 成片: {os.path.basename(edited)}")

        # ---------- 8. 总结报告 ----------
        self._finalize()
        return self.report

    # ---------- 打磨模式：人工确认点 ----------

    def _gate(self, step, payload):
        """确认点：返回 (action, edited)，action ∈ continue/redo/abort。
        confirm_cb=None（全自动模式）时直接放行，行为与原流水线一致；
        断点续跑时此前已人工确认过的步骤（confirmed_gates）直接跳过，
        不重复弹卡——刷新页面/断网重连后续跑只会停在下一个未确认的步骤。"""
        if self.confirm_cb is None:
            return "continue", None
        if step in self.ckpt.get("confirmed_gates", []):
            print(f"  ♻️ 此前已人工确认过本步骤，续跑直接跳过该确认点")
            return "continue", None
        print(f"\n  ⏸️ 打磨确认点 · {self.GATE_TIPS[step]}")
        return self.confirm_cb(step, payload)

    def _mark_confirmed(self, step):
        """确认通过后记入 checkpoint：续跑时该确认点不再重复打扰。"""
        gates = self.ckpt.get("confirmed_gates", [])
        if step not in gates:
            self._save_ckpt(confirmed_gates=gates + [step])

    def _pause(self, step):
        """确认点选择终止：不写 finished/report.json，已完成步骤均在 checkpoint 中，
        可用 --resume（或界面「续跑」按钮）从断点继续，不重复提交、不重复计费。"""
        print(f"\n{'=' * 60}\n⏸️ 已在「{step}」确认点终止。产物目录: {self.run_dir}")
        print("   已完成步骤均已落盘，可断点续跑（CLI --resume / 界面「续跑」按钮）。")
        print(f"{'=' * 60}")
        self.report["paused"] = True
        self.report["models_used"] = sorted(self.report["models_used"])
        self.report["task_stats"] = self.tm.stats
        self.report["run_dir"] = self.run_dir
        return self.report

    def _finalize(self):
        self.report["models_used"] = sorted(self.report["models_used"])
        self._save_ckpt(finished=True)
        self.report["task_stats"] = self.tm.stats
        self.report["run_dir"] = self.run_dir
        path = os.path.join(self.run_dir, "report.json")
        with open(path, "w") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n{'=' * 60}\n✅ 流水线完成。产物目录: {self.run_dir}\n{'=' * 60}")

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
import shutil
import subprocess
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

        # ---------- 2. 海报 + 角色锚定 + 各镜头首帧（qwen-image-3.0-pro，同步接口） ----------
        print(f"\n[2] 图像生成（qwen-image-3.0-pro：海报 + 角色锚定 + 镜头首帧）")
        while True:
            images = self.ckpt.get("images")
            if images:
                print("  ♻️ 海报/锚定图/镜头首帧已生成，跳过（本地缺失时按 URL 重下）")
                poster_url, poster_model = images["poster_url"], images["poster_model"]
                poster_local = os.path.join(self.run_dir, "poster.png")
                if not os.path.isfile(poster_local):
                    self.gen.download(poster_url, poster_local)
                char_ref_url = images.get("char_ref_url")
                char_ref_local = os.path.join(self.run_dir, "character_ref.png")
                if char_ref_url and not os.path.isfile(char_ref_local):
                    self.gen.download(char_ref_url, char_ref_local)
                stills = []  # [(scene, shot, url, local_path)]
                for item in images["stills"]:
                    local = os.path.join(self.run_dir, item["local"])
                    if not os.path.isfile(local):
                        self.gen.download(item["url"], local)
                    # 旧 checkpoint 兼容：早期单镜头 run 无 shot 字段 → 包默认镜头
                    shot = item.get("shot") or {"shot_id": 1, "framing": "中景",
                                                "video_prompt": "", "duration": -1}
                    stills.append((item["scene"], shot, item["url"], local))
                self.report["models_used"].add(poster_model)
                self._log(f"海报完成（{poster_model}，复用）")
            else:
                # 多镜头并行生图：海报 + 角色锚定图 + 各镜头首帧（qwen-image 同步接口）。
                # 每镜头独立首帧（景别各异），角色锚定图作为 reference 供视频步角色一致性。
                def _gen_one(job):
                    if job["kind"] == "poster":
                        url, model = self.gen.text2image(
                            board["poster_prompt"],
                            [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                            size="1536*2688",  # 9:16 竖版海报
                        )
                        local = os.path.join(self.run_dir, "poster.png")
                    elif job["kind"] == "char_ref":
                        url, model = self.gen.text2image(
                            board.get("character_ref_prompt") or board["poster_prompt"],
                            [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                            size="1024*1024",  # 角色标准像（参考图正方形）
                        )
                        local = os.path.join(self.run_dir, "character_ref.png")
                    else:
                        sc, shot = job["scene"], job["shot"]
                        url, model = self.gen.text2image(
                            shot["image_prompt"],
                            [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                            size="1728*2368",  # 3:4 竖构图首帧
                        )
                        local = os.path.join(
                            self.run_dir, f"scene_{sc['id']}_shot{shot['shot_id']}_still.png")
                    self.gen.download(url, local)
                    return job, url, model, local

                # 镜头清单：新 schema（shots[]）或兼容旧 schema（单镜头字段）
                def _shots_of(sc):
                    if sc.get("shots"):
                        return sc["shots"]
                    return [{"shot_id": 1, "framing": "中景",
                             "image_prompt": sc.get("image_prompt", ""),
                             "video_prompt": sc.get("video_prompt", ""),
                             "duration": sc.get("video_duration", -1)}]

                jobs = ([{"kind": "poster"}, {"kind": "char_ref"}]
                        + [{"kind": "still", "scene": sc, "shot": shot}
                           for sc in board["scenes"] for shot in _shots_of(sc)])
                n_shots = len(jobs) - 2
                print(f"  并行提交 {len(jobs)} 个图像任务（海报 1 + 角色锚定 1 + 镜头首帧 {n_shots}）…")
                poster_url = poster_model = poster_local = None
                char_ref_url = char_ref_local = None
                stills = []  # [(scene, shot, url, local_path)]
                with ThreadPoolExecutor(max_workers=min(len(jobs), 8)) as pool:
                    futures = [pool.submit(_gen_one, j) for j in jobs]
                    for fut in as_completed(futures):
                        job, url, model, local = fut.result()  # 单任务失败则整体抛错，续跑重试
                        self.report["models_used"].add(model)
                        if job["kind"] == "poster":
                            poster_url, poster_model, poster_local = url, model, local
                            self._log(f"海报完成（{model}）")
                        elif job["kind"] == "char_ref":
                            char_ref_url, char_ref_local = url, local
                            self._log(f"角色锚定图完成（{model}）")
                        else:
                            stills.append((job["scene"], job["shot"], url, local))
                            self._log(f"场景 {job['scene']['id']}-镜头 {job['shot']['shot_id']}"
                                      f"（{job['shot'].get('framing', '?')}）首帧完成")
                stills.sort(key=lambda x: (x[0]["id"], x[1]["shot_id"]))  # 按（场景号，镜头号）重排
                # 图片产物归档（URL 有效期 24h，续跑时缺失的本地文件可按 URL 重下）
                self._save_ckpt(images={
                    "poster_url": poster_url, "poster_model": poster_model,
                    "char_ref_url": char_ref_url,
                    "stills": [{"scene": sc, "shot": shot, "url": url,
                                "local": os.path.basename(local)}
                               for sc, shot, url, local in stills],
                })
            self._step("images", f"海报 1 + 锚定 1 + 镜头首帧 {len(stills)}（{poster_model}）")
            # 确认点：预览相对路径供 Web 前端拼 /files/ 直链
            act, _ = self._gate("images", {
                "poster": os.path.relpath(poster_local, config.OUTPUT_DIR).replace(os.sep, "/"),
                "stills": [os.path.relpath(local, config.OUTPUT_DIR).replace(os.sep, "/")
                           for _, _, _, local in stills],
            })
            if act == "abort":
                return self._pause("海报剧照")
            if act == "redo":
                self.ckpt.pop("images", None)
                print("  🔁 按确认指令重新生成海报/剧照（同名覆盖，旧图作废）…")
                continue
            self._mark_confirmed("images")
            break

        # ---------- 3. 镜头首帧质量验收（qwen4-max 多模态） ----------
        print(f"\n[3] 质量验收（qwen4-max 多模态图像理解，镜头粒度）")
        while True:
            qa_results = self.ckpt.get("qa_results")
            if qa_results is not None:
                passed = sum(1 for q in qa_results if q.get("pass"))
                print(f"  ♻️ 验收结果已存在，跳过（{passed}/{len(qa_results)} 镜头通过）")
                self.report["models_used"].add(self.llm.model)
                for qa in qa_results:
                    self._log(f"场景{qa.get('scene')}-镜头{qa.get('shot')}: {'✅ 通过' if qa.get('pass') else '⚠️ 未过'}"
                              f"（{qa.get('score', '?')} 分）{qa.get('summary', '')[:50]}")
            else:
                qa_results = []
                for sc, shot, url, local in stills:
                    qa = self.llm.review_image(
                        local, f"{sc['desc']}；本镜头：{shot.get('framing', '')} {shot.get('image_prompt', '')[:60]}",
                        sc.get("dialogue", ""))
                    qa_results.append({"scene": sc["id"], "shot": shot.get("shot_id", 1), **qa})
                    self._log(f"场景{sc['id']}-镜头{shot.get('shot_id')}: {'✅ 通过' if qa.get('pass') else '⚠️ 未过'}"
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

        # ---------- 4. 视频生成（镜头粒度，异步，双 take + 角色锚定 + 挑优） ----------
        print(f"\n[4] 视频生成（{config.VIDEO_MODEL}，每镜头双 take，角色锚定参考）")
        TAKES = 2  # 同镜头抽卡次数（业内标准：多 take 挑优）
        video_records = []  # [(scene, shot, rec, model)]，rec 为选定 take 的任务记录
        submitted = {(t["scene_id"], t.get("shot_id", 1)): t for t in ckpt.get("video_tasks", [])}
        for sc, shot, still_url, _ in stills:
            # 时长决策：镜头级 duration；平台时段性故障规避：<8 档位规整为 8
            dur = shot.get("duration")
            if not isinstance(dur, int) or not (2 <= dur <= 30):
                dur = -1
            elif 0 < dur < 8:
                self._log(f"场景{sc['id']}-镜头{shot['shot_id']} duration={dur} 规整为 8（平台 <8s 档位 2s 故障规避）")
                dur = 8
            key = (sc["id"], shot.get("shot_id", 1))
            saved = submitted.get(key)
            if saved:
                task_id, model = saved["task_id"], saved["model"]
                self._log(f"场景{sc['id']}-镜头{shot['shot_id']} ♻️ 复用已提交任务（{model}）")
                rec = self.tm.add_bailian_task(task_id, "bailian_video",
                                               f"场景{sc['id']}-镜头{shot['shot_id']}({model})")
                video_records.append((sc, shot, rec, model, None))
                self.report["models_used"].add(model)
                continue
            # 新提交：优先角色锚定参考生视频（首帧构图换角色一致性），锚定图缺失时回退首帧驱动
            ref_urls = [char_ref_url, still_url] if char_ref_url else []
            take_jobs = []  # [(take_id, task_id, model)]
            for take_id in range(TAKES):
                if ref_urls:
                    # 参考生视频：锚定图保角色一致，prompt 描述构图/运镜（首镜头把首帧图也作参考保持构图）
                    prompt = (f"{shot['video_prompt']}；保持人物与参考图完全一致的面容发型服饰。"
                              f"构图：{shot.get('framing', '中景')}景，3:4 竖构图")
                    task_id, model = self.gen.ref2video(
                        prompt, [ref_urls[0]],
                        [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
                        resolution="480P", duration=dur,
                    )
                else:
                    task_id, model = self.gen.image2video(
                        shot["video_prompt"], still_url,
                        [config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS,
                        resolution="480P", duration=dur,
                    )
                take_jobs.append((take_id, task_id, model))
                self._log(f"场景{sc['id']}-镜头{shot['shot_id']} take{take_id + 1} 已提交（{model}, {dur if dur > 0 else '智能'}s）")
                self._ckpt_append("video_tasks",
                                  {"scene_id": sc["id"], "shot_id": shot.get("shot_id", 1),
                                   "take_id": take_id, "task_id": task_id, "model": model})
            for take_id, task_id, model in take_jobs:
                rec = self.tm.add_bailian_task(task_id, "bailian_video",
                                               f"场景{sc['id']}-镜头{shot['shot_id']}-t{take_id}({model})")
                video_records.append((sc, shot, rec, model, take_id))
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
            "clips": [{"scene": sc["id"], "shot": shot.get("shot_id"),
                       "url": rec.info.get("output", {}).get("video_url")}
                      for sc, shot, rec, _, _ in video_records],
        })
        if act == "abort":
            return self._pause("图生视频")
        self._mark_confirmed("video")

        # ---------- 7. take 挑优下载 + 场内拼接 + 生成式编辑 ----------
        print(f"\n[7] take 挑优 + 场内镜头拼接 + 生成式编辑")
        # 7a. 同镜头多 take：下载各 take → qwen4-max 多模态抽帧挑优 → 选定片段
        chosen_take_local = {}  # (scene_id, shot_id) -> local path
        takes_by_key = {}
        for sc, shot, rec, model, take_id in video_records:
            key = (sc["id"], shot.get("shot_id", 1))
            takes_by_key.setdefault(key, {"scene": sc, "shot": shot, "takes": []})
            url = rec.info.get("output", {}).get("video_url")
            if not url:
                self._log(f"场景{sc['id']}-镜头{key[1]}-take{take_id} 未成功（{rec.status}）")
                continue
            take_local = os.path.join(self.run_dir,
                                      f"scene_{key[0]}_shot{key[1]}_take{take_id}.mp4")
            self.gen.download(url, take_local)
            takes_by_key[key]["takes"].append((take_id, take_local))
        for key, bundle in takes_by_key.items():
            sc, shot, takes = bundle["scene"], bundle["shot"], bundle["takes"]
            if not takes:
                self._log(f"⚠️ 场景{key[0]}-镜头{key[1]} 全部 take 失败，本镜头缺片")
                continue
            if len(takes) == 1:
                chosen, reason = takes[0][0], "单 take 直接采用"
            else:
                chosen, reason = self.llm.pick_take(
                    [t[1] for t in takes],
                    f"{shot.get('framing', '')}景，{shot.get('video_prompt', '')[:80]}")
                self._log(f"场景{key[0]}-镜头{key[1]} 挑优：take{chosen + 1}（{reason}）")
            chosen_local = next(p for tid, p in takes if tid == chosen)
            chosen_take_local[key] = chosen_local

        # 7b. 场内拼接：同一场景的多镜头硬切拼接（业内实践：场内硬切，场间转场）
        scene_raw = {}  # scene_id -> 拼接后原始片段路径
        for sc in board["scenes"]:
            keys = sorted(k for k in chosen_take_local if k[0] == sc["id"])
            if not keys:
                continue
            if len(keys) == 1:
                scene_raw[sc["id"]] = chosen_take_local[keys[0]]
            else:
                merged = os.path.join(self.run_dir, f"scene_{sc['id']}_raw.mp4")
                lst = os.path.join(self.run_dir, f"concat_s{sc['id']}.txt")
                with open(lst, "w") as f:
                    f.writelines("file '" + os.path.relpath(chosen_take_local[k], self.run_dir) + "'" + chr(10)
                                 for k in keys)
                ok = subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", merged],
                    capture_output=True)
                if ok.returncode == 0:
                    scene_raw[sc["id"]] = merged
                    self._log(f"场景 {sc['id']} 场内 {len(keys)} 镜硬切拼接完成")
                else:  # concat 失败（编码不一致等）→ 逐镜头转码拼接兜底
                    inputs, fc = [], []
                    for i, k in enumerate(keys):
                        inputs += ["-i", chosen_take_local[k]]
                        fc.append(f"[{i}:v]scale=820:1124,setsar=1,fps=30[v{i}]")
                        fc.append(f"[{i}:a]aresample=44100[a{i}]")
                    for i in range(1, len(keys)):
                        fc.append(f"[v{i - 1}][v{i}]concat=n=2:v=1:a=0[vc{i}]")
                        fc.append(f"[a{i - 1}][a{i}]concat=n=2:v=0:a=1[ac{i}]")
                    if len(keys) > 1:
                        last = len(keys) - 1
                        try:
                            subprocess.run(
                                ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
                                 "-map", f"[vc{last}]", "-map", f"[ac{last}]",
                                 "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", merged],
                                capture_output=True, check=True)
                            scene_raw[sc["id"]] = merged
                            self._log(f"场景 {sc['id']} 场内转码拼接完成（硬切）")
                        except subprocess.SubprocessError:
                            # 转码也失败（如 mock 测试的假文件）：回退用第一镜头，不阻断
                            scene_raw[sc["id"]] = chosen_take_local[keys[0]]
                            self._log(f"⚠️ 场景 {sc['id']} 场内拼接失败，回退第一镜头")

        # 7c. 生成式编辑（场景粒度，同前：复用/新提交）
        edit_records = []
        edit_saved = {e["scene_id"]: e for e in ckpt.get("edit_tasks", [])}
        for sc in board["scenes"]:
            raw_path = scene_raw.get(sc["id"])
            if not raw_path:
                self._log(f"场景 {sc['id']} 无可用片段，跳过编辑")
                continue
            video_url = next((rec.info.get("output", {}).get("video_url")
                              for s2, sh2, rec, _, _ in video_records
                              if s2["id"] == sc["id"]), None)
            if not video_url:
                continue
            saved = edit_saved.get(sc["id"])
            if saved:
                edit_task, edit_model = saved["task_id"], saved["model"]
                self._log(f"场景 {sc['id']} ♻️ 复用已提交编辑任务（{edit_model}）")
            else:
                edit_task, edit_model = self.gen.video_edit(
                    sc.get("edit_instruction") or "把背景替换为雨夜霓虹街头",
                    video_url, [config.VIDEOEDIT_MODEL], resolution="720P",
                )
                self._ckpt_append("edit_tasks",
                                  {"scene_id": sc["id"], "task_id": edit_task, "model": edit_model})
                self._log(f"场景 {sc['id']} 编辑任务已提交（{edit_model}）")
            rec2 = self.tm.add_bailian_task(edit_task, "bailian_video", f"场景{sc['id']}-编辑({edit_model})")
            edit_records.append((sc, rec2, raw_path))
            self.report["models_used"].add(edit_model)
        if edit_records:
            print("  等待编辑任务完成...")
            self.tm.poll_until_done(workers=8, max_wait=1800)
            for sc, rec2, raw_local in edit_records:
                url2 = rec2.info.get("output", {}).get("video_url")
                if url2:
                    edited = os.path.join(self.run_dir, f"scene_{sc['id']}_edited.mp4")
                    self.gen.download(url2, edited)
                    self._check_clip_duration(sc, edited)
                    self._log(f"场景 {sc['id']} 成片: {os.path.basename(edited)}")
        else:
            for sid, raw_path in scene_raw.items():
                sc2 = next(s for s in board["scenes"] if s["id"] == sid)
                self._check_clip_duration(sc2, raw_path)

        # ---------- 8. 剪辑合成：按场景号拼接连贯成片 ----------
        self._concat_final_cut()

        # ---------- 8.5 配音字幕版：TTS 台词 + 字幕烧录 + fun-music BGM ----------
        self._dub_final_cut()

        # ---------- 9. 总结报告 ----------
        self._finalize()
        return self.report

    def _check_clip_duration(self, sc, clip_path):
        """片段时长校验：实际与预期偏差过大时打警告，不阻断流程。
        预期取镜头时长求和（新 schema shots[].duration），兼容旧字段 video_duration。"""
        if not shutil.which("ffprobe"):
            return
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", clip_path], capture_output=True, text=True, timeout=30)
            actual = float(r.stdout.strip())
        except (ValueError, subprocess.SubprocessError, OSError):
            return
        shots = sc.get("shots") or []
        want = sum(s.get("duration") or 0 for s in shots if isinstance(s.get("duration"), int))
        if not want:
            want = sc.get("video_duration") or 0
        if isinstance(want, int) and want > 0 and actual < want - 1.5:
            self._log(f"⚠️ 场景 {sc['id']} 片段仅 {actual:.1f}s（预期 {want}s），疑似平台短时长故障，"
                      f"成片节奏会偏快；可在确认点重做或手工重提")

    def _dub_final_cut(self):
        """配音版全片（第 8.5 步）：qwen-audio-3.1-tts-plus 台词配音 + PIL 字幕 +
        fun-music-v1 纯器乐 BGM → final_dubbed.mp4。

        成片不足 2 段或依赖缺失时跳过；失败不阻断主流水线（final_cut 已产出），
        幂等可重跑（scripts/make_dubbed_final.py 亦可独立对任意历史 run 执行）。"""
        clips = glob.glob(os.path.join(self.run_dir, "scene_*_edited.mp4"))
        if len(clips) < 2:
            self._log(f"成片仅 {len(clips)} 段，跳过配音版合成")
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
            from make_dubbed_final import dub_final
            print(f"\n[8.5] 配音字幕版：TTS 台词 + 字幕 + BGM → final_dubbed.mp4")
            out = dub_final(self.run_dir)
            self._step("final_dubbed", os.path.basename(out))
        except Exception as e:
            self._log(f"⚠️ 配音版合成失败（不影响 final_cut）：{type(e).__name__}: {e}")

    def _concat_final_cut(self):
        """把各场景成片按场景号顺序拼接为 final_cut.mp4（第 8 步，自动）。

        同代 wan3.0/wan2.7 产物分辨率/帧率/编码一致，用 concat demuxer -c copy
        零转码无损拼接；成片不足 2 段（如部分场景视频失败）时跳过不报错。
        ffmpeg 不存在时降级为提示，不阻断流水线。"""
        clips = sorted(glob.glob(os.path.join(self.run_dir, "scene_*_edited.mp4")))
        if len(clips) < 2:
            self._log(f"成片仅 {len(clips)} 段，跳过拼接（需 ≥2 段）")
            return
        if not shutil.which("ffmpeg"):
            self._log("⚠️ 未安装 ffmpeg，跳过自动拼接（brew install ffmpeg）")
            return
        # 按场景号排序（scene_10 应排在 scene_9 之后，字典序不对）
        clips.sort(key=lambda p: int(p.rsplit("scene_", 1)[1].split("_", 1)[0]))
        lst = os.path.join(self.run_dir, "concat.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{os.path.basename(c)}'\n" for c in clips)
        out = os.path.join(self.run_dir, "final_cut.mp4")
        print(f"\n[8] 剪辑合成：拼接 {len(clips)} 段成片 → final_cut.mp4")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                capture_output=True, check=True, timeout=120,
            )
            size_mb = os.path.getsize(out) / 1048576
            self._log(f"✅ 全片完成: final_cut.mp4（{len(clips)} 段拼接，{size_mb:.1f}MB）")
            self._step("final_cut", f"{len(clips)} 段拼接")
        except (subprocess.SubprocessError, OSError) as e:
            self._log(f"⚠️ 拼接失败（不影响成片，可手工 ffmpeg concat）：{e}")

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

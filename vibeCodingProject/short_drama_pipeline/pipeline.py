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
import sys
import json
import glob
import time
import hashlib
import math
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

    def __init__(self, theme="都市逆袭短剧", num_scenes=None, ims_real=False, target_qps=10,
                 resume_dir=None, confirm_cb=None, custom_images=None, custom_voice=None,
                 char_ref_image=None):
        self.llm = Qwen4MaxClient()
        self.gen = BailianAsyncClient()
        self.ims = IMSClient(real=ims_real)
        self.tm = TaskManager(self.gen, self.ims, target_qps=target_qps)
        self.confirm_cb = confirm_cb  # None=全自动；否则每步确认返回 (action, edited)
        # 客户图库模式：图先决（看图写分镜，跳过 AI 生图）；绝对路径列表，续跑时以
        # checkpoint 内的 custom_images（相对 run 目录的路径）为准
        self.custom_images = custom_images or []
        # 克隆音色：str=全局单音色；dict=多角色映射（角色名→voice_id，
        # 按分镜 scenes[].speaker 路由）。配音与口型驱动按场景选对应角色声音；
        # 续跑时从 checkpoint 恢复
        self.custom_voice = custom_voice
        # 女主角真实照片参考（换人/角色一致性锚定）：图库模式下用它把客户图
        # 里的女主角重制为照片人物（参考图生图：图1定人物、图2定场景）；
        # AI 生图模式下替代 AI 锚定图。续跑时从 checkpoint 恢复
        self.char_ref_image = char_ref_image
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
        # 恢复时以 checkpoint 内的主题/场数为准（忽略新传入值，避免口径错乱）；
        # 客户图库模式同理：续跑时从 checkpoint 恢复图路径列表
        self.theme = self.ckpt.get("theme", theme)
        self.num_scenes = self.ckpt.get("num_scenes", num_scenes)
        if self.ckpt.get("custom_images"):
            self.custom_images = [os.path.join(self.run_dir, c) if not os.path.isabs(c) else c
                                  for c in self.ckpt["custom_images"]]
        if self.ckpt.get("custom_voice"):
            self.custom_voice = self.ckpt["custom_voice"]
        if self.ckpt.get("char_ref_image"):
            ref_p = os.path.join(self.run_dir, self.ckpt["char_ref_image"])
            if os.path.isfile(ref_p):
                self.char_ref_image = ref_p
        # 角色参考图归档进 run 目录（统一命名 char_ref.png，续跑/重跑均按此复用）
        if self.char_ref_image and os.path.isfile(self.char_ref_image):
            dst_ref = os.path.join(self.run_dir, "char_ref.png")
            if os.path.abspath(self.char_ref_image) != os.path.abspath(dst_ref):
                shutil.copyfile(self.char_ref_image, dst_ref)
            self.char_ref_image = dst_ref
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
                if self.custom_images:
                    # 客户图库模式（图先决）：qwen4-max 多模态看图写分镜，
                    # 每张图必成为一个镜头首帧（seq 对应）；图先复制进 run 目录归档
                    for i, src in enumerate(self.custom_images, 1):
                        dst = os.path.join(self.run_dir, f"custom_{i:02d}{os.path.splitext(src)[1]}")
                        if not os.path.isfile(dst):
                            shutil.copyfile(src, dst)
                    self.custom_images = sorted(
                        glob.glob(os.path.join(self.run_dir, "custom_*.*")))
                    board = self.llm.generate_storyboard_with_images(
                        self.theme, self.custom_images, self.num_scenes)
                    print(f"  图库模式：{len(self.custom_images)} 张客户图 → 看图写分镜")
                else:
                    board = self.llm.generate_storyboard(self.theme, self.num_scenes)
                # num_scenes=None（AI 自动）时以 LLM 实际决策为准，回写后落入
                # checkpoint，续跑与后续日志/报告口径一致
                auto = self.num_scenes is None
                self.num_scenes = len(board["scenes"])
                self._log(f"共 {self.num_scenes} 场" + ("（AI 自动决策）" if auto else ""))
                with open(os.path.join(self.run_dir, "storyboard.json"), "w") as f:
                    json.dump(board, f, ensure_ascii=False, indent=2)
                self._save_ckpt(theme=self.theme, num_scenes=self.num_scenes, storyboard=board,
                                 custom_images=[os.path.basename(p) for p in self.custom_images],
                                 custom_voice=self.custom_voice)
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
            # 镜头清单：新 schema（shots[]）或兼容旧 schema（单镜头字段）。
            # 提前定义：客户图库分支与 AI 生图分支都依赖。
            def _shots_of(sc):
                if sc.get("shots"):
                    return sc["shots"]
                return [{"shot_id": 1, "framing": "中景",
                         "image_prompt": sc.get("image_prompt", ""),
                         "video_prompt": sc.get("video_prompt", ""),
                         "duration": sc.get("video_duration", -1)}]

            if images:
                print("  ♻️ 海报/锚定图/镜头首帧已生成，跳过（本地缺失时按 URL 重下）" if not images.get("custom")
                      else "  ♻️ 客户图库模式：首帧已绑定，跳过")
                if images.get("custom"):
                    # 客户图模式：首帧即 run 目录内 custom_*.* 文件，无需下载；
                    # poster 由图 1 兼任；无 AI 生图产物。
                    poster_url = poster_model = None
                    char_ref_url = None
                    stills = []
                    for item in images["stills"]:
                        shot = item.get("shot") or {"shot_id": 1, "framing": "中景",
                                                    "video_prompt": "", "duration": -1}
                        stills.append((item["scene"], shot, None,
                                       os.path.join(self.run_dir, item["local"])))
                    poster_local = stills[0][3] if stills else None
                else:
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
                # 对齐当前分镜：images.stills 里存的 scene/shot 是存图时的快照，
                # 打磨模式改分镜 / rework 脚本改词后即过时（run_011 实踩：口型
                # 镜头指纹比对用了旧快照台词，改词后旧视频被静默复用）。台词、
                # 时长档位、镜头参数一律以当前 storyboard 为准，快照仅作兑底。
                sc_map = {s["id"]: s for s in board["scenes"]}
                stills = [(sc_map.get(sc["id"], sc),
                           next((s for s in _shots_of(sc_map.get(sc["id"], sc))
                                 if s.get("shot_id") == shot.get("shot_id")), shot),
                           url, local)
                          for sc, shot, url, local in stills]
            else:
                # 客户图库模式：跳过 AI 生图，客户图直接作镜头首帧（图先决）。
                # poster/char_ref 同样不生成：海报由图 1 兼任，角色一致性由真实图
                # 天然保证（同一图库）；url 字段填 data URI 占位由视频步现转，
                # checkpoint 仍存 local 路径供续跑复用。
                if self.custom_images:
                    poster_url = poster_model = None
                    char_ref_url = None
                    poster_local = self.custom_images[0]
                    stills = []
                    for sc in board["scenes"]:
                        for shot in _shots_of(sc):
                            seq = shot.get("seq")
                            if not isinstance(seq, int) or not (1 <= seq <= len(self.custom_images)):
                                self._log(f"⚠️ 场景{sc['id']}-镜头{shot.get('shot_id')} 缺失有效 seq，"
                                          f"按顺序取下一张图")
                                seq = (len(stills) % len(self.custom_images)) + 1
                            stills.append((sc, shot, None, self.custom_images[seq - 1]))
                    print(f"  图库模式：{len(stills)} 个镜头直接使用 {len(self.custom_images)} 张客户图，跳过 AI 生图")
                    if self.char_ref_image:
                        # 真实照片角色参考（换人）：参考图生图重制每镜头首帧——
                        # 图1=char_ref.png（定人物面容发型），图2=原客户图（定场景
                        # 构图光影服饰），换人保景；原客户图保留归档可对照
                        print(f"  女主角替换：以 {os.path.basename(self.char_ref_image)}"
                              f" 为角色参考，参考图生图重制 {len(stills)} 个首帧…")
                        stills = self._regen_lead_stills(stills)
                        poster_local = stills[0][3] if stills else None
                else:
                    # 多镜头并行生图：海报 + 角色锚定图 + 各镜头首帧（qwen-image 同步接口）。
                    # 每镜头独立首帧（景别各异），角色锚定图作为 reference 供视频步角色一致性。
                    # 真实照片角色参考（char_ref_image）时：锚定图不再 AI 生成（照片即锚定），
                    # 海报/首帧改走参考图生图，女主角直接生成照片人物。
                    def _gen_one(job):
                        if job["kind"] == "poster":
                            if self.char_ref_image:
                                b64p, mimep = self.llm._encode_image(self.char_ref_image)
                                url, model = self.gen.ref_image2image(
                                    board["poster_prompt"] + "；女主角面容发型与第一张参考图完全一致。",
                                    [f"data:{mimep};base64,{b64p}"],
                                    [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                                    size="1536*2688",  # 9:16 竖版海报
                                )
                            else:
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
                            if self.char_ref_image:
                                b64p, mimep = self.llm._encode_image(self.char_ref_image)
                                url, model = self.gen.ref_image2image(
                                    shot["image_prompt"] + "；女主角面容发型与第一张参考图完全一致。",
                                    [f"data:{mimep};base64,{b64p}"],
                                    [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                                    size="1728*2368",  # 3:4 竖构图首帧
                                )
                            else:
                                url, model = self.gen.text2image(
                                    shot["image_prompt"],
                                    [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                                    size="1728*2368",  # 3:4 竖构图首帧
                                )
                            local = os.path.join(
                                self.run_dir, f"scene_{sc['id']}_shot{shot['shot_id']}_still.png")
                        self.gen.download(url, local)
                        return job, url, model, local

                    # 镜头清单（同外层 _shots_of）已提前定义

                    jobs = ([{"kind": "poster"}]
                            + ([] if self.char_ref_image else [{"kind": "char_ref"}])
                            + [{"kind": "still", "scene": sc, "shot": shot}
                               for sc in board["scenes"] for shot in _shots_of(sc)])
                    n_shots = len(jobs) - 1
                    if self.char_ref_image:
                        print(f"  并行提交 {len(jobs)} 个图像任务（海报 1 + 镜头首帧 {n_shots}，女主角参考图生图）…")
                    else:
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
                    "char_ref_image": (os.path.basename(self.char_ref_image)
                                       if self.char_ref_image else None),
                    "custom": bool(self.custom_images),
                    "stills": [{"scene": sc, "shot": shot, "url": url,
                                "local": os.path.basename(local)}
                               for sc, shot, url, local in stills],
                })
            self._step("images", ("客户图库模式：客户图直用，无 AI 生图" if self.custom_images
                                  else f"海报 1 + 锚定 1 + 镜头首帧 {len(stills)}（{poster_model}）"))
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
        for sc, shot, still_url, still_local in stills:
            # 时长决策：镜头级 duration；平台时段性故障规避：<8 档位规整为 8
            dur = shot.get("duration")
            if not isinstance(dur, int) or not (2 <= dur <= 30):
                dur = -1
            elif 0 < dur < 8:
                self._log(f"场景{sc['id']}-镜头{shot['shot_id']} duration={dur} 规整为 8（平台 <8s 档位 2s 故障规避）")
                dur = 8
            # 客户图库模式：图无公网 URL，降采样转 base64 data URI 直传
            # （实测 wan3.0/wan2.7 均接受，探测脚本 scripts/test_datauri_first_frame.py）
            if not still_url:
                b64, mime = self.llm._encode_image(still_local)
                still_url = f"data:{mime};base64,{b64}"
            key = (sc["id"], shot.get("shot_id", 1))
            # 口型镜头判定提前到复用决策前：台词指纹任一变化旧口型视频即作废
            needs_lipsync = bool(shot.get("needs_lipsync")) and bool(sc.get("dialogue"))
            dlg_hash = self._lipsync_hash(sc) if needs_lipsync else None
            saved = submitted.get(key)
            if (saved and saved.get("lipsync") and dlg_hash
                    and saved.get("dialogue_hash") not in (None, dlg_hash)):
                # 改词/换情绪/换音色后续跑：旧口型视频音轨还是旧台词，若静默复用
                # 会出现「字幕新台词、烧入音轨旧台词」（run_011 场景4 实踩）。
                # 剔除旧任务记录强制重新提交（TTS/口型重新生成，其余步骤照旧）
                self._save_ckpt(video_tasks=[t for t in ckpt.get("video_tasks", [])
                                             if not (t.get("scene_id") == sc["id"]
                                                     and t.get("shot_id") == key[1])])
                submitted.pop(key, None)
                saved = None
                self._log(f"场景{sc['id']}-镜头{key[1]} 台词已修改，旧口型镜头作废重新生成")
            if saved:
                task_id, model = saved["task_id"], saved["model"]
                self._log(f"场景{sc['id']}-镜头{shot['shot_id']} ♻️ 复用已提交任务（{model}）")
                rec = self.tm.add_bailian_task(task_id, "bailian_video",
                                               f"场景{sc['id']}-镜头{shot['shot_id']}({model})")
                video_records.append((sc, shot, rec, model, None))
                self.report["models_used"].add(model)
                continue
            # 新提交：三层路由（口型镜头 / 角色锚定参考 / 首帧驱动）。
            # 真实照片角色参考时首帧已携带照片人物（换人重制/参考生图），
            # 首帧驱动即可保人物一致，不再叠加 reference_image（wan3.0 的
            # first_frame 与 reference_image 互斥，构图控制优先走首帧）。
            ref_urls = [char_ref_url, still_url] \
                if (char_ref_url and not self.char_ref_image) else []
            take_jobs = []  # [(take_id, task_id, model)]
            audio_url = None
            if needs_lipsync:
                # 口型镜头前置：先合成台词 TTS 音轨（driving_audio 需公网 URL）。
                # 上传用百炼临时存储：dashscope 内置 OSS 通道（voice 同款接口返回的 URL 不可复用，
                # 改用百炼文件上传 API 拿公网 URL）。
                audio_url = self._prep_driving_audio(sc, shot)
                if not audio_url:
                    self._log(f"⚠️ 场景{sc['id']}-镜头{shot['shot_id']} 口型音轨准备失败，回退常规生成")
                    needs_lipsync = False
                else:
                    # 时长档位随台词音轨定：视频档位长于台词时尾部会生成
                    # 「嘴动无声」的表演段（详见 _lipsync_duration）
                    dur = self._lipsync_duration(sc, dur)
            for take_id in range(TAKES if not needs_lipsync else 1):  # 口型镜头单 take（成本高）
                if needs_lipsync:
                    # 口型路径：默认 wan3.0 语音带入（reference_image+reference_audio，
                    # 91s/条实测），wan2.7-i2v first_frame+driving_audio 作降级
                    task_id, model = self.gen.lipsync2video(
                        shot["video_prompt"], still_url, audio_url,
                        [config.LIPSYNC_MODEL] + config.LIPSYNC_MODEL_FALLBACKS,
                        resolution="720P", duration=dur,
                    )
                    self._log(f"场景{sc['id']}-镜头{shot['shot_id']} 口型同步提交（{model}，台词驱动）")
                elif ref_urls:
                    # 参考生视频：锚定图保角色一致，prompt 描述构图/运镜
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
                if not needs_lipsync:
                    self._log(f"场景{sc['id']}-镜头{shot['shot_id']} take{take_id + 1} 已提交（{model}, {dur if dur > 0 else '智能'}s）")
                task_rec = {"scene_id": sc["id"], "shot_id": shot.get("shot_id", 1),
                            "take_id": take_id, "task_id": task_id, "model": model,
                            "lipsync": needs_lipsync}
                if needs_lipsync:
                    # 台词指纹落盘：续跑时比对，改词强制重生成口型镜头
                    task_rec["dialogue_hash"] = dlg_hash
                self._ckpt_append("video_tasks", task_rec)
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
                                      f"scene_{key[0]}_shot{key[1]}_take{take_id if take_id is not None else 'r'}.mp4")
            self.gen.download(url, take_local)
            if bool(shot.get("needs_lipsync")) and bool(sc.get("dialogue")):
                self._trim_lipsync_tail(take_local, sc, shot, take_id)
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
                else:  # concat 失败（编码不一致等）→ 统一画布转码拼接兜底
                    inputs, fc = [], []
                    for i, k in enumerate(keys):
                        inputs += ["-i", chosen_take_local[k]]
                        fc.append(f"[{i}:v]scale=1080:1440:force_original_aspect_ratio=decrease,"
                                  f"pad=1080:1440:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]")
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
        lipsync_sids = {t["scene_id"] for t in ckpt.get("video_tasks", []) if t.get("lipsync")}
        for sc in board["scenes"]:
            raw_path = scene_raw.get(sc["id"])
            if not raw_path:
                self._log(f"场景 {sc['id']} 无可用片段，跳过编辑")
                continue
            if sc["id"] in lipsync_sids:
                # 口型保护：videoedit 重绘会破坏逐字口型并丢失台词音轨，
                # 含 lipsync 镜头的场景直接用场内拼接原片作为成片
                scene_edited = os.path.join(self.run_dir, f"scene_{sc['id']}_edited.mp4")
                shutil.copyfile(raw_path, scene_edited)
                self._check_clip_duration(sc, scene_edited, lipsync=True)
                self._log(f"场景 {sc['id']} 含口型镜头，跳过生成式编辑（保护口型与台词音轨）")
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
                    video_url,
                    [config.VIDEOEDIT_MODEL] + config.VIDEOEDIT_MODEL_FALLBACKS,
                    resolution="720P",
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

    def _regen_lead_stills(self, stills):
        """图库模式 + 真实照片角色参考：参考图生图重制镜头首帧（换人保景）。

        图1=char_ref.png（定女主角面容发型），图2=原客户图（定场景构图灯光
        服饰动作姿态）；产物 lead_s{sid}_shot{shid}.png，原 custom_* 保留
        归档可对照。多镜头并行提交（同步接口，每张约 1-4 分钟）；原图比例
        各异（4:3 / 16:9 / 3:4 混排），size 逐张跟随原图不裁切。"""
        b64, mime = self.llm._encode_image(self.char_ref_image)
        photo_uri = f"data:{mime};base64,{b64}"

        def _gen_one(item):
            sc, shot, _old_url, custom_local = item
            try:
                from PIL import Image
                w, h = Image.open(custom_local).size
            except Exception:
                w, h = 1728, 2368  # PIL 缺失/图损坏时回退 3:4
            b2, m2 = self.llm._encode_image(custom_local)
            scene_uri = f"data:{m2};base64,{b2}"
            prompt = (
                "把第二张图场景中的女主角替换为第一张参考照片中的女士："
                "面容与发型完全采用参考照片人物，保留第二张图的场景、构图、"
                "灯光氛围、人物动作姿态与服饰，女主角以外的元素保持不变；"
                f"写实摄影风格。剧情语境：{sc['desc'][:100]}"
            )
            url, model = self.gen.ref_image2image(
                prompt, [photo_uri, scene_uri],
                [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS,
                size=f"{w}*{h}")
            local = os.path.join(
                self.run_dir, f"lead_s{sc['id']}_shot{shot.get('shot_id', 1)}.png")
            self.gen.download(url, local)
            return sc, shot, url, local, model

        new_stills = []
        with ThreadPoolExecutor(max_workers=min(len(stills), 4)) as pool:
            futures = [pool.submit(_gen_one, it) for it in stills]
            for fut in as_completed(futures):
                sc, shot, url, local, model = fut.result()  # 单任务失败整体抛错，续跑重试
                self.report["models_used"].add(model)
                new_stills.append((sc, shot, url, local))
                self._log(f"场景 {sc['id']}-镜头{shot.get('shot_id', 1)}"
                          f" 女主角重制首帧完成（{model}）")
        new_stills.sort(key=lambda x: (x[0]["id"], x[1].get("shot_id", 1)))
        return new_stills

    def _check_clip_duration(self, sc, clip_path, lipsync=False):
        """片段时长校验：实际与预期偏差过大时打警告，不阻断流程。
        预期取镜头时长求和（新 schema shots[].duration），兼容旧字段 video_duration。
        口型镜头（lipsync=True）时长由台词音轨决定（片尾静音已裁剪），
        分镜 duration 不再适用，只校验「台词音轨未被截断」。"""
        if not shutil.which("ffprobe"):
            return
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", clip_path], capture_output=True, text=True, timeout=30)
            actual = float(r.stdout.strip())
        except (ValueError, subprocess.SubprocessError, OSError):
            return
        if lipsync:
            voice = os.path.join(self.run_dir, f"voice_{sc['id']}.mp3")
            try:
                r = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", voice], capture_output=True, text=True, timeout=30)
                ad = float(r.stdout.strip())
            except (ValueError, subprocess.SubprocessError, OSError):
                return
            if actual + 0.3 < ad:
                self._log(f"⚠️ 场景 {sc['id']} 口型片段 {actual:.1f}s 短于台词音轨 {ad:.1f}s，"
                          f"台词尾字可能被截断")
            return
        shots = sc.get("shots") or []
        want = sum(s.get("duration") or 0 for s in shots if isinstance(s.get("duration"), int))
        if not want:
            want = sc.get("video_duration") or 0
        if isinstance(want, int) and want > 0 and actual < want - 1.5:
            self._log(f"⚠️ 场景 {sc['id']} 片段仅 {actual:.1f}s（预期 {want}s），疑似平台短时长故障，"
                      f"成片节奏会偏快；可在确认点重做或手工重提")

    def _voice_for(self, sc):
        """按场景选克隆音色：voice_map（dict）时用分镜 speaker 路由到该角色的
        voice_id；无匹配回退全局音色（str）；都不是则 None（用默认旗舰音色）。"""
        vc = self.custom_voice
        if isinstance(vc, dict):
            speaker = (sc.get("speaker") or "").strip()
            if speaker and speaker in vc:
                return vc[speaker]
            if speaker:
                self._log(f"⚠️ 场景{sc.get('id')} speaker「{speaker}」无对应克隆音色，"
                          f"回退默认音色（可用角色：{list(vc.keys())}）")
            return None
        return vc

    def _lipsync_hash(self, sc):
        """口型镜头台词指纹：dialogue / voice_mood / 音色任一变化，
        旧口型视频的烧入音轨即与新台词不一致，续跑时强制重生成。"""
        raw = "|".join([sc.get("dialogue") or "", sc.get("voice_mood") or "",
                        str(self._voice_for(sc) or "")])
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _lipsync_duration(self, sc, fallback):
        """口型镜头时长按台词音轨实测定档（run_011 实测：视频按 8s 档出片、
        台词只有 2-3s，音频结束后 wan2.7-i2v 继续外推张嘴动作 → 尾部嘴动无声）。
        取 语音时长+0.8s 缓冲向上取偶数档，不低于 8（平台 <8 档位 2s 故障
        规避），封顶 30；音轨探测失败回退 fallback（剩余尾部静音由
        trim_speech_tail 兜底裁剪）。"""
        local = os.path.join(self.run_dir, f"voice_{sc['id']}.mp3")
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", local], capture_output=True, text=True, timeout=30)
            ad = float(r.stdout.strip())
        except (ValueError, subprocess.SubprocessError, OSError):
            return fallback
        want = min(30, max(8, int(math.ceil((ad + 0.8) / 2.0)) * 2))
        self._log(f"场景{sc['id']} 口型镜头时长按台词音轨定档：{want}s（音轨 {ad:.1f}s）")
        return want

    def _trim_lipsync_tail(self, take_local, sc, shot, take_id):
        """口型 take 下载后裁掉片尾静音段（嘴动无声尾巴，详见
        make_dubbed_final.trim_speech_tail）。失败静默跳过不阻断
        （mock 测试的假文件探测必然失败，跳过即可）。"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
            from make_dubbed_final import trim_speech_tail
            trimmed, new_dur = trim_speech_tail(take_local)
            if trimmed:
                self._log(f"场景{sc['id']}-镜头{shot.get('shot_id', 1)}-take{take_id} "
                          f"片尾静音已裁剪（现 {new_dur:.1f}s）")
        except Exception:
            pass

    def _prep_driving_audio(self, sc, shot):
        """口型镜头前置：台词 TTS 合成 → 直接用 TTS 返回的公网签名 URL。

        wan2.7-i2v 的 driving_audio 仅接受公网 HTTP(S) URL（官方 API 参考）：
        - 百炼 uploads 两步上传（getPolicy→OSS）返回的 oss:// 地址会被拒（实测
          报 Failed to download oss://…，且 OSS 对象私有 403 不可公开读）；
        - TTS 接口响应自带 dashscope OSS 签名 URL，合成后立即提交时效足够；
        同时落盘 voice_{sid}.mp3 供第 8.5 步配音字幕复用（不重复合成）。
        失败返回 None（上层回退常规生成）。"""
        local = os.path.join(self.run_dir, f"voice_{sc['id']}.mp3")
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
            from make_dubbed_final import synth, MOOD_CYCLE
            line = sc.get("dialogue", "")
            # 情绪优先用分镜的 voice_mood（贴合人设），缺失时兑底 MOOD_CYCLE；
            # 已有本地音轨但 URL 过期不可复用（签名有时效）：重合成拿新 URL；
            # 克隆音色模式下台词用客户本人的声音驱动口型
            mood = sc.get("voice_mood") or MOOD_CYCLE[(sc["id"] - 1) % len(MOOD_CYCLE)]
            audio_url = synth(line, mood, local, voice=self._voice_for(sc))
            self._log(f"场景{sc['id']} 台词音轨已合成"
                      + (f"（{sc.get('speaker') or '旁白'}，克隆音色）"
                         if self._voice_for(sc) else "")
                      + "（口型驱动用，公网 URL）")
            return audio_url
        except Exception as e:
            self._log(f"⚠️ 台词 TTS 失败：{e}")
            return None

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
            print(f"\n[8.5] 配音字幕版：TTS 台词 + 字幕 + BGM → final_dubbed.mp4"
                  + ("（多角色克隆音色）" if isinstance(self.custom_voice, dict)
                     else "（克隆音色）" if self.custom_voice else ""))
            out = dub_final(self.run_dir, voice=self.custom_voice)
            self._step("final_dubbed", os.path.basename(out))
            # 台词质检（8.6）：ASR 识别配音与分镜台词逐场比对，相似度低于阈值告警。
            # 背景：run_010 曾发生 TTS 情绪指令被克隆音色当台词朗读的事故
            # （[俏皮重庆妹儿] 被念出来），无质检则静默进入成片。仅旁白场景受检
            # （口型镜头台词已烧进视频音轨）。仅告警不阻断（ASR 有识别噪声）。
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
                from qa_dubbing import asr as asr_text, similarity
                board = json.load(open(os.path.join(self.run_dir, "storyboard.json")))
                for sc in board["scenes"]:
                    line = sc.get("dialogue", "")
                    if not line or sc["id"] in self._lipsync_scene_ids(self.run_dir):
                        continue
                    audio = os.path.join(self.run_dir, f"voice_{sc['id']}.mp3")
                    if not os.path.isfile(audio):
                        continue
                    sim = similarity(asr_text(audio), line)
                    if sim < 0.85:
                        self._log(f"⚠️ 台词质检：场景{sc['id']} ASR 相似度 {sim:.0%}，"
                                  f"疑似指令被朗读/幻觉/漏读，建议重跑配音（scripts/qa_dubbing.py）")
                    else:
                        self._log(f"✅ 台词质检：场景{sc['id']} ASR 相似度 {sim:.0%}")
            except Exception as e:
                self._log(f"⚠️ 台词质检跳过：{type(e).__name__}: {e}")
        except Exception as e:
            self._log(f"⚠️ 配音版合成失败（不影响 final_cut）：{type(e).__name__}: {e}")

    @staticmethod
    def _lipsync_scene_ids(run_dir):
        """checkpoint 中标记了 lipsync 的镜头所在场景集合（配音质检时跳过它们：
        台词已烧进视频音轨，旁白 ASR 比对不适用）。"""
        try:
            ck = json.load(open(os.path.join(run_dir, "checkpoint.json")))
            return {t["scene_id"] for t in ck.get("video_tasks", []) if t.get("lipsync")}
        except (OSError, json.JSONDecodeError, KeyError):
            return set()

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
        # 主动检测分辨率一致性：-c copy 对多分辨率混合会“成功”但只保留首段规格
        # （其余段被播放器拉伸，客户图库模式必踩）；不一致时直接走统一画布转码
        resos = set()
        for c in clips:
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height",
                                "-of", "csv=p=0", c], capture_output=True, text=True)
            if r.stdout.strip():
                resos.add(r.stdout.strip())
        uniform = len(resos) <= 1
        try:
            if not uniform:
                raise subprocess.CalledProcessError(1, "ffmpeg")  # 直接走转码兑底
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                capture_output=True, check=True, timeout=120,
            )
        except (subprocess.SubprocessError, OSError):
            # 编码/分辨率不一致（如客户图库模式各段随原图比例各异）：
            # 内接缩放到 3:4 画布 + 居中 pad 统一规格后转码拼接（不裁切不变形）
            try:
                inputs, fc = [], []
                for i, c in enumerate(clips):
                    inputs += ["-i", c]
                    fc.append(f"[{i}:v]scale=1080:1440:force_original_aspect_ratio=decrease,"
                              f"pad=1080:1440:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]")
                    fc.append(f"[{i}:a]aresample=44100[a{i}]")
                # 链式 concat：上一步的输出 [vc{i-1}] 接下一段，不是原流 v{i}
                prev_v, prev_a = "v0", "a0"
                for i in range(1, len(clips)):
                    out_v, out_a = (f"vc{i}", f"ac{i}") if i < len(clips) - 1 else ("vc", "ac")
                    fc.append(f"[{prev_v}][v{i}]concat=n=2:v=1:a=0[{out_v}]")
                    fc.append(f"[{prev_a}][a{i}]concat=n=2:v=0:a=1[{out_a}]")
                    prev_v, prev_a = out_v, out_a
                subprocess.run(
                    ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
                     "-map", "[vc]", "-map", "[ac]",
                     "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", out],
                    capture_output=True, check=True, timeout=300,
                )
            except (subprocess.SubprocessError, OSError) as e:
                self._log(f"⚠️ 拼接失败（不影响成片，可手工 ffmpeg concat）：{e}")
                return
        size_mb = os.path.getsize(out) / 1048576
        self._log(f"✅ 全片完成: final_cut.mp4（{len(clips)} 段拼接，{size_mb:.1f}MB）")
        self._step("final_cut", f"{len(clips)} 段拼接")

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

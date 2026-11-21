"""qwen4-max 客户端（北京节点 OpenAI 兼容模式）。

两类用途（对应配额申请中『资料整理、检索、图像理解及质量验收』）：
- chat(): 剧本/分镜 JSON 结构化生成（资料整理）
- chat_with_image(): 多模态输入，图像质量验收（视觉理解）
"""
import base64
import io
import json
import os
import random
import re
import time
import requests

import config


class Qwen4MaxClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=120):
        self.api_key = api_key or config.API_KEY
        self.base_url = (base_url or config.OPENAI_BASE_URL).rstrip("/")
        self.model = model or config.LLM_MODEL
        self.timeout = timeout

    def chat(self, messages, temperature=0.7, max_tokens=2000, stream=False, enable_thinking=False):
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            # qwen4 代思考模型：思考默认开启，max_tokens 含思考额度；结构化生成场景关闭
            "enable_thinking": enable_thinking,
        }
        for _ in range(2):
            for attempt in range(3):
                try:
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=body,
                        timeout=self.timeout,
                    )
                    break
                except requests.RequestException as e:
                    # 多模态大请求偶发写超时/连接重置：全抖动退避重试
                    wait = random.uniform(0, 2 ** attempt + 1)
                    print(f"    ⚠️ qwen4-max 网络错误（{type(e).__name__}），退避 {wait:.1f}s 后重试", flush=True)
                    time.sleep(wait)
            else:
                raise RuntimeError("qwen4-max 网络重试耗尽")
            data = resp.json()
            # 部分商用型号不接受 enable_thinking 字段：去除后重试一次
            if resp.status_code == 400 and "enable_thinking" in str(data.get("message", "")):
                body.pop("enable_thinking", None)
                continue
            break
        if resp.status_code != 200:
            raise RuntimeError(f"qwen4-max 调用失败 HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:300]}")
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _encode_image(image_path, max_side=1024, quality=85):
        """图片降采样后转 base64（JPEG）。

        原图（1728*2368 PNG ≈ 4.8MB）直接 base64 成 ~6.4MB 单请求体时，
        长距离链路频繁 write timeout；缩到 ≤1024px JPEG 后请求体 ≈150KB。
        """
        try:
            from PIL import Image
            im = Image.open(image_path)
            im.thumbnail((max_side, max_side))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, format="JPEG", quality=quality)
            return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
        except Exception:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
            return b64, mime

    def chat_with_image(self, prompt, image_path, question=None, max_tokens=800):
        """多模态质量验收：本地图片 → 降采样 base64 → image_url。"""
        b64, mime = self._encode_image(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": question or prompt},
                ],
            }
        ]
        return self.chat(messages, temperature=0.2, max_tokens=max_tokens)

    def generate_storyboard(self, theme="都市逆袭短剧", num_scenes=None):
        """生成短剧分镜脚本（结构化 JSON，多镜头 shot list 版）。

        每场拆 2-3 个镜头（业内实践：短剧平均 2-4s 切镜，景别必须有变化，
        远全交代环境→中景推叙事→近特写给情绪）；另出 character_ref_prompt
        （主角标准像提示词）供角色锚定图生成，保全片角色一致性。
        num_scenes=None 时场景数量由 LLM 按剧情复杂度自行决定（业内做法，
        界面默认 AI 自动）；显式传值则为人工指定。"""
        if num_scenes:
            scenes_hint = f"共 {num_scenes} 个场景。"
        else:
            scenes_hint = ("场景数量由你根据主题的剧情复杂度自行决定（1-4 场）："
                           "单一日常小事或单一情绪短片 1-2 场；有地点转换、起承转合的完整小故事 2-3 场；"
                           "复仇/逆袭/多重反转等强剧情 3-4 场。宁少勿滥，每场都必须有不可删的剧情价值。")
        prompt = f"""你是短剧制作流水线的总编剧兼分镜师。请为主题「{theme}」创作一段竖屏短剧的分镜脚本。
要求输出严格的 JSON（不要 markdown 代码块、不要多余文字），结构如下：
{{
  "title": "剧名",
  "logline": "一句话剧情",
  "poster_prompt": "竖版海报的文生图提示词（中文，包含画面主体、氛围、风格）",
  "character_ref_prompt": "主角标准像提示词（中文，正面清晰半身照，明确发型服饰面容，背景纯色，供全片角色一致性参考）",
  "scenes": [
    {{
      "id": 1,
      "desc": "剧情描述",
      "speaker": "本场景开口说话/旁白的角色名（无台词则填空字符串；多角色短剧时由配音步按角色路由克隆音色）",
      "dialogue": "一句台词",
      "voice_mood": "这句台词的说话方式（自然语言：语气/情绪/语速，须与人物身份和剧情情绪一致，20字内；无台词则填空字符串）",
      "shots": [
        {{
          "shot_id": 1,
          "framing": "景别（远景/全景/中景/近景/特写）",
          "image_prompt": "本镜头首帧的文生图提示词（中文，含人物状态/构图/光线，3:4 竖构图）",
          "video_prompt": "本镜头的运动与运镜提示词（中文，单镜头单一运镜，节奏与景别匹配）",
          "duration": 本镜头时长秒数（2-8 的整数；特写反应 2-3s，中景动作 4-6s，环境交代 6-8s），
          "needs_lipsync": 是否需要口型同步（true/false；仅当【正面近景/特写 且 有人物开口说台词】时 true，
                          其余一律 false——中远景台词用画外音+字幕即可，不必浪费口型链路）
        }},
        {{"shot_id": 2, "framing": "...", "image_prompt": "...", "video_prompt": "...", "duration": 4}}
      ],
      "edit_instruction": "对场景成片做生成式编辑的指令（如：把背景替换为雨夜街头）"
    }}
  ]
}}
每场拆 2-3 个镜头，景别必须有变化（不得全为同一景别），镜头切换服务剧情节奏；
同一主角在各镜头的发型服饰面容必须一致（与 character_ref_prompt 呼应）；
voice_mood 必须贴合人物身份与剧情情绪（如霸道总裁用沉稳从容的语气，不用"俏皮妹儿"），仅描述语气不写入台词本身；
全片 needs_lipsync 的镜头不超过 1-2 个（选台词最关键、最适合特写的那句），其余台词走画外音。
{scenes_hint}"""
        raw = self.chat([{"role": "user", "content": prompt}], temperature=0.8, max_tokens=2500)
        return self._extract_json(raw)

    def generate_storyboard_with_images(self, theme, image_paths, num_scenes=None):
        """客户图库模式：qwen4-max 多模态「看图写分镜」。

        剧情围绕客户图来写（图先决）而非先生成分镜再硬配图：每张图必成为一个
        镜头首帧（seq 与图片顺序一一对应），剧情/台词/运镜必须与图内容严格自洽；
        场景数量由图数与剧情共同决定。返回的 shots 内含 seq 字段指向图序号。"""
        if num_scenes:
            scenes_hint = f"场景数固定为 {num_scenes} 场。"
        else:
            scenes_hint = "场景数量由你根据图片内容与剧情复杂度自行决定。"
        question = (
            f"这些是客户图库中的图片（按顺序编号 1-{len(image_paths)}）。"
            f"请围绕这些图为主题「{theme}」创作竖屏短剧分镜，剧情必须与图内容自洽，"
            "要求输出严格的 JSON（不要 markdown 代码块），结构必须完全如下（字段名逐一照抄，不得自创同义词）：" + chr(10)
            + "{" + chr(10)
            + "  \"title\": \"剧名\"," + chr(10)
            + "  \"logline\": \"一句话剧情\"," + chr(10)
            + "  \"character_ref_prompt\": \"主角标准像描述（供参考）\"," + chr(10)
            + "  \"scenes\": [" + chr(10)
            + "    {" + chr(10)
            + "      \"id\": 1," + chr(10)
            + "      \"desc\": \"剧情描述\"," + chr(10)
            + "      \"speaker\": \"本场景开口说话的角色名（无台词填空）\"," + chr(10)
            + "      \"dialogue\": \"一句台词（可为空字符串）\"," + chr(10)
            + "      \"voice_mood\": \"这句台词的说话方式（语气/情绪，贴合人物身份，20字内；无台词填空）\"," + chr(10)
            + "      \"shots\": [" + chr(10)
            + "        {" + chr(10)
            + "          \"shot_id\": 1," + chr(10)
            + f"          \"seq\": 图序号（1-{len(image_paths)}），每个镜头必填、不得为空，" + chr(10)
            + "          \"framing\": \"景别（远景/全景/中景/近景/特写）\"," + chr(10)
            + "          \"image_prompt\": \"描述对应图画面（供参考，不用于生图）\"," + chr(10)
            + "          \"video_prompt\": \"本镜头的运动与运镜提示词（与图内容一致：图中人物服饰/场景/光线是既定事实）\"," + chr(10)
            + "          \"duration\": 本镜头时长秒数（2-8 的整数），" + chr(10)
            + "          \"needs_lipsync\": false（仅【正面近景/特写且开口说台词】才 true，全片 ≤1-2 个）" + chr(10)
            + "        }" + chr(10)
            + "      ]," + chr(10)
            + "      \"edit_instruction\": \"对场景成片做生成式编辑的指令\"" + chr(10)
            + "    }" + chr(10)
            + "  ]" + chr(10)
            + "}" + chr(10)
            + "硬性约束：镜头总数必须等于图片数量，每个镜头的 seq 与图一一对应（可用不同图，但不得虚构没有对应图的新镜头，也不得遇漏任何一张图）；"
              "不得使用 scene_id/scene_name/shot_size/camera_movement/action/sound 等自创字段名。" + chr(10)
            + f"{scenes_hint} 共 {len(image_paths)} 张图。"
        )
        # 多图多模态消息：文本指令在前，图片依序附后（与 chat_with_image 同降采样规格）
        content = [{"type": "text", "text": question}]
        for p in image_paths:
            b64, mime = self._encode_image(p)
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"}})
        raw = self.chat([{"role": "user", "content": content}], temperature=0.8, max_tokens=2500)
        return self._extract_json(raw)

    def review_image(self, image_path, scene_desc, dialogue):
        """质量验收：用多模态输入校验镜头首帧是否符合分镜要求，返回结构化评价。"""
        question = (
            f"这是一张短剧分镜的生成图。分镜要求：{scene_desc}；台词：{dialogue}。"
            "请从以下维度验收并输出严格 JSON（不要 markdown）："
            "{\"pass\": true/false, \"score\": 0-10, \"issues\": [\"问题列表\"], \"summary\": \"一句话结论\"}"
        )
        raw = self.chat_with_image(question, image_path)
        return self._extract_json(raw)

    def pick_take(self, take_paths, shot_desc):
        """双 take 挑优：对同一镜头的两条生成视频抽帧后多模态打分，返回较优序号（0/1）。

        抽各 take 的首/中/尾三帧拼为一图比较，避免上传整段视频；
        返回 (chosen_index, reason)。"""
        import subprocess as sp
        import tempfile
        from PIL import Image
        frames = []
        tmpdir = tempfile.mkdtemp(prefix="take_")
        for i, tp in enumerate(take_paths):
            for tag, t in (("s", 0.1), ("m", 0.5), ("e", 0.9)):
                out = os.path.join(tmpdir, f"t{i}{tag}.jpg")
                sp.run(["ffmpeg", "-y", "-ss", str(t), "-i", tp, "-frames:v", "1",
                        "-vf", "scale=360:-2", out], capture_output=True)
                if os.path.isfile(out):
                    frames.append(out)
        if len(frames) < 2:
            return 0, "抽帧失败，默认选第一条"
        # 拼 2×3 网格对比图（take1 三帧上排，take2 三帧下排）
        grid = Image.new("RGB", (360 * 3, 640 * 2), (20, 20, 20))
        for idx, fp in enumerate(frames[:6]):
            img = Image.open(fp).convert("RGB")
            grid.paste(img, ((idx % 3) * 360, (idx // 3) * 640))
        grid_path = os.path.join(tmpdir, "grid.jpg")
        grid.save(grid_path, quality=85)
        question = (
            f"同一镜头生成了两条候选视频（上排=第一条的前/中/后帧，下排=第二条）。" + chr(10)
            + f"镜头要求：{shot_desc}。请从画面质量、人物一致性、运动自然度、瑕疵 artifacts "
            "四维评估哪条更好，输出严格 JSON（不要 markdown）："
            "{\"better\": 0 或 1, \"reason\": \"一句话理由\"}"
        )
        raw = self.chat_with_image(question, grid_path, max_tokens=300)
        result = self._extract_json(raw)
        chosen = 1 if result.get("better") == 1 else 0
        return chosen, result.get("reason", "")

    @staticmethod
    def _extract_json(raw):
        """从模型输出中稳健抽取 JSON（容忍代码块包裹）。"""
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m:
            raw = m.group(1)
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise ValueError(f"无法从模型输出解析 JSON: {raw[:200]}")

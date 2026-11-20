"""qwen4-max 客户端（北京节点 OpenAI 兼容模式）。

两类用途（对应配额申请中『资料整理、检索、图像理解及质量验收』）：
- chat(): 剧本/分镜 JSON 结构化生成（资料整理）
- chat_with_image(): 多模态输入，图像质量验收（视觉理解）
"""
import base64
import io
import json
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

    def generate_storyboard(self, theme="都市逆袭短剧", num_scenes=1):
        """生成短剧分镜脚本（结构化 JSON）。"""
        prompt = f"""你是短剧制作流水线的总编剧。请为主题「{theme}」创作一段竖屏短剧的分镜脚本。
要求输出严格的 JSON（不要 markdown 代码块、不要多余文字），结构如下：
{{
  "title": "剧名",
  "logline": "一句话剧情",
  "poster_prompt": "竖版海报的文生图提示词（中文，包含画面主体、氛围、风格）",
  "scenes": [
    {{
      "id": 1,
      "desc": "剧情描述",
      "dialogue": "一句台词",
      "image_prompt": "该场景剧照的文生图提示词（中文，含人物/场景/光线/风格，2:3 竖构图）",
      "video_prompt": "图生视频的运动与运镜提示词（中文）",
      "video_duration": 建议视频时长秒数（2-30 的整数，按剧情动作量与镜头节奏判断：单一反应特写 2-3s，
一个完整动作与调度 5-8s，多人物调度或长镜头 8-12s），
      "edit_instruction": "对生成视频做生成式编辑的指令（如：把背景替换为雨夜街头）"
    }}
  ]
}}
共 {num_scenes} 个场景。"""
        raw = self.chat([{"role": "user", "content": prompt}], temperature=0.8, max_tokens=1500)
        return self._extract_json(raw)

    def review_image(self, image_path, scene_desc, dialogue):
        """质量验收：用多模态输入校验剧照是否符合分镜要求，返回结构化评价。"""
        question = (
            f"这是一张短剧分镜的生成图。分镜要求：{scene_desc}；台词：{dialogue}。"
            "请从以下维度验收并输出严格 JSON（不要 markdown）："
            "{\"pass\": true/false, \"score\": 0-10, \"issues\": [\"问题列表\"], \"summary\": \"一句话结论\"}"
        )
        raw = self.chat_with_image(question, image_path)
        return self._extract_json(raw)

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

"""DashScope 原生异步任务客户端（北京节点 workspace 端点）。

覆盖三类生成接口（均为异步任务：提交 -> 轮询 GET /api/v1/tasks/{task_id}）：
- 文生图：POST /services/aigc/text2image/image-synthesis
- 视频（文生/图生/参考生，wan3.0-video / wan2.7 系列）：
  POST /services/aigc/video-generation/video-synthesis
- 生成式视频编辑（wan2.7-videoedit）：同 video-synthesis 路径，input 带 video_url

统一处理：限流（Throttling）退避重试、模型不可用降级候选、任务结果下载。
"""
import os
import time
import json
import random
import requests

import config

IMAGE_PATH = "/services/aigc/text2image/image-synthesis"
VIDEO_PATH = "/services/aigc/video-generation/video-synthesis"
TASK_POLL_PATH = "/tasks/{task_id}"
# qwen-image 系列：同步接口，请求体为 input.messages 结构，响应直接携带图片 URL
QWEN_IMAGE_SYNC_PATH = "/services/aigc/multimodal-generation/generation"

# 限流/可重试错误码
THROTTLING_CODES = {"Throttling", "Throttling.RateQuota", "Throttling.AssociatedFlowControl"}
# 模型不可用类错误码（触发候选模型降级）
MODEL_UNAVAILABLE_CODES = {"model_not_found", "Model.AccessDenied", "AccessDenied"}


class ModelNotAvailableError(Exception):
    """模型在北京节点不可用（未开通/不存在），应尝试降级候选。"""


class ThrottledError(Exception):
    """限流重试耗尽（配额级问题）：换下一候选模型（额度独立）而非硬等窗口。"""


class BailianAsyncClient:
    def __init__(self, api_key=None, base_url=None, timeout=60):
        self.api_key = api_key or config.API_KEY
        self.base_url = (base_url or config.NATIVE_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # ---------- 底层请求 ----------
    def _headers(self, async_mode=True):
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if async_mode:
            h["X-DashScope-Async"] = "enable"
        return h

    def _post_task(self, body, max_retry=3):
        """提交异步任务，返回 task_id；限流时退避重试。"""
        url = self.base_url + VIDEO_PATH if body.get("_kind") == "video" else self.base_url + IMAGE_PATH
        body = {k: v for k, v in body.items() if not k.startswith("_")}
        last_err = None
        for attempt in range(max_retry):
            try:
                resp = self.session.post(url, headers=self._headers(), json=body, timeout=self.timeout)
            except requests.RequestException as e:
                # 网络级错误（连接重置/超时）同样退避重试，否则长流水线一抖就整条挂
                wait = random.uniform(0, 2 ** attempt + 1)
                print(f"    ⚠️ 网络错误（{type(e).__name__}），退避 {wait:.1f}s 后重试")
                time.sleep(wait)
                last_err = {"message": str(e)}
                continue
            data = self._parse(resp)
            if "output" in data and data["output"].get("task_id"):
                return data["output"]["task_id"], data.get("request_id", "")
            code = data.get("code", "")
            if code in THROTTLING_CODES:
                # 全抖动退避：固定间隔会让并发请求同步唤醒形成重试风暴
                wait = random.uniform(0, 2 ** attempt + 1)
                print(f"    ⚠️ 限流（{code}），退避 {wait:.1f}s 后重试（attempt {attempt + 1}/{max_retry}）")
                time.sleep(wait)
                last_err = data
                continue
            if code in MODEL_UNAVAILABLE_CODES or resp.status_code in (403, 404):
                raise ModelNotAvailableError(f"{body.get('model')}: {code} {data.get('message', '')}")
            raise RuntimeError(f"提交失败 HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:300]}")
        raise RuntimeError(f"提交失败（限流重试耗尽）: {json.dumps(last_err, ensure_ascii=False)[:300]}")

    def query_task(self, task_id):
        """查询单个任务状态。

        注意：GET /tasks/{task_id} 不能携带 X-DashScope-Async 头，否则返回
        403 AccessDenied「current user api does not support asynchronous calls」
        （官方示例的 GET 请求仅带 Authorization）。
        """
        url = self.base_url + TASK_POLL_PATH.format(task_id=task_id)
        last_err = None
        for attempt in range(3):
            try:
                resp = self.session.get(url, headers=self._headers(async_mode=False), timeout=self.timeout)
                return self._parse(resp)
            except requests.RequestException as e:
                last_err = e
                time.sleep(random.uniform(0, 2 ** attempt + 1))
        raise RuntimeError(f"任务查询网络错误（重试 3 次）: {last_err}")

    @staticmethod
    def _parse(resp):
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"非 JSON 响应 HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 401:
            raise RuntimeError("401: Key 与端点不配对（sk-ws- Key 必须配 workspace 端点）")
        return data

    @staticmethod
    def is_terminal(status_info):
        ts = status_info.get("output", {}).get("task_status", "")
        return ts in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN")

    # ---------- 业务封装 ----------
    def text2image(self, prompt, model_candidates, negative_prompt=None, size="1536*2688", n=1):
        """文生图（剧照/海报），返回 (image_url, model)。

        - qwen-image-* 系列：同步接口（/multimodal-generation/generation），响应直接含 URL
        - wan*-image 系列（降级候选）：异步 image-synthesis 路径，内部轮询到终态
        """
        for model in model_candidates:
            try:
                if model.startswith("qwen-image"):
                    return self._qwen_text2image_sync(prompt, model, size, negative_prompt, n), model
                return self._wan_text2image_async(prompt, model, negative_prompt, n), model
            except ModelNotAvailableError as e:
                print(f"    ⚠️ 模型不可用，降级: {e}")
                continue
            except ThrottledError as e:
                # 限流是配额级问题：同模型硬等窗口不划算了（RPM 打空时退避再久也可能徒劳），
                # 降级到下一候选模型继续干（额度独立），全链路不至于停在图像步
                print(f"    ⚠️ 限流降级: {e}")
                continue
        raise ModelNotAvailableError("所有图像候选模型均不可用")

    def _qwen_text2image_sync(self, prompt, model, size, negative_prompt, n):
        """qwen-image 同步文生图：单轮 messages 结构，直接返回图片 URL。"""
        params = {"size": size, "n": n}
        if negative_prompt:
            params["negative_prompt"] = negative_prompt
        body = {
            "model": model,
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": params,
        }
        last_err = None
        for attempt in range(6):  # 限流退避加长：RPM 配额耗尽需等到限流窗口回填（实测 2026-11-20 晚）
            try:
                resp = self.session.post(
                    self.base_url + QWEN_IMAGE_SYNC_PATH,
                    headers=self._headers(async_mode=False), json=body, timeout=180,
                )
            except requests.RequestException as e:
                wait = random.uniform(0, 2 ** attempt + 1)
                print(f"    ⚠️ 文生图网络错误（{type(e).__name__}），退避 {wait:.1f}s 后重试")
                time.sleep(wait)
                last_err = {"message": str(e)}
                continue
            data = self._parse(resp)
            if resp.status_code == 200:
                content = data["output"]["choices"][0]["message"]["content"]
                for c in content:
                    if c.get("image"):
                        return c["image"]
                raise RuntimeError(f"响应中未找到图片 URL: {json.dumps(data, ensure_ascii=False)[:300]}")
            code = data.get("code", "")
            if code in THROTTLING_CODES:
                # RPM 窗口级限流：指数退避拉长（最大 ~60s）；重试耗尽抛 ThrottledError
                # 交由上层降级到下一候选模型（配额独立），不停在单模型上硬等
                wait = random.uniform(0, min(2 ** attempt + 1, 60))
                print(f"    ⚠️ 限流（{code}），退避 {wait:.1f}s 后重试（attempt {attempt + 1}/6）")
                time.sleep(wait)
                last_err = data
                continue
            if code in MODEL_UNAVAILABLE_CODES or resp.status_code in (403, 404):
                raise ModelNotAvailableError(f"{model}: {code} {data.get('message', '')}")
            raise RuntimeError(f"文生图失败 HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:300]}")
        raise ThrottledError(f"文生图限流重试耗尽（{model}）: {json.dumps(last_err, ensure_ascii=False)[:150]}")

    def _wan_text2image_async(self, prompt, model, negative_prompt, n):
        """wan*-image 异步文生图（降级路径）：提交任务并轮询到终态，返回图片 URL。"""
        inp = {"prompt": prompt}
        if negative_prompt:
            inp["negative_prompt"] = negative_prompt
        task_id, _ = self._post_task({
            "_kind": "image", "model": model, "input": inp,
            "parameters": {"size": "1024*1024", "n": n},
        })
        info = self.wait_task(task_id)
        if info.get("output", {}).get("task_status") != "SUCCEEDED":
            raise RuntimeError(f"wan 文生图任务失败: {json.dumps(info.get('output', {}), ensure_ascii=False)[:200]}")
        urls = self.extract_image_urls(info)
        if not urls:
            raise RuntimeError("wan 文生图任务成功但未返回 URL")
        return urls[0]

    def image2video(self, prompt, image_url, model_candidates, resolution="480P", duration=None):
        """图生视频（首帧驱动），按候选列表降级。返回 (task_id, model)。

        输入格式按模型代际分流（实测 2026-11-20）：
        - wan3.0-video 系（All-in-One）：input.media + type=first_frame；
          否则 images 字段被静默忽略 → 退化为纯 T2V 且 duration 不生效（实测输出 2s）
        - wan2.7-i2v：input.images + type=image（老格式）
        """
        def build_input(model):
            if model.startswith("wan3.0"):
                return {
                    "prompt": prompt,
                    "media": [{"type": "first_frame", "url": image_url}],
                }
            return {
                "prompt": prompt,
                "images": [{"type": "image", "url": image_url}],
            }
        return self._submit_video(
            model_candidates, build_input, resolution=resolution, duration=duration,
        )

    def ref2video(self, prompt, ref_image_urls, model_candidates, resolution="480P", duration=None):
        """参考生视频（角色锚定）：纯 reference_image 输入驱动，保证角色一致性。

        实测约束（2026-11-20 探测）：wan3.0 的 first_frame 不能与 reference_image
        混用（InvalidParameter: first_frame cannot be combined with other media
        types except last_frame），角色一致性只能走纯 reference_image 形态；
        图像首帧构图控制与角色一致性不可兼得，由 prompt 描述构图。"""
        def build_input(model):
            media = [{"type": "reference_image", "url": u} for u in ref_image_urls]
            return {"prompt": prompt, "media": media}
        return self._submit_video(
            model_candidates, build_input, resolution=resolution, duration=duration,
        )

    def text2video(self, prompt, model_candidates, resolution="480P", duration=None):
        """文生视频，按候选列表降级。返回 (task_id, model)。"""
        return self._submit_video(
            model_candidates, lambda _m: {"prompt": prompt},
            resolution=resolution, duration=duration,
        )

    def video_edit(self, prompt, video_url, model_candidates, resolution="720P"):
        """生成式视频编辑（元素替换/运镜/特效复刻）。

        与生成接口的差异：输入是 input.media 数组（type=video / reference_image）；
        resolution 仅支持 720P/1080P（无 480P）；不接受 duration。
        注意：提交时不校验 resolution，执行时才报 InvalidParameter，
        因此必须在提交侧就过滤非法档位。
        """
        errors = []
        # 仅保留合法档位（传入 480P 等非法值会被静默受理后在执行阶段失败）
        reso_chain = [r for r in dict.fromkeys([resolution, "720P", "1080P"]) if r in ("720P", "1080P")]
        for model in model_candidates:
            for reso in reso_chain:
                try:
                    body = {
                        "_kind": "video",
                        "model": model,
                        "input": {
                            "prompt": prompt,
                            "media": [{"type": "video", "url": video_url}],
                        },
                        "parameters": {"resolution": reso},
                    }
                    task_id, _ = self._post_task(body)
                    return task_id, model
                except ModelNotAvailableError:
                    errors.append(f"{model}: 不可用")
                    break
                except RuntimeError as e:
                    msg = str(e)
                    errors.append(f"{model}@{reso}: {msg[:120]}")
                    if "InvalidParameter" in msg or "size is not match" in msg:
                        continue
                    raise
        raise ModelNotAvailableError("视频编辑提交失败: " + "; ".join(errors[-3:]))

    def _submit_video(self, model_candidates, input_builder, resolution="480P", duration=None):
        # 参数不合法时逐级放宽：480P->720P；缺省时长 -> 5s -> 2s
        reso_candidates = [resolution, "720P"]
        dur_candidates = [duration, 5, 2] if duration is None else [duration, 2, 5]
        errors = []
        for model in model_candidates:
            for reso in reso_candidates:
                for dur in {d for d in dur_candidates if d is not None}:
                    try:
                        params = {"resolution": reso}
                        if dur is not None:
                            params["duration"] = dur
                        if model.startswith("wan3.0"):
                            # wan3.0 All-in-One：adaptive 自适应输入素材比例
                            params["ratio"] = "adaptive"
                        body = {
                            "_kind": "video",
                            "model": model,
                            "input": input_builder(model),
                            "parameters": params,
                        }
                        task_id, _ = self._post_task(body)
                        return task_id, model
                    except ModelNotAvailableError:
                        errors.append(f"{model}: 不可用")
                        break  # 模型级错误，换模型
                    except RuntimeError as e:
                        msg = str(e)
                        errors.append(f"{model}@{reso}/{dur}s: {msg[:120]}")
                        if "size is not match" in msg or "InvalidParameter" in msg:
                            continue  # 参数级错误，换参数组合
                        raise
        raise ModelNotAvailableError("所有视频候选模型均不可用: " + "; ".join(errors[-3:]))

    def download(self, url, local_path, max_retry=3):
        """下载生成产物（任务结果 URL 24 小时有效，须及时保存）。网络错误退避重试。"""
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        last_err = None
        for attempt in range(max_retry):
            try:
                with self.session.get(url, stream=True, timeout=self.timeout) as r:
                    r.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(65536):
                            f.write(chunk)
                return local_path
            except requests.RequestException as e:
                last_err = e
                wait = random.uniform(0, 2 ** attempt + 1)
                print(f"    ⚠️ 下载失败（{type(e).__name__}），退避 {wait:.1f}s 后重试")
                time.sleep(wait)
        raise RuntimeError(f"下载失败（重试 {max_retry} 次）: {last_err}")

    def wait_task(self, task_id, poll_interval=10, max_wait=900, progress_cb=None):
        """阻塞等待任务终态（单任务场景用；批量场景请用 task_manager）。"""
        start = time.time()
        while True:
            info = self.query_task(task_id)
            status = info.get("output", {}).get("task_status", "UNKNOWN")
            if self.is_terminal(info):
                return info
            if progress_cb:
                progress_cb(task_id, status, time.time() - start)
            if time.time() - start > max_wait:
                raise TimeoutError(f"任务 {task_id} 超过 {max_wait}s 未完成")
            time.sleep(poll_interval)

    @staticmethod
    def extract_image_urls(task_info):
        return [r.get("url") for r in task_info.get("output", {}).get("results", []) if r.get("url")]

    @staticmethod
    def extract_video_url(task_info):
        return task_info.get("output", {}).get("video_url")

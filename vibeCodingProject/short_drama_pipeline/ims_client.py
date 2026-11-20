"""IMS（智能媒体服务，产品代码 ice）接口层：字幕擦除 + 剪辑合成。

对应配额申请第 7 项：
- IMS 字幕擦除：SubmitIProductionJob（FunctionName=VideoDetext，高质算法
  ModelId=algo-video-detext-new）/ 查询 QueryIProductionJob
- IMS 剪辑合成：SubmitMediaProducingJob（Timeline JSON）/ 查询 GetMediaProducingJob

真实调用需：pip install alibabacloud_ice20201109，且账号已开通 IMS、输出 bucket
已注册。默认走 Mock（SDP_IMS_REAL=1 开启真实调用），Mock 模拟 PENDING→RUNNING→
SUCCESS 状态机，用于演示流水线编排与任务管理器纳管。
"""
import os
import time
import threading
import uuid


class IMSClient:
    def __init__(self, region="cn-beijing", real=False):
        self.region = region
        self.real = real or os.getenv("SDP_IMS_REAL", "").strip() == "1"
        self._mock_jobs = {}
        self._lock = threading.Lock()
        if self.real:
            self._init_real_client()

    # ---------- 真实客户端（SDK 缺失或未开通时抛错，回落 mock 需显式设置） ----------
    def _init_real_client(self):
        try:
            from alibabacloud_ice20201109.client import Client
            from alibabacloud_tea_openapi import models as open_api_models
            ak = os.getenv("IMS_ACCESS_KEY_ID", "").strip()
            sk = os.getenv("IMS_ACCESS_KEY_SECRET", "").strip()
            if not ak or not sk:
                raise RuntimeError("未设置 IMS_ACCESS_KEY_ID / IMS_ACCESS_KEY_SECRET")
            cfg = open_api_models.Config(
                access_key_id=ak, access_key_secret=sk,
                endpoint=f"ice.{self.region}.aliyuncs.com",
            )
            self._sdk = Client(cfg)
            print("IMS: 真实客户端已初始化（ice endpoint）")
        except Exception as e:
            raise RuntimeError(
                f"IMS 真实模式初始化失败（{e}）。请确认：pip install alibabacloud_ice20201109，"
                f"且已开通智能媒体服务并设置 IMS_ACCESS_KEY_ID/IMS_ACCESS_KEY_SECRET；"
                f"或将 SDP_IMS_REAL 留空使用 Mock 演示模式"
            )

    # ---------- 字幕擦除 ----------
    def submit_subtitle_erase(self, media_url, output_oss_url):
        """提交字幕擦除智能生产任务，返回 job_id。"""
        if self.real:
            from alibabacloud_ice20201109 import models as ice_models
            req = ice_models.SubmitIProductionJobRequest(
                function_name="VideoDetext",
                model_id="algo-video-detext-new",
                input={"Type": "Media", "MediaURL": media_url},
                output={"Type": "Media", "OutputUrl": output_oss_url},
            )
            resp = self._sdk.submit_iproduction_job(req)
            return resp.body.job_id
        return self._mock_submit("ims_erase", media_url)

    # ---------- 剪辑合成 ----------
    def submit_produce_job(self, timeline_json):
        """提交剪辑合成任务（Timeline JSON：多片段拼接、转场、字幕轨）。返回 job_id。"""
        if self.real:
            from alibabacloud_ice20201109 import models as ice_models
            req = ice_models.SubmitMediaProducingJobRequest(
                output_media_target="oss",
                output_media_config='{"Type":"Media","OutputUrl":"' + os.getenv("IMS_OUTPUT_OSS", "") + '"}',
                timeline=timeline_json,
            )
            resp = self._sdk.submit_media_producing_job(req)
            return resp.body.job_id
        return self._mock_submit("ims_produce", timeline_json)

    # ---------- 查询（QueryIProductionJob / GetMediaProducingJob） ----------
    def query_job(self, job_id, kind):
        if self.real:
            from alibabacloud_ice20201109 import models as ice_models
            if kind == "ims_erase":
                resp = self._sdk.query_iproduction_job(
                    ice_models.QueryIProductionJobRequest(job_id=job_id))
                return resp.body.status, {"raw": resp.body.to_map()}
            resp = self._sdk.get_media_producing_job(
                ice_models.GetMediaProducingJobRequest(job_id=job_id))
            return resp.body.media_producing_job.status, {"raw": resp.body.to_map()}
        return self._mock_query(job_id)

    # ---------- Mock 实现 ----------
    def _mock_submit(self, kind, payload):
        job_id = f"mock-{kind}-{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._mock_jobs[job_id] = {
                "kind": kind, "payload": str(payload)[:80],
                "state": "PENDING", "t0": time.time(),
                "stages": [("PENDING", 2), ("RUNNING", 6), ("SUCCESS", 0)],
            }
        mode = "真实" if self.real else "MOCK"
        print(f"    [IMS-{mode}] 已提交 {kind} 任务 {job_id}")
        return job_id

    def _mock_query(self, job_id):
        with self._lock:
            job = self._mock_jobs.get(job_id)
            if not job:
                return "UNKNOWN", {}
            elapsed = time.time() - job["t0"]
            state = job["stages"][0][0]
            for st_name, st_dur in job["stages"]:
                if elapsed >= st_dur:
                    state = st_name
                    elapsed -= st_dur
                else:
                    break
            job["state"] = state if state != "SUCCESS" else "SUCCESS"
        return job["state"], {"mock": True, "kind": job["kind"]}

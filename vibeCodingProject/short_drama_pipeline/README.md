# 短剧批量生产流水线 Demo（北京节点）

面向短剧制作业务的端到端演示项目：剧本分镜 → 剧照/海报生成 → 质量验收 → 图生视频 → 生成式视频编辑 → IMS 字幕擦除/剪辑合成，全部异步任务统一纳管批量轮询。

**节点**：阿里云百炼 北京（cn-beijing），workspace 专属端点（`{WorkspaceId}.cn-beijing.maas.aliyuncs.com`）。

## 模型与接口可用性（2026-11-20 实测）

| 模型 | 用途 | 接口 | 北京节点状态 |
|------|------|------|------|
| qwen4-max | 剧本/分镜结构化生成 + 多模态质量验收 | OpenAI 兼容 `/compatible-mode/v1/chat/completions` | ✅ 可用 |
| qwen-image-3.0-pro | 海报/剧照文生图 | **同步** `/api/v1/services/aigc/multimodal-generation/generation` | ✅ 可用 |
| wan3.0-video-prime（默认）/ wan3.0-video | 图生视频（剧照首帧驱动） | 异步 `/api/v1/services/aigc/video-generation/video-synthesis` | ✅ 实测出片（prime 为官方「高速版」，480P/5s 约 45-90s 完成；首帧用 `input.media` type=first_frame） |
| wan2.7-i2v / wan2.7-t2v | 降级候选 | 同上 | ✅ 均可提交 |
| wan2.7-videoedit | 生成式编辑（元素替换/运镜/特效复刻） | 同上，但输入用 `input.media` 数组 | ✅ 实测出片（720P，141 秒） |
| IMS VideoDetext（algo-video-detext-new） | 字幕擦除 | `SubmitIProductionJob` / `QueryIProductionJob` | Mock（SDK：`alibabacloud_ice20201109`，真实模式需开通 IMS） |
| IMS MediaProducing | 剧集剪辑合成 | `SubmitMediaProducingJob` / `GetMediaProducingJob` | Mock（同上） |

> 注：配额申请中 wan3.0-video 申请地域为新加坡（ap-southeast-1），本 demo 在北京节点验证同样可调用，两地可用性结论可供答复客户参考。

### 实测数据（run_001_20261120_113905 + 对照实验）

- 剧本分镜：qwen4-max 生成「王者归来」分镜 JSON，结构完整（含海报/剧照/视频/编辑四套 prompt）
- 质量验收：qwen4-max 多模态对剧照打分 4/10，准确指出 7 处与分镜的叙事偏差（缺协议书/酒杯等）——验收能力真实可用
- 图生视频（wan3.0-video 系）：首帧必须用 `input.media` + `type: "first_frame"`；错误传 wan2.7 式 `input.images` 会被**静默忽略**退化成纯 T2V（判据：竖版剧照输出 16:9 横版）
- duration 参数：正常生效（dur=10 → 10s，dur=5 → 5s，dur=-1 智能时长 → 9s）；曾两次偶发输出 2s（正确参数下复测不重现，服务端偶发，遇 2s 输出重提任务即可）
- **时长决策（双层）**：分镜阶段 qwen4-max 按剧情动作量推荐每场 `video_duration`（反应特写 2-3s / 完整动作 5-8s / 多人物长镜头 8-12s，实测两场给出 8s/10s）；推荐缺失时传 `duration: -1` 交由服务端智能时长模式（模型按 prompt/内容自动推荐）
- 生成式编辑：wan2.7-videoedit 720P 编辑 141s 完成
- prime vs 标准版：prime 为官方「高速版，能力对齐标准版，端到端速度显著提升」（非高画质档），480P/5s 出片 45s、480P/10s 出片 61s；价格略高（国际站列表价 480P $0.068/s vs $0.05/s）
- 状态查询压测：**单线程串行可持续 ~16 QPS、零限流**（瓶颈是单请求 RTT ~60ms，非配额）；客户 500 QPS 需多线程并发 + 工单扩配，且需确认三类查询接口（百炼 tasks / IMS QueryIProductionJob / GetMediaProducingJob）是否共池
- **Web 界面 E2E 实测**（run_006_20261120_155110，纯 SSE 驱动）：分镜→海报/剧照→多模态验收→wan3.0-video-prime 图生视频→wan2.7-videoedit 编辑成片全部完成，图片/视频/报告均以 asset 事件流式推送到页面；视频生成本次排队较久（约 28 分钟才 SUCCEEDED，出片 6.6MB 长时长片段），建议产线场景按 20-12s 时长与排队波动预留等待窗口

## 关键技术要点

1. **qwen-image 与 wan*-image 接口不同**：qwen-image 系列走同步 `multimodal-generation/generation`（`input.messages` 单轮结构、响应直接含图片 URL），不能打到异步 `image-synthesis` 路径（否则报 `InvalidParameter: url error`）。本项目的 [bailian_client.py](bailian_client.py) 已按模型名自动分流。
2. **任务查询 GET 不能带 `X-DashScope-Async` 头**：否则返回 403 `AccessDenied: current user api does not support asynchronous calls`，且响应里无 `task_status`，极易误判为任务异常。官方示例 GET 仅带 Authorization。
3. **wan3.0-video 系首帧输入用 `input.media` + `type: "first_frame"`**，与 wan2.7-I2V 的 `input.images` 不兼容；错传会被静默忽略退化成纯 T2V（竖版剧照输出 16:9 横版即是此症状）。`ratio: "adaptive"` 可自适应首帧比例。客户端已按模型代际自动分流。
4. **wan2.7-videoedit 输入用 `input.media` 数组**（`{type: video|reference_image, url}`），不是 `video_url`；resolution 仅支持 720P/1080P，且**提交时不校验、执行时才报 InvalidParameter**——必须在提交侧过滤非法档位，否则降级重试链不生效。
5. **qwen4-max 为思考模型**：`max_tokens` 含思考额度；结构化 JSON 生成场景传 `enable_thinking: false`（不兼容时自动去除重试）。
6. **Key 与端点成对**：`sk-ws-` 前缀 workspace Key 必须配 workspace 端点，错配返回 401/403。凭证从仓库根 `.env` 读取（`DASHSCOPE_API_KEY_CN_TEST` + `DASHSCOPE_API_KEY_CN_URL`），禁止硬编码。
7. **异步任务统一管理**：[task_manager.py](task_manager.py) 实现自适应爬坡限速（遇 `Throttling`/BurstRate 全抖动退避），对应客户「任务状态查询 ≥500 QPS」诉求提供 `--pressure` 压测模式，实测当前 workspace 可持续查询 QPS 与限流触发点。
8. **长流水线的网络韧性（Web 界面实测补强）**：①所有 HTTP 调用（提交/查询/下载/LLM）均带全抖动退避重试——长流水线跑几十分钟，任何一次网络抖动都会整条失败；②qwen4-max 多模态验收前将 1728*2368 原图（~5MB）降采样到 ≤1024px JPEG（~220KB），否则 base64 单请求体约 6.4MB，长距链路频繁 write timeout；③任务终态集合必须同时包含百炼的 `SUCCEEDED` 与 IMS 的 `SUCCESS`，漏写会让 IMS 任务永不算完成、轮询被迫跑满 max_wait。
9. **断点续传（checkpoint）**：[pipeline.py](pipeline.py) 每步完成后把关键产物写入 run 目录的 `checkpoint.json`（分镜、图片 URL、验收结果、已提交的异步任务 task_id，原子写防损坏）。网络中断等异常后传入 `resume_dir` 复用同一 run 目录：已完成的步骤直接跳过、复用已落盘的分镜与图片产物；已提交的异步任务在服务端仍在跑，凭 task_id 重新登记轮询即可，**不重复提交、不重复计费**。恢复时以 checkpoint 内的主题/场数为准。验收：`scripts/test_checkpoint_resume.py`（全程 mock，不调真实模型）。

## 目录结构

```
short_drama_pipeline/
├── config.py           # 凭证/端点/模型候选（含降级链）
├── llm_client.py       # qwen4-max：分镜生成 + 多模态质量验收
├── bailian_client.py   # 百炼异步任务客户端（图像/视频/编辑，限流退避+模型降级）
├── ims_client.py       # IMS 字幕擦除 + 剪辑合成（Mock/真实 SDK 双模式）
├── task_manager.py     # 批量任务轮询 + 自适应限速 + QPS 压测
├── pipeline.py         # 流水线编排
├── run_demo.py         # CLI 入口
├── server.py           # Web 服务（FastAPI + SSE，前端风格对齐 Alibaba_presale_agent）
├── static/
│   ├── index.html      # 页面（暖白底 + 品牌橙，与 presale_agent 同一视觉口径）
│   ├── style.css
│   └── app.js          # 原生 JS，SSE 消费 /api/run 流式事件
├── scripts/
│   ├── probe_models.py # 模型可用性探测（供售前答复口径使用）
│   └── exp_*.py        # wan3.0 时长/首帧格式对照实验
└── output/             # 运行产物（git 忽略，全部文件不进仓库）
```

## 两种使用方式

### Web 界面（推荐）

```bash
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 7861
# 浏览器打开 http://127.0.0.1:7861
```

- 输入短剧主题/场景数 → 点「开始生产」，SSE 实时推送运行日志，海报/剧照/视频边生成边出现
- **打磨模式（默认开启）**：剧本分镜 → 海报剧照 → 质量验收 → 图生视频四个步骤后暂停，界面弹确认卡（预览产物）等你人工确认：
  - ✅ 确认继续 · 🔁 重新生成本步（图生视频已计费，不提供重做） · ⛔ 终止（保留进度，可续跑）
  - 分镜确认点可直接在页面编辑分镜 JSON（改剧名/台词/时长建议），确认后按新分镜走后续生成
  - 已确认过的步骤记入 checkpoint（confirmed_gates），刷新页面/断网后续跑不再重复弹卡，直接停在下一个未确认的步骤
  - 勾掉「打磨模式」复选框则恢复全自动一次跑到底；关闭页面/断网时确认点自动视为终止，不锁死后续生产
- 左侧阶段列表随日志自动点亮（分镜→图像→验收→视频→编辑→IMS）
- **断点续跑**：运行失败后（如 qwen4-max 网络重试耗尽）界面自动出现「♻️ 续跑」按钮，从最新未完成 run 的 checkpoint 继续；跑完的 run 不可再续
- **历史执行记录**：页面加载即列出全部 run 目录（时间倒序，含剧名/产物计数/完成状态），点「回看产物」可在画廊中重新查看该次的海报/剧照/视频/报告；未完成的 run（有 checkpoint 且未标记 finished）额外显示「♻️ 续跑」按钮，可从指定 run 断点继续（不重复计费）
- 接口：`GET /api/health`（含可续跑探测）、`GET /api/runs`（历史记录）、`POST /api/run`（SSE，`resume: true` 断点续跑、`manual: true` 打磨模式）、`POST /api/run/confirm`（人工确认：action=continue/redo/abort，分镜可带编辑后的 storyboard JSON）、`GET /files/*`（产物）。状态查询压测已从界面移除，仅保留 CLI：`run_demo.py --pressure`

### CLI

```bash
# 1) 探测各模型在北京节点的可用性
.venv/bin/python scripts/probe_models.py

# 2) 跑完整流水线（1 场景：分镜→海报→剧照→验收→图生视频→生成式编辑→IMS）
.venv/bin/python run_demo.py

# 3) 附加 30 秒任务状态查询压测（验证 500 QPS 申请的当前水位）
.venv/bin/python run_demo.py --pressure 30 --qps 50

# 多场景 / 换题材
.venv/bin/python run_demo.py --theme "古装甜宠复仇" --scenes 2

# 打磨模式（CLI 版人工确认）：分镜/图像/验收/视频每步暂停，回车=继续 e=改完分镜后继续 r=重做本步 n=终止
.venv/bin/python run_demo.py --manual

# 断点续跑：从最新未完成 run 的 checkpoint 继续（已完成步骤跳过、已提交任务复用 task_id）
.venv/bin/python run_demo.py --resume

# 断点续传逻辑单测（全程 mock，不调真实模型）
.venv/bin/python -u scripts/test_checkpoint_resume.py

# 打磨模式全链路冒烟（真实调用：分镜编辑→图像确认点终止，验证 HITL + 可续跑）
.venv/bin/python scripts/smoke_manual_gate.py
```

## 与客户配额申请的对应关系

| 客户申请项 | demo 对应 |
|------|------|
| qwen4-max：资料整理、检索、图像理解及质量验收 | 分镜 JSON 生成 + 剧照多模态验收（含流式/多模态形态验证） |
| qwen-image-3.0-pro：剧照、海报、Banner | `text2image`（9:16 海报 1536*2688、3:4 剧照 1728*2368） |
| wan3.0-video / prime：文生/图生/参考生视频 | 剧照首帧驱动图生视频（480P/720P，2-5s） |
| wan2.7-videoedit：元素替换、运镜及特效复刻 | 对成片执行 `edit_instruction` 生成式编辑 |
| IMS QueryIProductionJob / GetMediaProducingJob ≥500 QPS | IMS 层接口封装 + TaskManager 统一轮询、`--pressure` 压测 |
| 回调/批量查询 | 当前百炼任务查询为拉模式（`GET /api/v1/tasks/{id}`，task_id 有效 24h）；IMS 支持 StatusURL 回调，真实模式已预留 |

## 环境变量

从仓库根 `.env` 读取（已存在，无需新增）：

- `DASHSCOPE_API_KEY_CN_TEST`：北京节点 workspace 按量 Key
- `DASHSCOPE_API_KEY_CN_URL`：配套 workspace compatible-mode 端点

可选（通过环境变量传入，不写入仓库）：

- `SDP_LLM_MODEL` / `SDP_IMAGE_MODEL` / `SDP_VIDEO_MODEL`：覆盖默认模型
- `SDP_IMS_REAL=1` + `IMS_ACCESS_KEY_ID` / `IMS_ACCESS_KEY_SECRET` / `IMS_OUTPUT_OSS`：开启 IMS 真实调用（需开通智能媒体服务、安装 `alibabacloud_ice20201109`）

## 运行产物

每次运行生成 `output/run_NNN_YYYYMMDD_HHMMSS/`（NNN 为递增序号，按名字排序即时间顺序，一眼可辨是第几次生产；删除旧 run 后序号重新从 001 计）：storyboard.json、poster.png、scene\*_still.png、qa_results.json、scene\*_raw.mp4、scene\*_edited.mp4、report.json，以及断点续传用的 checkpoint.json（完成时标记 finished，之后不再可续跑）。生成结果 URL 有效期 24 小时，脚本会及时下载到本地。`output/` 下所有文件已在 .gitignore 中全部忽略。

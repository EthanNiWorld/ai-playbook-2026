"""
Model Salebook Agent — Gradio Web UI 入口
==========================================

自由对话式 Chat 界面：BD/SA 像和真人销售顾问聊天一样，
Agent 自动从对话中提取信息，生成定制化 HTML Salebook。

使用:
    python web.py
    # 浏览器打开 http://localhost:7860
"""

import re
import sys
import uuid
import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

import gradio as gr
from langgraph.types import Command
from graph import build_graph
from config import MODEL_OPTIONS, DEFAULT_MODEL, set_runtime_model, get_log_path


# 常见模型名识别 regex（首条消息拆解 target_model）
MODEL_NAME_RE = re.compile(
    r"(qwen[\d.]+-(?:max|plus|flash)(?:-preview)?"
    r"|wan[\d.]+"
    r"|deepseek-v[\d.]+(?:-pro|-flash)?"
    r"|claude-(?:opus|sonnet|haiku)-?[\d.]*"
    r"|gpt-[\d.]+(?:-mini|-nano)?"
    r"|gemini-[\d.]+"
    r"|kimi-k[\d.]+"
    r"|glm-[\d.]+)",
    re.IGNORECASE,
)


def parse_first_message(text: str) -> tuple[str, str]:
    """从首条消息拆出 target_model + user_brief。

    例：
        "Qwen3.7-Plus 德勤推 max 还是 plus" → ("Qwen3.7-Plus", "德勤推 max 还是 plus")
        "Wan2.7" → ("Wan2.7", "")
        "德勤推 qwen3.7-max 好吗" → ("qwen3.7-max", "德勤推  好吗")
    """
    text = text.strip()
    m = MODEL_NAME_RE.search(text)
    if m:
        target = m.group(0)
        # 去掉模型名后剩下的作为 brief
        brief = (text[:m.start()] + " " + text[m.end():]).strip()
        return target, brief
    # 未识别到模型名：整个当 brief，返回原文作为 target_model（供下游提示）
    return text, ""


# 全局 graph 实例
graph = build_graph()

# 会话状态存储
sessions: dict = {}

# 不记录进日志的中间态回复前缀
_TRANSIENT_PREFIXES = ("🔍 加载", "（请输入内容）")


def _log_turn(session_id: str, user_msg: str, agent_reply: str, llm_model: str) -> None:
    """将一轮对话追加到 output/log/{session_id}.md。
    跳过中间态提示（加载中/请输入）。
    """
    if not user_msg or not agent_reply:
        return
    if any(agent_reply.startswith(p) for p in _TRANSIENT_PREFIXES):
        return
    log_file = get_log_path() / f"{session_id}.md"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not log_file.exists():
        header = (
            f"# Session `{session_id}`\n\n"
            f"- Started: {now}\n"
            f"- LLM: {llm_model}\n\n---\n\n"
        )
        log_file.write_text(header, encoding="utf-8")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"## 👤 User · {now}\n\n{user_msg}\n\n")
        f.write(f"## 🤖 Agent · {now}\n\n{agent_reply}\n\n---\n\n")


def get_session(session_id: str):
    """获取或创建会话配置"""
    if session_id not in sessions:
        sessions[session_id] = {
            "config": {"configurable": {"thread_id": session_id}},
            "started": False,
            "finished": False,
            "output_path": None,
        }
    return sessions[session_id]


def chat_fn(message: str, history: list, session_id: str, llm_choice: str):
    """
    Gradio chat 回调。
    首条消息 = 目标模型名，启动 graph；
    后续消息 = interrupt resume 值，驱动 LLM 对话。
    每轮调用都会以 dropdown 当前选择覆盖底层 LLM。
    会话结束后将本轮输入 + 最后一条回复追加到 output/log/{session_id}.md。
    """
    # 每轮同步一次 LLM 选择（允许会话中途切换）
    if llm_choice:
        set_runtime_model(llm_choice)

    session = get_session(session_id)
    config = session["config"]
    last_reply: str | None = None

    try:
        if session["finished"]:
            last_reply = "✅ 当前会话已完成。请点击 **🔄 新建会话** 开始下一轮。"
            yield last_reply
            return

        if not message or not message.strip():
            yield "（请输入内容）"
            return

        try:
            if not session["started"]:
                # 首条消息：拆解 target_model + user_brief
                session["started"] = True
                target_model, user_brief = parse_first_message(message)
                last_reply = f"🔍 加载 **{target_model}** 知识，基于已有描述出初稿中..."
                yield last_reply
                init_state = {"target_model": target_model}
                if user_brief:
                    init_state["user_brief"] = user_brief
                result = graph.invoke(init_state, config=config)
            else:
                result = graph.invoke(Command(resume=message.strip()), config=config)

            # 检查是否有 interrupt（需要用户回答）
            if isinstance(result, dict) and "__interrupt__" in result:
                interrupts = result["__interrupt__"]
                if interrupts:
                    info = interrupts[0].value
                    question = info.get("question", "请继续...")
                    summary = info.get("summary", "")
                    response = f"{summary}\n\n{question}" if summary else question
                    last_reply = response
                    yield response
                    return

            # 没有 interrupt = 整个流程完成
            session["finished"] = True
            output_path = result.get("output_path", "") if isinstance(result, dict) else ""
            strategy = result.get("strategy_type", "") if isinstance(result, dict) else ""
            session["output_path"] = output_path

            strategy_label = {
                "tech_advantage": "技术碾压（数据说话）",
                "price_value": "性价比（同等能力更低成本）",
                "trojan_horse": "田忌赛马（先做进去等升级）",
            }.get(strategy, strategy)

            last_reply = f"""✅ **Salebook 生成完成！**

🎯 **采用策略**：{strategy_label}
📄 **文件路径**：`{output_path}`

请点击右下方 **📥 下载 Salebook HTML** 按钮获取文件。"""
            yield last_reply

        except Exception as e:
            import traceback
            traceback.print_exc()
            last_reply = f"❌ 出错了：{str(e)}\n\n点击 **🔄 新建会话** 重试。"
            yield last_reply
    finally:
        if last_reply and message and message.strip():
            _log_turn(session_id, message.strip(), last_reply, llm_choice or DEFAULT_MODEL)


def download_fn(session_id: str):
    """返回生成的 HTML 文件路径供下载"""
    session = get_session(session_id)
    path = session.get("output_path")
    if path:
        return path
    return None


def new_session():
    """创建新会话"""
    new_id = str(uuid.uuid4())[:8]
    return new_id, [], gr.update(value=None)


# 自定义样式：渐变 Hero / 卡片侧栏 / 气泡化聊天
CSS = """
.gradio-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
}
footer {display: none !important;}

/* Hero 区 */
#hero-banner {
    background: linear-gradient(135deg, #FF6A00 0%, #EE0979 60%, #6A11CB 100%);
    border-radius: 18px;
    padding: 28px 36px;
    margin: 16px 0 20px 0;
    color: #fff !important;
    box-shadow: 0 8px 24px rgba(255, 106, 0, 0.18);
}
#hero-banner h1 {
    margin: 0 0 6px 0;
    font-size: 28px;
    font-weight: 800;
    color: #fff;
}
#hero-banner p {
    margin: 0;
    font-size: 14px;
    opacity: 0.92;
    color: #fff;
}
#hero-banner code {
    background: rgba(255,255,255,0.18);
    padding: 1px 8px;
    border-radius: 6px;
    font-size: 12px;
}

/* 侧栏卡片 */
.side-card {
    background: #FAFBFC;
    border: 1px solid #EDEFF3;
    border-radius: 14px;
    padding: 14px 16px !important;
    margin-bottom: 12px;
}
.side-card h4 {
    font-size: 13px;
    font-weight: 700;
    margin: 0 0 8px 0;
    color: #4B5563;
    letter-spacing: 0.3px;
}
.side-card .markdown-text {
    font-size: 12px;
    color: #6B7280;
    line-height: 1.55;
}

/* 底部操作区 */
.action-row {
    margin-top: 8px !important;
}
.action-row .gr-button {
    border-radius: 10px !important;
    font-weight: 600;
}

/* Chatbot 美化 */
.chatbot, .chatbot * {border-radius: 0;}
.chatbot {
    border: 1px solid #EDEFF3 !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    background: #fff !important;
}
.chatbot .message {
    border-radius: 12px !important;
    padding: 10px 14px !important;
}
.chatbot .user {
    background: linear-gradient(135deg, #FF6A00, #EE0979) !important;
    color: #fff !important;
}
.chatbot .bot {
    background: #F5F6F8 !important;
    color: #1F2937 !important;
}
.chatbot pre {
    border-radius: 8px !important;
    background: #1A1F2E !important;
    color: #E8EAED !important;
}
.chatbot table {
    border-collapse: collapse;
    margin: 8px 0;
}
.chatbot table th, .chatbot table td {
    border: 1px solid #E5E7EB;
    padding: 6px 10px;
    font-size: 13px;
}
.chatbot table th {
    background: #F9FAFB;
    font-weight: 600;
}

/* Textbox 输入区 */
.gr-textbox textarea, .gr-textbox input {
    border-radius: 12px !important;
    border: 1px solid #DDE1E7 !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
}
.gr-textbox textarea:focus, .gr-textbox input:focus {
    border-color: #FF6A00 !important;
    box-shadow: 0 0 0 3px rgba(255,106,0,0.12) !important;
}

/* Dropdown */
.gr-dropdown {
    border-radius: 10px !important;
}

/* Examples 区 */
.gr-examples {
    border-radius: 12px !important;
    background: transparent !important;
}
.gr-examples table tr td {
    background: #FFF7F0 !important;
    border: 1px solid #FFE4D1 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 13px !important;
    color: #7C2D12 !important;
    transition: all 0.2s;
}
.gr-examples table tr td:hover {
    background: #FFEBD9 !important;
    transform: translateY(-1px);
}

/* 打包下载文件卡片 */
.gr-file {
    border-radius: 12px !important;
    border: 1px dashed #DDE1E7 !important;
}

/* 隐藏 Gradio 默认 padding */
.contain {padding: 0 !important;}
"""

with gr.Blocks(title="Model Salebook Agent") as demo:
    # ─── Hero 渐变区 ───
    gr.HTML("""
<div id="hero-banner">
    <h1>🎯 Model Salebook Agent</h1>
    <p>一句话说明目标模型 + 客户背景，5 秒出一份可调整的销售策略简报 · 定制 HTML Salebook</p>
    <p style="margin-top:6px;font-size:12px;">示例：<code>Qwen3.7-Plus 德勤考虑从 3.6-Plus 升级，纠结是上 Max 还是 Plus</code></p>
</div>
    """)

    session_state = gr.State(lambda: str(uuid.uuid4())[:8])

    with gr.Row(equal_height=False):
        # ─── 左侧控制区 ───
        with gr.Column(scale=1, min_width=260):
            with gr.Group(elem_classes=["side-card"]):
                gr.Markdown("#### 🧠 底层 LLM")
                llm_choice = gr.Dropdown(
                    choices=MODEL_OPTIONS,
                    value=DEFAULT_MODEL,
                    label="",
                    show_label=False,
                    interactive=True,
                    container=False,
                )
                gr.Markdown(
                    "默认 **qwen3.7-max**（能力顶到）。策略推断质量与模型能力成正比。",
                    elem_classes=["markdown-text"],
                )

            with gr.Group(elem_classes=["side-card"]):
                gr.Markdown("#### ⚡ 快速启动")
                gr.Markdown(
                    "- 一句话描述**目标模型 + 客户背景**\n"
                    "- 5 秒出初稿策略简报\n"
                    "- 随时补充信息 → 增量重写\n"
                    "- 输 `y` / `生成` → 出 HTML Salebook",
                    elem_classes=["markdown-text"],
                )

            with gr.Group(elem_classes=["side-card"]):
                gr.Markdown("#### 📁 会话操作")
                with gr.Column(elem_classes=["action-row"]):
                    new_btn = gr.Button("🔄 新建会话", variant="secondary", size="sm")
                    download_btn = gr.Button("📥 下载 Salebook", variant="primary", size="sm")
                file_output = gr.File(label="生成的文件", file_count="single")

        # ─── 右侧聊天主区 ───
        with gr.Column(scale=3, min_width=560):
            chatbot = gr.ChatInterface(
                fn=chat_fn,
                additional_inputs=[session_state, llm_choice],
                chatbot=gr.Chatbot(
                    height=620,
                    elem_classes=["chatbot"],
                    placeholder=(
                        "<div style='text-align:center;padding:40px 20px;color:#9CA3AF;'>"
                        "<div style='font-size:32px;margin-bottom:12px;'>👋</div>"
                        "<h3 style='margin:0 0 8px 0;color:#4B5563;'>一句话描述你的场景</h3>"
                        "<p style='font-size:13px;margin:0;'>例如：<br>"
                        "<code style='background:#FFF7F0;padding:4px 10px;border-radius:6px;color:#7C2D12;'>"
                        "Qwen3.7-Plus 德勤从 3.6-Plus 升级，纠结上 Max 还是 Plus</code></p>"
                        "</div>"
                    ),
                ),
                textbox=gr.Textbox(
                    placeholder="一句话启动会话；后续补充信息或输 'y' 生成...",
                    lines=1,
                ),
                examples=[
                    ["Qwen3.7-Max 德勤 AI Coding 场景，从 Claude Opus 抢回"],
                    ["Qwen3.7-Plus 德勤从 3.6-Plus 升级，纠结上 Max 还是 Plus"],
                    ["Wan2.7 短剧制作公司选型"],
                    ["DeepSeek-V4-Pro 金融客户 RAG 场景，预算极敏感"],
                ],
            )

    download_btn.click(fn=download_fn, inputs=[session_state], outputs=[file_output])
    new_btn.click(
        fn=new_session,
        outputs=[session_state, chatbot.chatbot, file_output],
    )


if __name__ == "__main__":
    demo.launch(
        server_port=7860,
        share=False,
        inbrowser=True,
        css=CSS,
        theme=gr.themes.Soft(
            primary_hue="orange",
            secondary_hue="slate",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        ),
    )

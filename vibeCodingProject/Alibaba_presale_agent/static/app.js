/* 阿里小可爱AI问答助手 — 前端逻辑：SSE 流式聊天 + 👍/👎 反馈 */
"use strict";

const chatEl = document.getElementById("chat");
const statusBar = document.getElementById("statusBar");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const stopBtn = document.getElementById("stop");
const inputHint = document.getElementById("inputHint");
const queueBar = document.getElementById("queueBar");
const newBtn = document.getElementById("newSession");
const newTopBtn = document.getElementById("newSessionTop");
const workspaceEl = document.getElementById("workspace");
const suggestionsEl = document.getElementById("suggestions");
const sidebarToggle = document.getElementById("sidebarToggle");
const layoutEl = document.querySelector(".layout");
const desktopQuery = window.matchMedia("(min-width: 821px)");

let busy = false;
let history = []; // [{role, content}] 供多轮上下文
let queue = []; // 待发送问题（串行：当前回答结束后依次自动发送）
let controller = null; // 当前流的 AbortController，供「停止」中断
const MAX_QUEUE = 3; // 排队上限，避免无限堆叠
const REASONS = ["价格不对/过期", "内容过时", "答非所问", "来源不可信", "其他"];

/* ── 工具函数 ── */

function sessionId() {
  let sid = localStorage.getItem("apa_session");
  if (!sid) {
    sid = (crypto.randomUUID ? crypto.randomUUID() : "s" + Date.now()).slice(0, 12);
    localStorage.setItem("apa_session", sid);
  }
  return sid;
}

function renderMd(text) {
  if (window.marked) {
    const html = marked.parse(text, { breaks: true });
    // 轻量防护：移除脚本/事件属性/javascript: 协议链接
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
      .replace(/(href|src)\s*=\s*("|')\s*javascript:[^"]*\2/gi, '$1="#"');
  }
  // marked 加载失败时的兑底：纯文本
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML.replace(/\n/g, "<br>");
}

function scrollBottom() {
  chatEl.scrollTop = chatEl.scrollHeight;
}

/* ── 布局与按钮状态 ── */

function setEmptyState(empty) {
  chatEl.classList.toggle("is-empty", empty);
  workspaceEl.classList.toggle("is-empty", empty);
  suggestionsEl.hidden = !empty;
}

function syncButtons() {
  const canReset = !busy && !!chatEl.querySelector(".msg.user");
  newBtn.disabled = !canReset;
  newTopBtn.disabled = !canReset;
  // 生成中：发送按钮换成「停止」，输入框仍可用（回车入队）
  sendBtn.hidden = busy;
  sendBtn.disabled = busy || !inputEl.value.trim();
  stopBtn.hidden = !busy;
  inputHint.innerHTML = busy
    ? "Enter 加入排队<span> · 当前回答结束后依次发送</span>"
    : "Enter 发送<span> · Shift + Enter 换行</span>";
  chatEl.setAttribute("aria-busy", String(busy));
}

/* ── 排队（串行）── */

function renderQueue() {
  queueBar.innerHTML = "";
  if (!queue.length) {
    queueBar.hidden = true;
    return;
  }
  const head = queue[0].length > 30 ? queue[0].slice(0, 30) + "…" : queue[0];
  const text = document.createElement("span");
  text.className = "queue-text";
  text.textContent = "⏳ 已排队 " + queue.length + " 条 · 下一条：" + head;
  const clearBtn = document.createElement("button");
  clearBtn.type = "button";
  clearBtn.className = "queue-clear";
  clearBtn.textContent = "清空";
  clearBtn.addEventListener("click", () => {
    queue = [];
    renderQueue();
    syncButtons();
  });
  queueBar.appendChild(text);
  queueBar.appendChild(clearBtn);
  queueBar.hidden = false;
}

// 当前回答结束后取队首发送（串行，始终只有一条流在跑）
function drainQueue() {
  if (busy || !queue.length) return;
  const next = queue.shift();
  renderQueue();
  ask(next);
}

function syncSidebar() {
  const expanded = desktopQuery.matches && !layoutEl.classList.contains("sidebar-collapsed");
  sidebarToggle.setAttribute("aria-expanded", String(expanded));
  sidebarToggle.setAttribute("aria-label", expanded ? "收起侧边栏" : "展开侧边栏");
  sidebarToggle.title = expanded ? "收起侧边栏" : "展开侧边栏";
}

/* ── 消息渲染 ── */

function addUserMsg(text) {
  const div = document.createElement("div");
  div.className = "msg user";
  div.innerHTML =
    '<div class="avatar">👤</div>' +
    '<div class="bubble-wrap"><div class="bubble"></div></div>';
  div.querySelector(".bubble").textContent = text;
  chatEl.appendChild(div);
  scrollBottom();
}

function addBotMsg() {
  const div = document.createElement("div");
  div.className = "msg bot";
  div.innerHTML =
    '<div class="avatar">🤖</div>' +
    '<div class="bubble-wrap">' +
    '  <div class="sources" hidden></div>' +
    '  <details class="think" hidden>' +
    '    <summary><span class="think-title">思考中</span><span class="think-meta"></span></summary>' +
    '    <div class="think-body"></div>' +
    "  </details>" +
    '  <div class="bubble"><span class="cursor">▍</span></div>' +
    '  <div class="feedback" hidden></div>' +
    '  <div class="fb-panel" hidden></div>' +
    "</div>";
  chatEl.appendChild(div);
  scrollBottom();
  const ui = {
    root: div,
    bubble: div.querySelector(".bubble"),
    sources: div.querySelector(".sources"),
    think: div.querySelector(".think"),
    thinkBody: div.querySelector(".think-body"),
    thinkTitle: div.querySelector(".think-title"),
    thinkMeta: div.querySelector(".think-meta"),
    feedback: div.querySelector(".feedback"),
    fbPanel: div.querySelector(".fb-panel"),
  };
  // 手动展开/收起时同步 meta 文案（思考未结束时 dataset.secs 为空，不介入）
  ui.think.addEventListener("toggle", () => {
    const secs = ui.think.dataset.secs;
    if (!secs) return;
    ui.thinkMeta.textContent = ui.think.open
      ? " · " + secs + "s（点击收起）"
      : " · " + secs + "s（已收起，点击展开）";
  });
  return ui;
}

function showStatus(msg) {
  statusBar.hidden = false;
  statusBar.innerHTML = '<span class="dot"></span>' + msg;
}

function hideStatus() {
  statusBar.hidden = true;
  statusBar.innerHTML = "";
}

/* ── 来源与价格徽章 ── */

function renderSources(el, sources, priceStatus, priceAudit) {
  el.innerHTML = "";
  if (priceStatus === "official") {
    const badge = document.createElement("span");
    if (priceAudit && priceAudit.indexOf("mismatch") === 0) {
      // 输出侧审计发现回答表格价格与官方证据不符：撤掉「已核实」绿标，改警示。
      badge.className = "price-badge price-badge-warn";
      badge.textContent = "⚠️ 价格未通过自动核对，请以官方定价页为准";
    } else {
      badge.className = "price-badge";
      badge.textContent = "✅ 价格已联网核实（官方定价页）";
    }
    el.appendChild(badge);
  }
  for (const s of sources || []) {
    if (!s.url) continue;
    const a = document.createElement("a");
    a.className = "source-chip " + (s.kind || "knowledge");
    a.href = s.url;
    a.target = "_blank";
    a.rel = "noopener";
    a.title = s.url;
    const icon =
      s.kind === "official" ? "🏛" : s.kind === "web" ? "🌐" : "📄";
    a.textContent = icon + " " + (s.title || s.url);
    el.appendChild(a);
  }
  if (el.children.length > 0) el.hidden = false;
}

/* ── 反馈 ── */

function setupFeedback(feedbackEl, panelEl, answerId) {
  feedbackEl.hidden = false;
  feedbackEl.innerHTML =
    '<span class="fb-note">这条回答对你有帮助吗？</span>' +
    '<button class="fb-btn fb-up">👍</button>' +
    '<button class="fb-btn fb-down">👎</button>';

  const upBtn = feedbackEl.querySelector(".fb-up");
  const downBtn = feedbackEl.querySelector(".fb-down");

  upBtn.addEventListener("click", () => {
    sendFeedback(answerId, "up", "").then(() => {
      upBtn.classList.add("active-up");
      downBtn.classList.remove("active-down");
      panelEl.hidden = true;
      feedbackEl.querySelector(".fb-note").textContent = "✓ 已记录，感谢！";
    });
  });

  downBtn.addEventListener("click", () => {
    panelEl.hidden = false;
    downBtn.classList.add("active-down");
    renderDownPanel(panelEl, answerId, feedbackEl, downBtn);
    scrollBottom();
  });
}

function renderDownPanel(panelEl, answerId, feedbackEl, downBtn) {
  panelEl.innerHTML =
    '<div class="fb-title">哪里不对？（用于后续迭代）</div>' +
    '<div class="fb-reasons"></div>' +
    '<textarea placeholder="补充说明（可选）：正确信息或你期望的回答..."></textarea>' +
    '<button class="fb-submit">提交反馈</button>';

  const reasonsEl = panelEl.querySelector(".fb-reasons");
  let selected = "";
  for (const r of REASONS) {
    const b = document.createElement("button");
    b.className = "fb-reason";
    b.textContent = r;
    b.addEventListener("click", () => {
      selected = selected === r ? "" : r;
      reasonsEl.querySelectorAll(".fb-reason").forEach((x) =>
        x.classList.remove("selected")
      );
      if (selected) b.classList.add("selected");
    });
    reasonsEl.appendChild(b);
  }

  panelEl.querySelector(".fb-submit").addEventListener("click", () => {
    const note = panelEl.querySelector("textarea").value.trim();
    const reason = selected ? (note ? selected + "｜" + note : selected) : note;
    sendFeedback(answerId, "down", reason).then(() => {
      panelEl.hidden = true;
      feedbackEl.querySelector(".fb-note").textContent = "✓ 已记录，我们会据此改进";
      downBtn.classList.add("active-down");
      feedbackEl.querySelector(".fb-up").classList.remove("active-up");
    });
  });
}

async function sendFeedback(answerId, rating, reason) {
  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer_id: answerId, rating: rating, reason: reason }),
    });
  } catch (e) {
    console.error("feedback failed", e);
  }
}

/* ── 发送、停止与排队 ── */

// 生成中再发送 = 入队；空闲时立刻开新一轮
function submit(text) {
  const fromInput = text == null;
  const q = (fromInput ? inputEl.value : text).trim();
  if (!q) return;
  if (fromInput) {
    inputEl.value = "";
    inputEl.style.height = "auto";
  }
  if (busy) {
    if (queue.length >= MAX_QUEUE) {
      showStatus("排队已满（最多 " + MAX_QUEUE + " 条），等当前回答结束再问");
      return;
    }
    queue.push(q);
    renderQueue();
    syncButtons();
    return;
  }
  ask(q);
}

async function ask(question) {
  busy = true;
  controller = new AbortController();
  syncButtons();

  // 首条提问后移除空态首屏，主区回到对话流布局
  const welcomeEl = chatEl.querySelector(".msg.welcome");
  if (welcomeEl) {
    welcomeEl.remove();
    setEmptyState(false);
  }

  addUserMsg(question);
  // 流式生成期间两个新会话入口都保持禁用，避免旧回答写入新会话。
  const ui = addBotMsg();
  let answerText = "";
  let answerId = null;
  let priceStatus = "";
  let priceAudit = "";
  let thinkText = "";
  let thinkT0 = 0;
  let thinkCollapsed = false;

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        question: question,
        session_id: sessionId(),
        history: history.slice(-8),
      }),
    });
    if (!resp.ok || !resp.body) {
      throw new Error("HTTP " + resp.status);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        let ev;
        try {
          ev = JSON.parse(line.slice(5).trim());
        } catch (e) {
          continue;
        }
        if (ev.type === "status") {
          showStatus(ev.message || "");
        } else if (ev.type === "sources") {
          renderSources(ui.sources, ev.sources, "");
        } else if (ev.type === "think") {
          // 思考过程流式展示（改善长等待感知），正文开始后自动收起
          if (!thinkText) {
            thinkT0 = performance.now();
            ui.think.hidden = false;
            ui.think.open = true;
          }
          thinkText += ev.text;
          ui.thinkBody.textContent = thinkText;
          ui.thinkBody.scrollTop = ui.thinkBody.scrollHeight;
          scrollBottom();
        } else if (ev.type === "delta") {
          if (thinkText && !thinkCollapsed) {
            thinkCollapsed = true;
            const secs = ((performance.now() - thinkT0) / 1000).toFixed(1);
            ui.think.dataset.secs = secs;
            ui.thinkTitle.textContent = "思考过程";
            ui.thinkMeta.textContent = " · " + secs + "s（已收起，点击展开）";
            ui.think.open = false;
          }
          answerText += ev.text;
          ui.bubble.innerHTML = renderMd(answerText) + '<span class="cursor">▍</span>';
          scrollBottom();
        } else if (ev.type === "done") {
          answerId = ev.answer_id;
          priceStatus = ev.price_status;
          priceAudit = ev.price_audit || "";
        } else if (ev.type === "error") {
          answerText += (answerText ? "\n\n" : "") +
            "❌ " + (ev.message || "生成失败，请重试。");
        }
      }
    }

    ui.bubble.innerHTML = renderMd(answerText);
    if (priceStatus) {
      // done 事件到达后再补价格徽章（需保留已有来源 chips）
      const tmp = document.createElement("div");
      renderSources(tmp, [], priceStatus, priceAudit);
      if (tmp.firstChild && ui.sources.hidden) ui.sources.hidden = false;
      if (tmp.firstChild) ui.sources.insertBefore(tmp.firstChild, ui.sources.firstChild);
    }
    if (answerId != null) {
      setupFeedback(ui.feedback, ui.fbPanel, answerId);
      history.push({ role: "user", content: question });
      history.push({ role: "assistant", content: answerText });
    }
  } catch (e) {
    if (e && e.name === "AbortError") {
      // 用户点了「停止」：保留已生成部分（不计入对话上下文，后台已标记 interrupted）
      if (thinkText && !thinkCollapsed) {
        thinkCollapsed = true;
        ui.thinkTitle.textContent = "思考过程";
        ui.thinkMeta.textContent = " · 已停止";
        ui.think.open = false;
      }
      ui.bubble.innerHTML =
        (answerText ? renderMd(answerText) : "") +
        '<div class="stop-note">⏹ 已停止生成' +
        (answerText ? "，以上为已生成部分" : "") +
        "</div>";
    } else {
      ui.bubble.innerHTML =
        '<span class="error-text">❌ 连接失败：' + e.message + "</span>";
    }
  } finally {
    hideStatus();
    busy = false;
    controller = null;
    syncButtons();
    if (desktopQuery.matches) inputEl.focus();
    scrollBottom();
    drainQueue(); // 串行：自动发送排队中的下一条
  }
}

/* ── 事件绑定 ── */

sendBtn.addEventListener("click", () => submit());

stopBtn.addEventListener("click", () => {
  if (!busy || !controller) return;
  controller.abort(); // 断开 SSE，服务端取消上游 LLM 调用
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
    e.preventDefault();
    submit(); // 生成中回车 = 加入排队
  }
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 176) + "px";
  syncButtons();
});

function resetSession() {
  if (busy || !chatEl.querySelector(".msg.user")) return;
  localStorage.removeItem("apa_session");
  history = [];
  queue = [];
  renderQueue();
  chatEl.innerHTML = "";
  inputEl.value = "";
  inputEl.style.height = "auto";
  hideStatus();
  welcome();
  sessionId();
  workspaceEl.scrollTop = 0;
  if (desktopQuery.matches) inputEl.focus();
}

newBtn.addEventListener("click", resetSession);
newTopBtn.addEventListener("click", resetSession);
sidebarToggle.addEventListener("click", () => {
  layoutEl.classList.toggle("sidebar-collapsed");
  syncSidebar();
});
desktopQuery.addEventListener("change", syncSidebar);

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    submit(chip.dataset.q); // 生成中点击推荐问题同样入队
  });
});

/* ── 初始欢迎语 ── */

function welcome() {
  const div = document.createElement("div");
  div.className = "msg bot welcome";
  div.innerHTML =
    '<div class="avatar">🤖</div>' +
    '<div class="bubble-wrap"><div class="bubble"></div></div>';
  div.querySelector(".bubble").innerHTML =
    '<div class="welcome-mark" aria-hidden="true">' +
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M11 7H6v18h5M21 7h5v18h-5M11 19c3 3 7 3 10 0"/>' +
    '<path d="M12 13h.01M20 13h.01" stroke-width="3"/></svg></div>' +
    '<h1>今天想了解什么？</h1>' +
    '<p>从模型选型到产品方案，把问题交给我。</p>';
  chatEl.appendChild(div);
  setEmptyState(true);
  syncButtons();
}

welcome();
syncSidebar();

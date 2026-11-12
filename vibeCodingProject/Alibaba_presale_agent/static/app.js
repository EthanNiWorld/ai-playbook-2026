/* 阿里小可爱AI问答助手 — 前端逻辑：SSE 流式聊天 + 👍/👎 反馈 */
"use strict";

const chatEl = document.getElementById("chat");
const statusBar = document.getElementById("statusBar");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const stopBtn = document.getElementById("stop");
const attachBtn = document.getElementById("attach");
const fileInput = document.getElementById("fileInput");
const attachBar = document.createElement("div");
attachBar.id = "attachBar";
attachBar.className = "attach-bar";
attachBar.hidden = true;
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
let history = []; // [{role, content}] 供多轮上下文（content 可为 str 或多模态 blocks 数组）
let queue = []; // 待发送问题（串行：当前回答结束后依次自动发送）
let controller = null; // 当前流的 AbortController，供「停止」中断
const MAX_QUEUE = 3; // 排队上限，避免无限堆叠
const REASONS = ["价格不对/过期", "内容过时", "答非所问", "来源不可信", "其他"];

/* ── 截图/图片附件（qwen3.8-max 视觉输入）── */
const MAX_IMAGES = 4;
const MAX_IMAGE_MB = 5;
let pendingImages = []; // [{dataUrl, name, size}]

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = reject;
    fr.readAsDataURL(file);
  });
}

function isImageFile(file) {
  return /^(image\/png|image\/jpeg|image\/webp)$/.test(file.type || "");
}

function isHtmlFile(file) {
  return /\.html?$/i.test(file.name || "") || file.type === "text/html";
}

async function addImageFiles(files) {
  const list = Array.from(files || []).filter(isImageFile);
  for (const f of list) {
    if (pendingImages.length >= MAX_IMAGES) {
      showStatus("最多附 " + MAX_IMAGES + " 张截图，多余的已忽略");
      break;
    }
    if (f.size > MAX_IMAGE_MB * 1024 * 1024) {
      showStatus("图片超过 " + MAX_IMAGE_MB + "MB，已忽略：「" + f.name + "」");
      continue;
    }
    try {
      const dataUrl = await fileToDataUrl(f);
      pendingImages.push({ dataUrl: dataUrl, name: f.name, size: f.size });
    } catch (e) {
      console.error("read file failed", e);
    }
  }
  renderAttachBar();
  syncButtons();
}

function removePendingImage(i) {
  pendingImages.splice(i, 1);
  renderAttachBar();
  syncButtons();
}

function renderAttachBar() {
  attachBar.innerHTML = "";
  if (!pendingImages.length) {
    attachBar.hidden = true;
    return;
  }
  pendingImages.forEach((img, i) => {
    const item = document.createElement("div");
    item.className = "attach-item";
    const thumb = document.createElement("img");
    thumb.src = img.dataUrl;
    thumb.alt = img.name || "截图";
    thumb.title = img.name || "截图";
    item.appendChild(thumb);
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "attach-remove";
    rm.textContent = "×";
    rm.title = "移除「" + (img.name || "截图") + "」";
    rm.setAttribute("aria-label", rm.title);
    rm.addEventListener("click", () => removePendingImage(i));
    item.appendChild(rm);
    attachBar.appendChild(item);
  });
  attachBar.hidden = false;
}

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

const jumpLatestBtn = document.getElementById("jumpLatest");
// 用户是否停留在对话底部：上翻历史/输入时不被流式输出强行拽回最新
let stickBottom = true;
let lastTop = 0; // 上一次记录的滚动位置，用于识别「用户上翻」

function nearBottom(el, px = 90) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < px;
}

function syncStick() {
  const top = chatEl.scrollTop;
  // 位置变小 = 用户上翻（追加内容只会让 scrollHeight 变大，不会让 scrollTop 变小），
  // 直接比较位置而不只依赖 scroll 事件，避免流式 delta 抢在事件前把页面拽回底部。
  if (top < lastTop - 4) stickBottom = false;
  else if (nearBottom(chatEl)) stickBottom = true;
  lastTop = top;
  if (stickBottom) jumpLatestBtn.hidden = true;
}

function scrollBottom(force = false) {
  if (!force) {
    syncStick();
    if (!stickBottom) {
      // 用户正在上翻阅读：只给「回到最新」入口，不打断当前阅读位置
      jumpLatestBtn.hidden = false;
      return;
    }
  }
  chatEl.scrollTop = chatEl.scrollHeight;
  stickBottom = true;
  lastTop = chatEl.scrollTop;
  jumpLatestBtn.hidden = true;
}

chatEl.addEventListener("scroll", syncStick, { passive: true });

jumpLatestBtn.addEventListener("click", () => scrollBottom(true));

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
  sendBtn.disabled = busy || (!inputEl.value.trim() && !pendingImages.length);
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
  const head =
    queue[0].text.length > 30 ? queue[0].text.slice(0, 30) + "…" : queue[0].text;
  const text = document.createElement("span");
  text.className = "queue-text";
  text.textContent =
    "⏳ 已排队 " + queue.length + " 条 · 下一条：" +
    (head || "[截图]");
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
  ask(next.text, next.images || []);
}

function syncSidebar() {
  const expanded = desktopQuery.matches && !layoutEl.classList.contains("sidebar-collapsed");
  sidebarToggle.setAttribute("aria-expanded", String(expanded));
  sidebarToggle.setAttribute("aria-label", expanded ? "收起侧边栏" : "展开侧边栏");
  sidebarToggle.title = expanded ? "收起侧边栏" : "展开侧边栏";
}

/* ── 消息渲染 ── */

function addUserMsg(text, images) {
  const div = document.createElement("div");
  div.className = "msg user";
  div.innerHTML =
    '<div class="avatar">👤</div>' +
    '<div class="bubble-wrap"><div class="bubble"></div></div>';
  const bubble = div.querySelector(".bubble");
  if (images && images.length) {
    const strip = document.createElement("div");
    strip.className = "msg-images";
    images.forEach((src) => {
      const im = document.createElement("img");
      im.src = src;
      im.alt = "截图";
      im.addEventListener("click", () => {
        window.open(src, "_blank", "noopener");
      });
      strip.appendChild(im);
    });
    bubble.appendChild(strip);
  }
  if (text) {
    const line = document.createElement("div");
    line.textContent = text;
    bubble.appendChild(line);
  }
  chatEl.appendChild(div);
  scrollBottom(true); // 自己发消息时总是回到最新
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

// 生成中再发送 = 入队；空闲时立刻开新一轮（截图仅随输入框提交携带）
function submit(text) {
  const fromInput = text == null;
  const q = (fromInput ? inputEl.value : text).trim();
  const imgs = fromInput ? pendingImages : [];
  if (!q && !imgs.length) return;
  if (fromInput) {
    inputEl.value = "";
    inputEl.style.height = "auto";
  }
  if (busy) {
    if (queue.length >= MAX_QUEUE) {
      showStatus("排队已满（最多 " + MAX_QUEUE + " 条），等当前回答结束再问");
      return;
    }
    queue.push({ text: q, images: imgs });
    if (imgs.length) {
      pendingImages = [];
      renderAttachBar();
    }
    renderQueue();
    syncButtons();
    return;
  }
  if (imgs.length) {
    pendingImages = [];
    renderAttachBar();
  }
  ask(q, imgs);
}

async function ask(question, images) {
  images = images || [];
  busy = true;
  controller = new AbortController();
  syncButtons();

  // 首条提问后移除空态首屏，主区回到对话流布局
  const welcomeEl = chatEl.querySelector(".msg.welcome");
  if (welcomeEl) {
    welcomeEl.remove();
    setEmptyState(false);
  }

  addUserMsg(
    question,
    images.map((x) => x.dataUrl)
  );
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
        images: images.map((x) => x.dataUrl),
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
          // 思考面板内部同样遵循「只在底部才跟随」，上翻读思考时不被拽回
          if (nearBottom(ui.thinkBody, 60)) {
            ui.thinkBody.scrollTop = ui.thinkBody.scrollHeight;
          }
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
      // 截图轮的 user 消息以多模态 blocks 入历史（后续轮重发给模型，追问可见）
      if (images.length) {
        history.push({
          role: "user",
          content: images
            .map((x) => ({ type: "image_url", image_url: { url: x.dataUrl } }))
            .concat([{ type: "text", text: question }]),
        });
      } else {
        history.push({ role: "user", content: question });
      }
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

/* ── 供应商测试报告上传 → 阻塞项定界分析 ── */
const MAX_REPORT_MB = 3;

function readAsText(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = reject;
    fr.readAsText(file);
  });
}

async function analyzeReport(file) {
  if (!file) return;
  if (!/\.html?$/i.test(file.name) && file.type !== "text/html") {
    showStatus("请上传 HTML 格式的供应商测试报告");
    return;
  }
  if (file.size > MAX_REPORT_MB * 1024 * 1024) {
    showStatus("报告超过 " + MAX_REPORT_MB + "MB，请精简后重试");
    return;
  }
  if (busy) {
    showStatus("当前有回答正在生成，结束后再上传报告");
    return;
  }
  let htmlText;
  try {
    htmlText = await readAsText(file);
  } catch (e) {
    showStatus("读取文件失败：" + e.message);
    return;
  }
  busy = true;
  controller = new AbortController();
  syncButtons();
  const welcomeEl = chatEl.querySelector(".msg.welcome");
  if (welcomeEl) { welcomeEl.remove(); setEmptyState(false); }
  addUserMsg("📄 上传测试报告：" + file.name);
  const ui = addBotMsg();
  let answerText = "";
  let thinkText = "";
  let thinkT0 = 0;
  let thinkCollapsed = false;
  let metaShown = false;
  try {
    const resp = await fetch("/api/report/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ html: htmlText, filename: file.name }),
    });
    if (!resp.ok || !resp.body) {
      let detail = "HTTP " + resp.status;
      try { const j = await resp.json(); if (j.detail) detail = j.detail; } catch (e) {}
      throw new Error(detail);
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
        try { ev = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
        if (ev.type === "meta") {
          if (!metaShown && ev.summary) {
            metaShown = true;
            const md = document.createElement("div");
            md.className = "report-meta";
            md.textContent = ev.summary;
            ui.bubble.parentNode.insertBefore(md, ui.bubble);
          }
        } else if (ev.type === "status") {
          showStatus(ev.message || "");
        } else if (ev.type === "think") {
          if (!thinkText) { thinkT0 = performance.now(); ui.think.hidden = false; ui.think.open = true; }
          thinkText += ev.text;
          ui.thinkBody.textContent = thinkText;
          if (nearBottom(ui.thinkBody, 60)) ui.thinkBody.scrollTop = ui.thinkBody.scrollHeight;
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
        } else if (ev.type === "error") {
          answerText += (answerText ? "\n\n" : "") + "❌ " + (ev.message || "分析失败，请重试。");
        }
      }
    }
    ui.bubble.innerHTML = renderMd(answerText || "（无输出）");
  } catch (e) {
    if (e && e.name === "AbortError") {
      if (thinkText && !thinkCollapsed) { thinkCollapsed = true; ui.thinkTitle.textContent = "思考过程"; ui.thinkMeta.textContent = " · 已停止"; ui.think.open = false; }
      ui.bubble.innerHTML = (answerText ? renderMd(answerText) : "") +
        '<div class="stop-note">⏹ 已停止生成' + (answerText ? "，以上为已生成部分" : "") + "</div>";
    } else {
      ui.bubble.innerHTML = '<span class="error-text">❌ ' + e.message + "</span>";
    }
  } finally {
    hideStatus();
    busy = false;
    controller = null;
    syncButtons();
    if (desktopQuery.matches) inputEl.focus();
    scrollBottom();
    drainQueue();
  }
}

/* ── 语音输入（qwen-audio-3.1-asr-flash，实时分段识别）── */
const micBtn = document.getElementById("mic");
const MIC_MAX_S = 60;
const MIC_SEGMENT_S = 4;      // 分段窗口：边说边出字，说完一句 ≈4s 后文字上屏
let micRecording = false;
let micBusy = false;
let micStream = null;
let micCtx = null;
let micProc = null;
let micTimer = null;
let micAll = null;            // Float32 累积采样
let micAllLen = 0;
let micSegOffset = 0;         // 已送识别的采样偏移
let micReqBusy = false;       // 段识别请求串行闸
let micDraft = "";            // 已识别拼接文本（实时上屏）
let micBase = "";             // 录音开始时输入框已有内容

function micSetNote(text, rec) {
  let note = micBtn.parentElement.querySelector(".mic-note");
  if (!text) {
    if (note) note.remove();
    return;
  }
  if (!note) {
    note = document.createElement("span");
    note.className = "mic-note";
    micBtn.parentElement.insertBefore(note, micBtn);
  }
  note.textContent = text;
  note.classList.toggle("rec", !!rec);
}

function micUpdateInput() {
  inputEl.value = micBase + micDraft;
  inputEl.dispatchEvent(new Event("input", { bubbles: true }));
}

// 降采样到目标采样率（线性插值，录音质量对 ASR 足够）
function downsample(buf, from, to) {
  if (to >= from) return buf;
  const ratio = from / to;
  const n = Math.floor(buf.length / ratio);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const pos = i * ratio;
    const i0 = Math.floor(pos);
    const frac = pos - i0;
    out[i] = buf[i0] * (1 - frac) + buf[i0 + 1] * frac;
  }
  return out;
}

// Float32 PCM → 16bit mono WAV
function pcmToWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (off, s) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE");
  w(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, samples.length * 2, true);
  let off = 44;
  for (let i = 0; i < samples.length; i++, off += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

function blobToB64(blob) {
  return blob.arrayBuffer().then((ab) => {
    let bin = "";
    const u8 = new Uint8Array(ab);
    for (let i = 0; i < u8.length; i += 0x8000) {
      bin += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    }
    return btoa(bin);
  });
}

// 送识别一段（samples 为原始采样率的 Float32 段），带上一段文本作上下文
async function micRecognize(samples, srcRate) {
  const rate = 16000;
  const wav = pcmToWav(downsample(samples, srcRate, rate), rate);
  const b64 = await blobToB64(wav);
  const r = await fetch("/api/asr", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audio: b64, context: micDraft.slice(-380) }),
  });
  const d = await r.json();
  if (d.ok && d.text) {
    micDraft += (micDraft ? "" : "") + d.text;
    micUpdateInput();
  }
}

// 每 MIC_SEGMENT_S 秒触发一次：把未识别的累积采样切一段送 ASR
async function micFlushSegment(final) {
  if (micReqBusy || !micAll) return;
  const srcRate = micCtx ? micCtx.sampleRate : 48000;
  const segLen = Math.floor(MIC_SEGMENT_S * srcRate);
  const avail = micAllLen - micSegOffset;
  if (final) {
    if (avail < srcRate * 0.8) return; // 残段不足 0.8s 丢弃
  } else {
    if (avail < segLen) return;        // 未累积满一整段：等下一 tick
  }
  const take = final ? avail : Math.min(avail, segLen);
  const seg = micAll.slice(micSegOffset, micSegOffset + take);
  micSegOffset += take;
  micReqBusy = true;
  try {
    await micRecognize(seg, srcRate);
  } catch (e) {
    micSetNote("刚才没听清，已跳过", false);
    setTimeout(() => { if (!micRecording) micSetNote(""); }, 2500);
  } finally {
    micReqBusy = false;
  }
}

async function micStart() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
  } catch (e) {
    micSetNote("无法访问麦克风", false);
    setTimeout(() => micSetNote(""), 2500);
    return;
  }
  micCtx = new (window.AudioContext || window.webkitAudioContext)();
  const src = micCtx.createMediaStreamSource(micStream);
  micProc = micCtx.createScriptProcessor(4096, 1, 1);
  micAll = new Float32Array(Math.ceil(MIC_MAX_S * micCtx.sampleRate));
  micAllLen = 0;
  micSegOffset = 0;
  micDraft = "";
  micBase = inputEl.value ? inputEl.value.replace(/\s+$/, "") + "\n" : "";
  micReqBusy = false;
  micProc.onaudioprocess = (e) => {
    const d = e.inputBuffer.getChannelData(0);
    if (micAllLen + d.length <= micAll.length) {
      micAll.set(d, micAllLen);
      micAllLen += d.length;
    }
  };
  src.connect(micProc);
  micProc.connect(micCtx.destination);
  micRecording = true;
  micBtn.classList.add("recording");
  micBtn.title = "说完点我";
  micTimer = setInterval(() => {
    micFlushSegment(false);
    micSetNote("🎤 正在聆听…（说完点一下话筒）", true);
    const sec = Math.floor(micAllLen / (micCtx ? micCtx.sampleRate : 48000));
    if (sec >= MIC_MAX_S) micStop();
  }, 800);
}

async function micStop() {
  if (!micRecording) return;
  micRecording = false;
  clearInterval(micTimer);
  micSetNote("🎤 稍等，正在整理…", false);
  micBusy = true;
  try {
    await micFlushSegment(true);
    // 等待可能还在飞的段识别完成后收尾
    let waited = 0;
    while (micReqBusy && waited < 30) { await new Promise(r => setTimeout(r, 200)); waited += 0.2; }
    const track = micStream && micStream.getTracks()[0];
    if (track) track.stop();
    if (micProc) { try { micProc.disconnect(); } catch (e) {} }
    if (micCtx) { try { await micCtx.close(); } catch (e) {} }
    if (!micDraft) {
      micSetNote("没有识别到内容，请靠近麦克风重试", false);
      setTimeout(() => micSetNote(""), 3000);
      micUpdateInput();
    } else {
      inputEl.value = micBase + micDraft + " ";
      inputEl.dispatchEvent(new Event("input", { bubbles: true }));
      inputEl.focus();
      micSetNote("");
    }
  } finally {
    micBusy = false;
    micStream = null;
    micCtx = null;
    micProc = null;
    micAll = null;
    micBtn.classList.remove("recording");
    micBtn.title = "点我说话（最长 60 秒），说完再点一下";
  }
}

// 麦克风可用性：getUserMedia 仅在安全上下文（HTTPS / localhost）可用。
// HTTP 访问（如 http://day1cloud.cn）时按钮仍显示，点击给出升级提示，
// 避免用户以为功能缺失（线上实测踩坑：地址栏"不安全"= HTTP）。
const micSupported = !!(
  navigator.mediaDevices && navigator.mediaDevices.getUserMedia
);
if (micBtn) {
  micBtn.hidden = false;
  micBtn.addEventListener("click", () => {
    if (micBusy) return;
    if (!micSupported) {
      micSetNote("🎤 语音输入需要 HTTPS 访问（当前是 HTTP，浏览器不开放麦克风）", false);
      setTimeout(() => micSetNote(""), 4000);
      return;
    }
    if (micRecording) { micStop(); } else { micStart(); }
  });
}

/* ── 事件绑定 ── */

sendBtn.addEventListener("click", () => submit());

// 截图上传三入口：按钮选择 / 剪贴板粘贴 / 拖拽到输入区
const composerEl = document.querySelector(".composer");
composerEl.parentNode.insertBefore(attachBar, composerEl);
attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files || []);
  fileInput.value = "";
  const imgs = files.filter(isImageFile);
  const htmls = files.filter(isHtmlFile);
  if (imgs.length) addImageFiles(imgs);
  if (htmls.length) analyzeReport(htmls[0]);
});
inputEl.addEventListener("paste", (e) => {
  const files = Array.from(
    (e.clipboardData && e.clipboardData.files) || []
  ).filter(isImageFile);
  if (files.length) {
    e.preventDefault(); // 有图时不把文件名/乱码播进输入框
    addImageFiles(files);
  }
});
const composerWrapEl = document.querySelector(".composer-wrap");
composerWrapEl.addEventListener("dragover", (e) => e.preventDefault());
composerWrapEl.addEventListener("drop", (e) => {
  e.preventDefault();
  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
    const files = Array.from(e.dataTransfer.files);
    const imgs = files.filter(isImageFile);
    const htmls = files.filter(isHtmlFile);
    if (imgs.length) addImageFiles(imgs);
    if (htmls.length) analyzeReport(htmls[0]);
  }
});

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
  pendingImages = [];
  renderAttachBar();
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

/* 短剧工场前端 — 原生 JS（非 module），SSE 流式消费 /api/run。
   风格与事件口径对齐 Alibaba_presale_agent：type=log/asset/done/error。 */

(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  var runBtn = $("runBtn");
  var resumeBtn = $("resumeBtn");
  var logEl = $("log");
  var logCard = $("logCard");
  var statusCard = $("statusCard");
  var statusDot = $("statusDot");
  var statusText = $("statusText");
  var statusTime = $("statusTime");
  var mediaCard = $("mediaCard");
  var gallery = $("gallery");
  var videoGallery = $("videoGallery");
  var imageGallery = $("imageGallery");
  var videoGroup = $("videoGroup");
  var imageGroup = $("imageGroup");
  var mediaCount = $("mediaCount");
  var videoWrap = $("videoWrap");
  var videoPlayer = $("videoPlayer");
  var videoCaption = $("videoCaption");
  var reportCard = $("reportCard");
  var reportBody = $("reportBody");
  var healthBadge = $("healthBadge");
  var stageList = $("stageList");
  var runsList = $("runsList");
  var refreshRunsBtn = $("refreshRuns");
  // 打磨模式确认卡
  var confirmCard = $("confirmCard");
  var confirmStep = $("confirmStep");
  var confirmTip = $("confirmTip");
  var confirmPreview = $("confirmPreview");
  var storyboardEditor = $("storyboardEditor");
  var confirmErr = $("confirmErr");
  var confirmGo = $("confirmGo");
  var confirmRedo = $("confirmRedo");
  var confirmAbort = $("confirmAbort");

  var busy = false;
  var startedAt = 0;
  var timer = null;
  var assetCount = 0;

  // ── 健康检查 ──
  function updateResumeBtn(d) {
    if (d && d.resumable_run) {
      resumeBtn.hidden = false;
      resumeBtn.textContent = "♻️ 续跑 " + d.resumable_run;
    } else {
      resumeBtn.hidden = true;
    }
  }

  function refreshHealth(cb) {
    fetch("/api/health").then(function (r) { return r.json(); }).then(function (d) {
      updateResumeBtn(d);
      if (cb) cb(d);
    }).catch(function () { /* 刷新失败不影响主流程 */ });
  }

  fetch("/api/health").then(function (r) { return r.json(); }).then(function (d) {
    updateResumeBtn(d);
    if (d.credentials_ok) {
      healthBadge.textContent = "就绪 · " + d.video_model;
      healthBadge.className = "badge ok";
    } else {
      healthBadge.textContent = "缺少凭证（检查 .env）";
      healthBadge.className = "badge err";
    }
  }).catch(function () {
    healthBadge.textContent = "服务不可达";
    healthBadge.className = "badge err";
  });

  // ── 历史执行记录 ──
  function fmtTime(ts) {
    var d = new Date(ts * 1000);
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " " +
      p(d.getHours()) + ":" + p(d.getMinutes());
  }

  function loadRuns() {
    fetch("/api/runs").then(function (r) { return r.json(); }).then(function (d) {
      renderRuns((d || {}).runs || []);
    }).catch(function () { /* 历史加载失败不影响主流程 */ });
  }

  function renderRuns(runs) {
    while (runsList.firstChild) runsList.removeChild(runsList.firstChild);
    if (!runs.length) {
      var empty = document.createElement("div");
      empty.className = "run-empty";
      empty.textContent = "暂无历史记录（点「开始生产」跑一次试试）";
      runsList.appendChild(empty);
      return;
    }
    runs.forEach(function (r) {
      var item = document.createElement("div");
      item.className = "run-item";

      var name = document.createElement("span");
      name.className = "run-name"; name.textContent = r.name;
      item.appendChild(name);

      var title = document.createElement("span");
      title.className = "run-title";
      title.textContent = r.title || r.theme || "（未生成分镜）";
      item.appendChild(title);

      var meta = document.createElement("span");
      meta.className = "run-meta";
      meta.textContent = fmtTime(r.mtime) + " · " + (r.assets.image || 0) + " 图 · " +
        (r.assets.video || 0) + " 视频";
      item.appendChild(meta);

      if (r.finished === true) {
        var tag = document.createElement("span");
        tag.className = "tag ok"; tag.textContent = "已完成";
        item.appendChild(tag);
      } else if (r.finished === false) {
        var warn = document.createElement("span");
        warn.className = "tag warn"; warn.textContent = "未完成";
        item.appendChild(warn);
      }

      var actions = document.createElement("span");
      actions.className = "run-actions";
      if (r.resumable) {
        var rbtn = document.createElement("button");
        rbtn.className = "btn ghost small"; rbtn.textContent = "♻️ 续跑";
        rbtn.title = "从本次运行的 checkpoint 继续执行（已完成步骤跳过，不重复计费）";
        rbtn.addEventListener("click", function () { startRun(true, r.name); });
        actions.appendChild(rbtn);
      }
      var btn = document.createElement("button");
      btn.className = "btn ghost small"; btn.textContent = "回看产物";
      btn.addEventListener("click", function () { viewRunAssets(r); });
      actions.appendChild(btn);
      item.appendChild(actions);

      runsList.appendChild(item);
    });
  }

  function viewRunAssets(run) {
    // 回看历史产物：按后端返回的真实文件清单加载（final_cut 置顶，不再猜文件名）
    var runName = (typeof run === "string") ? run : run.name;
    var files = (run && run.files) ? run.files : null;
    resetUI();
    setStatus("回看历史产物：" + runName, false);
    appendLog("回看 " + runName + " 的历史产物");
    fetch("/files/" + runName + "/report.json").then(function (r) {
      if (!r.ok) return null;
      return r.json();
    }).then(function (d) {
      if (d) {
        renderReport({
          "产物目录": d.run_dir ? String(d.run_dir).split("/").slice(-1)[0] : runName,
          "使用模型": (d.models_used || []).join(" · "),
          "任务查询": ((d.task_stats || {}).queries || 0) + " 次，限流 " +
            ((d.task_stats || {}).throttled || 0) + " 次"
        });
      }
    }).catch(function () { /* 无报告则跳过 */ });
    if (files && files.length) {
      // 后端已排序：final_cut > edited > raw > 图片，逐个直接加载
      files.forEach(function (fi) {
        if (fi.kind === "image") addImage(fi.name, "/files/" + runName + "/" + fi.name);
        else addVideo(fi.name, "/files/" + runName + "/" + fi.name);
      });
    } else {
      // 兼容旧接口：files 缺失时回退猜文件名
      var imgs = ["poster.png"], vids = [];
      for (var i = 1; i <= 3; i++) {
        imgs.push("scene_" + i + "_still.png");
        vids.push("scene_" + i + "_raw.mp4");
        vids.push("scene_" + i + "_edited.mp4");
      }
      imgs.forEach(function (f) { probeAsset(runName, f, "image"); });
      vids.forEach(function (f) { probeAsset(runName, f, "video"); });
    }
  }

  function probeAsset(runName, file, kind) {
    var url = "/files/" + runName + "/" + file;
    fetch(url, { method: "HEAD" }).then(function (r) {
      if (r.ok) {
        if (kind === "image") addImage(file, url);
        else addVideo(file, url);
      }
    }).catch(function () { /* 不存在的产物直接跳过 */ });
  }

  refreshRunsBtn.addEventListener("click", loadRuns);
  loadRuns();  // 页面加载即展示历史执行记录

  // ── 阶段标记（按日志前缀识别）──
  var STAGE_RE = [
    [/^\[1\]/, "1"], [/^\[2\]/, "2"], [/^\[3\]/, "3"],
    [/^\[4\]/, "4"], [/^\[5\]/, "5"], [/^\[6\]/, "6"], [/^\[7\]/, "6"]
  ];
  var currentStage = "";

  function markStage(id) {
    if (!id || id === currentStage) return;
    var items = stageList.querySelectorAll("li");
    items.forEach(function (li, idx) {
      var n = String(idx + 1);
      li.classList.remove("active");
      if (n === id) li.classList.add("active", "done");
    });
    currentStage = id;
  }

  function completeStages() {
    stageList.querySelectorAll("li").forEach(function (li) {
      li.classList.remove("active");
      li.classList.add("done");
    });
  }

  // ── 状态条 ──
  function setStatus(text, running) {
    statusCard.hidden = false;
    statusText.textContent = text;
    statusDot.style.animation = running ? "" : "none";
    statusDot.style.background = running ? "" : "var(--ok)";
    if (running && !timer) {
      startedAt = Date.now();
      timer = setInterval(function () {
        var s = Math.round((Date.now() - startedAt) / 1000);
        statusTime.textContent = s + "s";
      }, 1000);
    }
    if (!running && timer) { clearInterval(timer); timer = null; }
  }

  // ── 日志 ──
  function appendLog(text) {
    logCard.hidden = false;
    var atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 30;
    logEl.textContent += text + "\n";
    // 只保留最近 400 行，避免长跑 DOM 膨胀
    var lines = logEl.textContent.split("\n");
    if (lines.length > 400) logEl.textContent = lines.slice(-400).join("\n");
    if (atBottom) logEl.scrollTop = logEl.scrollHeight;
    for (var i = 0; i < STAGE_RE.length; i++) {
      if (STAGE_RE[i][0].test(text)) { markStage(STAGE_RE[i][1]); break; }
    }
  }

  $("toggleLog").addEventListener("click", function () {
    var collapsed = logEl.hidden;
    logEl.hidden = !collapsed;
    this.textContent = collapsed ? "收起" : "展开";
  });

  // ── 产物 ──
  function addImage(label, url) {
    mediaCard.hidden = false;
    imageGroup.hidden = false;  // 图片分组：海报/剧照都进这一组
    var card = document.createElement("div");
    card.className = "shot";
    var a = document.createElement("a");
    a.href = url; a.target = "_blank"; a.rel = "noopener";
    var img = document.createElement("img");
    img.src = url; img.alt = label; img.loading = "lazy";
    a.appendChild(img);
    var cap = document.createElement("div");
    cap.className = "shot-label"; cap.textContent = label;
    card.appendChild(a); card.appendChild(cap);
    imageGallery.appendChild(card);
    assetCount++;
    mediaCount.textContent = assetCount + " 个产物";
  }

  function addVideo(label, url) {
    // 视频分组：每个视频独立成卡，final_cut 等成片与实时产物都进这一组
    mediaCard.hidden = false;
    videoGroup.hidden = false;
    var card = document.createElement("div");
    card.className = "shot shot-video";
    var v = document.createElement("video");
    v.src = url; v.controls = true; v.playsInline = true;
    v.preload = "metadata"; v.muted = true;
    card.appendChild(v);
    var cap = document.createElement("div");
    cap.className = "shot-label"; cap.textContent = label;
    card.appendChild(cap);
    videoGallery.appendChild(card);
    assetCount++;
    mediaCount.textContent = assetCount + " 个产物";
  }

  function addReport(url) {
    fetch(url).then(function (r) { return r.json(); }).then(function (d) {
      renderReport({
        "产物目录": d.run_dir || "",
        "使用模型": (d.models_used || []).join(" · "),
        "任务查询": (d.task_stats && d.task_stats.queries || 0) + " 次" +
          (d.task_stats ? "，限流 " + d.task_stats.throttled + " 次" : "")
      });
    }).catch(function () { /* 报告解析失败不影响主流程 */ });
  }

  function renderReport(kv) {
    reportCard.hidden = false;
    while (reportBody.firstChild) reportBody.removeChild(reportBody.firstChild);
    Object.keys(kv).forEach(function (k) {
      var row = document.createElement("div");
      row.className = "kv";
      var b = document.createElement("b"); b.textContent = k;
      var span = document.createElement("span");
      span.textContent = kv[k] || "—";
      row.appendChild(b); row.appendChild(span);
      reportBody.appendChild(row);
    });
  }

  // ── 打磨模式：人工确认卡 ──
  function clearNode(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function previewImage(path, label) {
    var wrap = document.createElement("div");
    wrap.className = "confirm-thumb";
    var img = document.createElement("img");
    img.src = "/files/" + path; img.alt = label; img.loading = "lazy";
    var cap = document.createElement("div");
    cap.className = "shot-label"; cap.textContent = label;
    wrap.appendChild(img); wrap.appendChild(cap);
    confirmPreview.appendChild(wrap);
  }

  function showConfirm(ev) {
    confirmCard.hidden = false;
    confirmStep.textContent = ev.title || ev.step;
    confirmTip.textContent = ev.tip || "";
    confirmErr.hidden = true;
    confirmErr.textContent = "";
    clearNode(confirmPreview);
    storyboardEditor.hidden = true;
    storyboardEditor.value = "";

    var p = ev.payload || {};
    if (ev.step === "storyboard") {
      // 分镜可直接在线编辑：改完点确认，后续图片/视频按新分镜走
      storyboardEditor.hidden = false;
      storyboardEditor.value = JSON.stringify(p.board, null, 2);
    } else if (ev.step === "images") {
      previewImage(p.poster, "海报 poster.png");
      (p.stills || []).forEach(function (s, i) {
        previewImage(s, "剧照 " + (i + 1));
      });
    } else if (ev.step === "qa") {
      (p.results || []).forEach(function (qa) {
        var row = document.createElement("div");
        row.className = "qa-row";
        var flag = document.createElement("span");
        flag.className = "tag " + (qa.pass ? "ok" : "warn");
        flag.textContent = qa.pass ? "✅ 通过" : "⚠️ 未过";
        var desc = document.createElement("span");
        desc.textContent = "场景 " + qa.scene + "（" + (qa.score != null ? qa.score + " 分）" : "）") +
          (qa.summary || "");
        row.appendChild(flag); row.appendChild(desc);
        confirmPreview.appendChild(row);
      });
    } else if (ev.step === "video") {
      (p.clips || []).forEach(function (c) {
        if (!c.url) return;
        var v = document.createElement("video");
        v.src = c.url; v.controls = true; v.playsInline = true;
        v.preload = "metadata"; v.className = "confirm-video";
        var cap = document.createElement("div");
        cap.className = "shot-label"; cap.textContent = "场景 " + c.scene + " 原始视频";
        confirmPreview.appendChild(v); confirmPreview.appendChild(cap);
      });
    }
    // 视频任务已计费，不提供「重新生成」（终止后可删 checkpoint 里的 video_tasks 再续跑重做）
    confirmRedo.hidden = (ev.step === "video");
    confirmCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function sendConfirm(action) {
    var body = { action: action, storyboard: null };
    if (action === "continue" && !storyboardEditor.hidden && storyboardEditor.value.trim()) {
      body.storyboard = storyboardEditor.value;
    }
    fetch("/api/run/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.ok) {
        confirmCard.hidden = true;
        appendLog("👉 已确认：" + ({ continue: "继续下一步", redo: "重新生成本步", abort: "终止（可续跑）" })[action]);
        if (action !== "abort") {
          // 清掉「等待人工确认」的状态文案，避免确认后仍残留
          setStatus(action === "redo" ? "🔁 已确认，重新生成本步…" : "✅ 已确认，继续执行…", true);
        }
      } else if ((d.error || "").indexOf("当前没有等待确认") >= 0) {
        // 确认点已失效（SSE 断开时服务端会自动终止确认点并清空状态）：
        // 隐藏残留卡片并提示原因，而不是留在页面上反复报错
        confirmCard.hidden = true;
        appendLog("ℹ️ 确认点已失效（页面刷新/断网时流水线会自动在确认点终止），已完成的步骤保留在 checkpoint。");
        refreshHealth();
        if (statusText.textContent.indexOf("⏸️") >= 0) {
          setStatus("⏸️ 确认点已失效，点「♻️ 续跑」可继续", false);
        }
      } else {
        confirmErr.hidden = false;
        confirmErr.textContent = "❌ " + (d.error || "确认失败");
      }
    }).catch(function (e) {
      confirmErr.hidden = false;
      confirmErr.textContent = "❌ " + e.message;
    });
  }

  confirmGo.addEventListener("click", function () { sendConfirm("continue"); });
  confirmRedo.addEventListener("click", function () { sendConfirm("redo"); });
  confirmAbort.addEventListener("click", function () { sendConfirm("abort"); });

  // ── SSE 消费 ──
  function handleEvent(ev) {
    if (ev.type === "log") {
      appendLog(ev.text);
    } else if (ev.type === "asset") {
      if (ev.kind === "image") addImage(ev.label, ev.url);
      else if (ev.kind === "video") addVideo(ev.label, ev.url);
      else if (ev.kind === "json" && ev.label === "report.json") addReport(ev.url);
    } else if (ev.type === "confirm") {
      showConfirm(ev);
      setStatus("⏸️ 等待人工确认：「" + (ev.title || ev.step) + "」", false);
    } else if (ev.type === "paused") {
      confirmCard.hidden = true;  // 终止时清掉确认卡，避免残留可点按钮
      var pr = ev.report || {};
      renderReport({
        "产物目录": pr.run_dir || "",
        "使用模型": (pr.models_used || []).join(" · "),
        "状态": "已在确认点终止（可续跑）"
      });
      setStatus("⏸️ 已在确认点终止，点「续跑」可继续", false);
      appendLog("⏸️ 已在确认点终止，已完成步骤保留在 checkpoint，可续跑。");
      refreshHealth();
    } else if (ev.type === "done") {
      var r = ev.report || {};
      renderReport({
        "产物目录": r.run_dir || "",
        "使用模型": (r.models_used || []).join(" · "),
        "任务查询": ((r.task_stats || {}).queries || 0) + " 次，限流 " +
          ((r.task_stats || {}).throttled || 0) + " 次"
      });
      completeStages();
      setStatus("✅ 生产完成", false);
      confirmCard.hidden = true;  // 收尾时清掉确认卡，避免残留可点按钮
    } else if (ev.type === "error") {
      appendLog("❌ " + ev.message);
      setStatus("❌ 出错：" + ev.message, false);
      confirmCard.hidden = true;  // 出错时清掉确认卡，避免残留可点按钮
      // 失败后刷新可续跑探测：失败任务已有 checkpoint，展示「续跑」按钮
      refreshHealth();
    }
  }

  function setBusy(v) {
    busy = v;
    runBtn.disabled = v;
    resumeBtn.disabled = v;
    runBtn.textContent = v ? "生产中…" : "🚀 开始生产";
    if (!v && timer) { clearInterval(timer); timer = null; }
  }

  function resetUI() {
    while (gallery.firstChild) gallery.removeChild(gallery.firstChild);
    while (videoGallery.firstChild) videoGallery.removeChild(videoGallery.firstChild);
    while (imageGallery.firstChild) imageGallery.removeChild(imageGallery.firstChild);
    videoGroup.hidden = true;
    imageGroup.hidden = true;
    assetCount = 0;
    mediaCount.textContent = "";
    mediaCard.hidden = true;
    videoWrap.hidden = true;
    videoPlayer.removeAttribute("src");
    videoPlayer.load();
    reportCard.hidden = true;
    logEl.textContent = "";
    statusTime.textContent = "";
    confirmCard.hidden = true;
    confirmPreview.textContent = "";
    storyboardEditor.value = "";
    currentStage = "";
    stageList.querySelectorAll("li").forEach(function (li) {
      li.classList.remove("active", "done");
    });
  }

  async function startRun(resume, resumeRun) {
    if (busy) return;
    setBusy(true);
    resetUI();
    setStatus(resume ? (resumeRun ? "断点续跑 " + resumeRun + "…" : "断点续跑启动…") : "启动流水线…", true);

    try {
      var resp = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          theme: $("theme").value.trim(),
          scenes: parseInt($("scenes").value, 10),
          resume: !!resume,
          resume_run: resumeRun || null,
          manual: $("manual").checked
        })
      });
      if (!resp.ok || !resp.body) throw new Error("HTTP " + resp.status);

      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buf = "";
      while (true) {
        var chunk = await reader.read();
        if (chunk.done) break;
        buf += decoder.decode(chunk.value, { stream: true });
        var idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          var block = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          var line = block.trim();
          if (line.indexOf("data: ") === 0) {
            try { handleEvent(JSON.parse(line.slice(6))); }
            catch (e) { /* 单条事件解析失败不中断流 */ }
          }
        }
      }
    } catch (e) {
      setStatus("❌ 连接中断：" + e.message, false);
    } finally {
      setBusy(false);
      // 结束后刷新可续跑状态与历史记录：新 run 已落盘，列表应即时更新
      refreshHealth();
      loadRuns();
      if (statusText.textContent.indexOf("✅") < 0 && statusText.textContent.indexOf("❌") < 0) {
        setStatus("流程结束", false);
      }
    }
  }

  runBtn.addEventListener("click", function () { startRun(false); });
  resumeBtn.addEventListener("click", function () { startRun(true); });
  $("theme").addEventListener("keydown", function (e) {
    if (e.key === "Enter") startRun();
  });
})();

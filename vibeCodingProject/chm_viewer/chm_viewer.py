#!/usr/bin/env python3
"""
CHM 文件 Web 查看器
带文件导入按钮的 Web 界面，支持选择、解压、浏览 .chm 文件。

用法:
    python3 chm_viewer.py [--port PORT]
"""

import argparse
import email
import email.parser
import html
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8899
DATA_DIR = ""  # 运行时设置

# ── HTML 模板 ──────────────────────────────────────────────────────────────────

LANDING_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CHM 查看器</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
         min-height: 100vh; display: flex; align-items: center; justify-content: center; color: #fff; }
  .card { background: rgba(255,255,255,0.08); backdrop-filter: blur(16px);
          border: 1px solid rgba(255,255,255,0.15); border-radius: 20px;
          padding: 48px; max-width: 520px; width: 90%; text-align: center; }
  h1 { font-size: 2rem; margin-bottom: 8px; }
  .sub { color: rgba(255,255,255,0.6); margin-bottom: 36px; font-size: 0.95rem; }
  .drop-zone { border: 2px dashed rgba(255,255,255,0.3); border-radius: 14px;
               padding: 40px 20px; margin-bottom: 24px; cursor: pointer;
               transition: all .2s; }
  .drop-zone:hover, .drop-zone.drag-over { border-color: #7c6cf0; background: rgba(124,108,240,0.1); }
  .drop-zone p { color: rgba(255,255,255,0.5); margin-top: 10px; font-size: 0.9rem; }
  .icon { font-size: 3rem; }
  input[type=file] { display: none; }
  .btn { display: inline-block; background: #7c6cf0; color: #fff; padding: 12px 32px;
         border-radius: 10px; border: none; font-size: 1rem; cursor: pointer;
         transition: background .2s; }
  .btn:hover { background: #5a4ed4; }
  .status { margin-top: 20px; color: rgba(255,255,255,0.7); font-size: 0.9rem; }
  .book-list { margin-top: 24px; text-align: left; }
  .book-list h3 { font-size: 0.85rem; color: rgba(255,255,255,0.5); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
  .book-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px;
               border-radius: 10px; margin-bottom: 6px; cursor: pointer; transition: background .15s; }
  .book-item:hover { background: rgba(255,255,255,0.1); }
  .book-item .name { flex: 1; font-size: 0.95rem; }
  .book-item .size { color: rgba(255,255,255,0.4); font-size: 0.8rem; }
</style>
</head>
<body>
<div class="card">
  <div class="icon">📖</div>
  <h1>CHM 查看器</h1>
  <p class="sub">选择 .chm 文件，在浏览器中直接阅读</p>

  <form id="upload-form" action="/upload" method="post" enctype="multipart/form-data">
    <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
      <p>📁 点击选择文件 或将 .chm 文件拖拽到此处</p>
    </div>
    <input type="file" id="file-input" name="chm_file" accept=".chm" onchange="onFileSelected(this)">
    <button type="submit" class="btn" id="open-btn" style="display:none">🚀 打开文件</button>
    <div class="status" id="file-name"></div>
  </form>

  <div class="book-list" id="book-list" style="display:none">
    <h3>📚 已解压的文档</h3>
    <div id="books"></div>
  </div>
</div>
<script>
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const openBtn = document.getElementById('open-btn');
const fileName = document.getElementById('file-name');

// 拖拽
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; onFileSelected(fileInput); }
});

function onFileSelected(input) {
  if (input.files.length) {
    const f = input.files[0];
    fileName.textContent = '已选择: ' + f.name + ' (' + (f.size / 1024 / 1024).toFixed(1) + ' MB)';
    openBtn.style.display = 'inline-block';
  }
}

// 加载已有文档列表
fetch('/api/books').then(r => r.json()).then(books => {
  if (books.length === 0) return;
  document.getElementById('book-list').style.display = 'block';
  const container = document.getElementById('books');
  books.forEach(b => {
    const div = document.createElement('div');
    div.className = 'book-item';
    div.innerHTML = '<span>📕</span><span class="name">' + b.name + '</span><span class="size">' + b.files + ' 文件</span>';
    div.onclick = () => window.location.href = '/book/' + b.id + '/';
    container.appendChild(div);
  });
});
</script>
</body>
</html>"""

NAV_FRAME_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  body {{ margin:0; font-family: -apple-system, sans-serif; }}
  .toolbar {{ background:#1e1e2e; color:#fff; padding:10px 20px; display:flex; align-items:center; gap:16px; position:fixed; top:0; left:0; right:0; z-index:999; }}
  .toolbar a {{ color:#a5b4fc; text-decoration:none; font-size:0.9rem; }}
  .toolbar a:hover {{ color:#fff; }}
  .toolbar .title {{ flex:1; font-size:0.95rem; }}
  iframe {{ border:none; width:100%; height:calc(100vh - 44px); margin-top:44px; }}
</style></head>
<body>
<div class="toolbar">
  <a href="/">🏠 首页</a>
  <span class="title">📖 {title}</span>
  <a href="/book/{book_id}/" target="content">📑 目录</a>
</div>
<iframe name="content" src="/book/{book_id}/{index_page}"></iframe>
</body></html>"""

DIR_INDEX_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>目录 - {title}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background:#0f0f1a; color:#e0e0e0; padding:24px; }}
  h1 {{ font-size:1.3rem; margin-bottom:20px; color:#a5b4fc; }}
  .folder {{ margin:8px 0; }}
  .folder-name {{ cursor:pointer; padding:8px 12px; background:rgba(165,180,252,0.08);
                  border-radius:8px; font-weight:600; display:flex; align-items:center; gap:8px; }}
  .folder-name:hover {{ background:rgba(165,180,252,0.15); }}
  .folder-content {{ margin-left:24px; display:none; }}
  .folder-content.open {{ display:block; }}
  .file-link {{ display:block; padding:6px 12px; color:#c4b5fd; text-decoration:none;
                border-radius:6px; margin:2px 0; font-size:0.9rem; }}
  .file-link:hover {{ background:rgba(196,181,253,0.1); color:#fff; }}
  .gallery-btn {{ display:inline-flex; align-items:center; gap:6px; padding:6px 14px;
                  background:rgba(124,108,240,0.2); color:#a5b4fc; border-radius:6px;
                  text-decoration:none; font-size:0.85rem; margin:4px 0 8px 0; transition:background .15s; }}
  .gallery-btn:hover {{ background:rgba(124,108,240,0.35); color:#fff; }}
  .stats {{ color:rgba(255,255,255,0.4); font-size:0.8rem; margin-bottom:20px; }}
</style></head>
<body>
<h1>📂 {title}</h1>
<div class="stats">共 {total_files} 个文件，{total_dirs} 个目录</div>
{tree_html}
<script>
document.querySelectorAll('.folder-name').forEach(el => {{
  el.onclick = () => {{
    const content = el.nextElementSibling;
    content.classList.toggle('open');
    el.querySelector('.arrow').textContent = content.classList.contains('open') ? '🔽' : '▶️';
  }};
}});
</script>
</body></html>"""

GALLERY_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>画廊 - {title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a14; color:#fff; font-family:-apple-system,sans-serif;
          overflow:hidden; height:100vh; display:flex; flex-direction:column; user-select:none; }}

  /* 顶部工具栏 */
  .topbar {{ background:rgba(20,20,40,0.9); backdrop-filter:blur(8px); padding:10px 20px;
             display:flex; align-items:center; gap:14px; flex-shrink:0; z-index:10; }}
  .topbar a {{ color:#a5b4fc; text-decoration:none; font-size:0.85rem; }}
  .topbar .info {{ flex:1; text-align:center; font-size:0.9rem; color:rgba(255,255,255,0.7); }}
  .topbar .info strong {{ color:#fff; }}

  /* 主图片区域 */
  .viewer {{ flex:1; position:relative; display:flex; align-items:center; justify-content:center;
             overflow:hidden; cursor:grab; }}
  .viewer:active {{ cursor:grabbing; }}
  .viewer img {{ max-width:92%; max-height:92%; object-fit:contain;
                 transition:opacity .25s, transform .25s; border-radius:4px;
                 box-shadow:0 8px 40px rgba(0,0,0,0.6); }}
  .viewer img.fade-in {{ opacity:1; transform:scale(1); }}
  .viewer img.fade-out {{ opacity:0; transform:scale(0.97); }}

  /* 左右箭头 */
  .arrow {{ position:absolute; top:50%; transform:translateY(-50%);
            width:52px; height:52px; border-radius:50%; border:none;
            background:rgba(255,255,255,0.08); color:#fff; font-size:1.4rem;
            cursor:pointer; display:flex; align-items:center; justify-content:center;
            transition:background .15s; z-index:5; backdrop-filter:blur(4px); }}
  .arrow:hover {{ background:rgba(124,108,240,0.5); }}
  .arrow:disabled {{ opacity:0.2; cursor:default; }}
  .arrow.left {{ left:16px; }}
  .arrow.right {{ right:16px; }}

  /* 底部缩略图条 */
  .thumbs {{ flex-shrink:0; background:rgba(20,20,40,0.9); backdrop-filter:blur(8px);
             padding:10px 16px; overflow-x:auto; overflow-y:hidden;
             display:flex; gap:6px; scrollbar-width:thin; scrollbar-color:#333 transparent; }}
  .thumbs::-webkit-scrollbar {{ height:4px; }}
  .thumbs::-webkit-scrollbar-thumb {{ background:#444; border-radius:2px; }}
  .thumb {{ width:64px; height:64px; flex-shrink:0; border-radius:6px; cursor:pointer;
            object-fit:cover; opacity:0.4; transition:opacity .15s, outline .15s;
            outline:2px solid transparent; }}
  .thumb:hover {{ opacity:0.8; }}
  .thumb.active {{ opacity:1; outline-color:#7c6cf0; }}

  /* 加载提示 */
  .loading {{ position:absolute; color:rgba(255,255,255,0.4); font-size:0.9rem; }}

  /* 主图可点击放大 */
  #main-img {{ cursor:zoom-in; }}

  /* 放大遮罩层 */
  .zoom-overlay {{ position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:100;
                   background:rgba(0,0,0,0.92); cursor:grab; overflow:hidden;
                   visibility:hidden; opacity:0; transition:opacity .2s, visibility .2s; }}
  .zoom-overlay.open {{ visibility:visible; opacity:1; }}
  .zoom-overlay.dragging {{ cursor:grabbing; }}
  .zoom-overlay img {{ position:absolute; top:0; left:0; transform-origin:0 0;
                       max-width:none; max-height:none; pointer-events:none; }}
  .zoom-hint {{ position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
                z-index:101; background:rgba(0,0,0,0.7); color:rgba(255,255,255,0.6);
                padding:6px 16px; border-radius:20px; font-size:0.8rem;
                pointer-events:none; opacity:0; transition:opacity .3s; }}
  .zoom-overlay.open ~ .zoom-hint {{ opacity:1; }}
  .zoom-close {{ position:fixed; top:16px; right:20px; z-index:102;
                 width:44px; height:44px; border-radius:50%; border:none;
                 background:rgba(255,255,255,0.1); color:#fff; font-size:1.3rem;
                 cursor:pointer; display:none; align-items:center; justify-content:center; }}
  .zoom-overlay.open ~ .zoom-close {{ display:flex; }}
  .zoom-close:hover {{ background:rgba(255,80,80,0.5); }}
  .zoom-level {{ position:fixed; top:20px; left:50%; transform:translateX(-50%);
                 z-index:102; background:rgba(0,0,0,0.6); color:rgba(255,255,255,0.5);
                 padding:4px 12px; border-radius:12px; font-size:0.75rem;
                 pointer-events:none; display:none; }}
  .zoom-overlay.open ~ .zoom-level {{ display:block; }}

  @media(max-width:600px) {{
    .arrow {{ width:40px; height:40px; font-size:1.1rem; }}
    .thumb {{ width:48px; height:48px; }}
  }}
</style></head>
<body>

<div class="topbar">
  <a href="/">🏠</a>
  <a href="/book/{book_id}/">📑 目录</a>
  <div class="info"><strong>{folder_name}</strong> &nbsp; <span id="counter">0 / 0</span></div>
  <a href="#" id="autoplay-btn" onclick="toggleAutoplay()">▶ 自动播放</a>
</div>

<div class="viewer" id="viewer">
  <button class="arrow left" id="prev-btn" onclick="prev()">‹</button>
  <img id="main-img" class="fade-in" alt="">
  <button class="arrow right" id="next-btn" onclick="next()">›</button>
  <div class="loading" id="loading">加载中…</div>
</div>

<div class="thumbs" id="thumbs"></div>

<!-- 放大遮罩 -->
<div class="zoom-overlay" id="zoom-overlay">
  <img id="zoom-img" alt="">
</div>
<button class="zoom-close" id="zoom-close" onclick="closeZoom()">✕</button>
<div class="zoom-level" id="zoom-level">100%</div>
<div class="zoom-hint" id="zoom-hint">滚轮缩放 · 拖拽平移 · 点击/Esc 关闭</div>

<script>
const images = {images_json};
const bookId = "{book_id}";
const startIdx = {start_idx};
let cur = startIdx;
let autoplay = null;

const img = document.getElementById('main-img');
const counter = document.getElementById('counter');
const thumbsEl = document.getElementById('thumbs');
const loading = document.getElementById('loading');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');

// 初始化缩略图
images.forEach((src, i) => {{
  const t = document.createElement('img');
  t.className = 'thumb';
  t.src = src;
  t.onclick = () => goTo(i);
  thumbsEl.appendChild(t);
}});

function goTo(i) {{
  if (i < 0 || i >= images.length) return;
  cur = i;
  img.classList.remove('fade-in');
  img.classList.add('fade-out');
  setTimeout(() => {{
    img.src = images[cur];
    img.onload = () => {{
      img.classList.remove('fade-out');
      img.classList.add('fade-in');
      loading.style.display = 'none';
    }};
    counter.textContent = (cur+1) + ' / ' + images.length;
    prevBtn.disabled = cur === 0;
    nextBtn.disabled = cur === images.length - 1;
    // 高亮缩略图
    document.querySelectorAll('.thumb').forEach((t,ti) => t.classList.toggle('active', ti===cur));
    // 滚动缩略图到可见
    const activeThumb = thumbsEl.children[cur];
    if (activeThumb) activeThumb.scrollIntoView({{behavior:'smooth', block:'nearest', inline:'center'}});
  }}, 120);
}}

function prev() {{ goTo(cur - 1); }}
function next() {{ goTo(cur + 1); }}

function toggleAutoplay() {{
  const btn = document.getElementById('autoplay-btn');
  if (autoplay) {{ clearInterval(autoplay); autoplay=null; btn.textContent='▶ 自动播放'; }}
  else {{ autoplay = setInterval(() => {{ cur >= images.length-1 ? goTo(0) : next(); }}, 2500); btn.textContent='⏸ 暂停'; }}
}}

// ── 放大查看 ──
let zoomOpen = false, zoomScale = 1, zoomX = 0, zoomY = 0;
let dragStartX = 0, dragStartY = 0, dragImgX = 0, dragImgY = 0, isDragging = false;
const overlay = document.getElementById('zoom-overlay');
const zoomImg = document.getElementById('zoom-img');
const zoomLevel = document.getElementById('zoom-level');

function openZoom() {{
  zoomOpen = true;
  // 先打开遮罩
  overlay.classList.add('open');
  document.getElementById('zoom-close').style.display = 'flex';
  document.getElementById('zoom-level').style.display = 'block';
  // 短暂显示提示
  const hint = document.getElementById('zoom-hint');
  hint.style.opacity = '1';
  setTimeout(() => hint.style.opacity = '0', 2500);

  function positionImg() {{
    const sw = window.innerWidth, sh = window.innerHeight;
    const iw = zoomImg.naturalWidth, ih = zoomImg.naturalHeight;
    if (!iw || !ih) return;
    const fit = Math.min(sw / iw, sh / ih);
    zoomScale = fit;
    zoomX = (sw - iw * fit) / 2;
    zoomY = (sh - ih * fit) / 2;
    applyZoom();
  }}

  zoomImg.src = images[cur];
  if (zoomImg.complete && zoomImg.naturalWidth > 0) {{
    requestAnimationFrame(positionImg);
  }} else {{
    zoomImg.onload = () => requestAnimationFrame(positionImg);
  }}
}}

function closeZoom() {{
  zoomOpen = false;
  overlay.classList.remove('open');
  overlay.classList.remove('dragging');
}}

function applyZoom() {{
  zoomImg.style.transform = `translate(${{zoomX}}px, ${{zoomY}}px) scale(${{zoomScale}})`;
  zoomLevel.textContent = Math.round(zoomScale * 100) + '%';
}}

function centerImage() {{
  const sw = window.innerWidth, sh = window.innerHeight;
  const iw = zoomImg.naturalWidth, ih = zoomImg.naturalHeight;
  if (!iw || !ih) return;
  const fit = Math.min(sw / iw, sh / ih, 1);
  zoomScale = fit;
  zoomX = (sw - iw * fit) / 2;
  zoomY = (sh - ih * fit) / 2;
  applyZoom();
}}

img.addEventListener('click', () => {{ if (!isDragging) openZoom(); }});

// 放大模式下滚轮缩放
overlay.addEventListener('wheel', e => {{
  e.preventDefault();
  const rect = overlay.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  // 缩放前鼠标对应的图片坐标
  const imgXBefore = (mx - zoomX) / zoomScale;
  const imgYBefore = (my - zoomY) / zoomScale;
  // 缩放
  const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
  zoomScale = Math.max(0.1, Math.min(zoomScale * factor, 20));
  // 保持鼠标位置不变
  zoomX = mx - imgXBefore * zoomScale;
  zoomY = my - imgYBefore * zoomScale;
  applyZoom();
}}, {{passive:false}});

// 放大模式下拖拽
overlay.addEventListener('mousedown', e => {{
  isDragging = true;
  dragStartX = e.clientX; dragStartY = e.clientY;
  dragImgX = zoomX; dragImgY = zoomY;
  overlay.classList.add('dragging');
  e.preventDefault();
}});
window.addEventListener('mousemove', e => {{
  if (!isDragging || !zoomOpen) return;
  zoomX = dragImgX + (e.clientX - dragStartX);
  zoomY = dragImgY + (e.clientY - dragStartY);
  applyZoom();
}});
window.addEventListener('mouseup', () => {{
  isDragging = false;
  overlay.classList.remove('dragging');
}});

// 点击遮罩背景关闭（非拖拽时）
overlay.addEventListener('click', e => {{
  if (e.target === overlay) closeZoom();
}});

// 双击切换缩放
overlay.addEventListener('dblclick', e => {{
  e.preventDefault();
  if (zoomScale > 1.05) {{
    // 回到适应
    const sw = window.innerWidth, sh = window.innerHeight;
    const iw = zoomImg.naturalWidth, ih = zoomImg.naturalHeight;
    const fit = Math.min(sw / iw, sh / ih, 1);
    zoomScale = fit;
    zoomX = (sw - iw * fit) / 2;
    zoomY = (sh - ih * fit) / 2;
  }} else {{
    // 放大到 2x，以点击位置为中心
    const rect = overlay.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const imgXBefore = (mx - zoomX) / zoomScale;
    const imgYBefore = (my - zoomY) / zoomScale;
    zoomScale = 2;
    zoomX = mx - imgXBefore * 2;
    zoomY = my - imgYBefore * 2;
  }}
  applyZoom();
}});

// 触摸双指缩放 (pinch zoom)
let lastPinchDist = 0;
overlay.addEventListener('touchstart', e => {{
  if (e.touches.length === 2) {{
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    lastPinchDist = Math.hypot(dx, dy);
  }} else if (e.touches.length === 1 && zoomOpen) {{
    isDragging = true;
    dragStartX = e.touches[0].clientX; dragStartY = e.touches[0].clientY;
    dragImgX = zoomX; dragImgY = zoomY;
  }}
}}, {{passive:true}});
overlay.addEventListener('touchmove', e => {{
  if (e.touches.length === 2) {{
    e.preventDefault();
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    const dist = Math.hypot(dx, dy);
    if (lastPinchDist > 0) {{
      const factor = dist / lastPinchDist;
      const cx = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const cy = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      const imgXBefore = (cx - zoomX) / zoomScale;
      const imgYBefore = (cy - zoomY) / zoomScale;
      zoomScale = Math.max(0.1, Math.min(zoomScale * factor, 20));
      zoomX = cx - imgXBefore * zoomScale;
      zoomY = cy - imgYBefore * zoomScale;
      applyZoom();
    }}
    lastPinchDist = dist;
  }} else if (e.touches.length === 1 && isDragging && zoomOpen) {{
    zoomX = dragImgX + (e.touches[0].clientX - dragStartX);
    zoomY = dragImgY + (e.touches[0].clientY - dragStartY);
    applyZoom();
  }}
}}, {{passive:false}});
overlay.addEventListener('touchend', () => {{ isDragging = false; lastPinchDist = 0; }});

// 键盘
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape' && zoomOpen) {{ closeZoom(); return; }}
  if (zoomOpen) {{
    if (e.key === '+' || e.key === '=') {{ zoomScale = Math.min(zoomScale*1.2,20); applyZoom(); }}
    if (e.key === '-') {{ zoomScale = Math.max(zoomScale/1.2,0.1); applyZoom(); }}
    if (e.key === '0') {{ openZoom(); }} // 重置缩放
    return;
  }}
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{ e.preventDefault(); prev(); }}
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {{ e.preventDefault(); next(); }}
  if (e.key === 'Enter' || e.key === 'z') {{ openZoom(); }}
}});

// 触摸滑动（画廊模式切换图片，放大模式下不触发翻页）
let touchX = 0;
const viewer = document.getElementById('viewer');
viewer.addEventListener('touchstart', e => {{ touchX = e.touches[0].clientX; }}, {{passive:true}});
viewer.addEventListener('touchend', e => {{
  if (zoomOpen) return;
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 40) {{ dx > 0 ? prev() : next(); }}
}});

// 鼠标滚轮（画廊模式翻页）
viewer.addEventListener('wheel', e => {{
  if (zoomOpen) return;
  e.preventDefault();
  e.deltaY > 0 || e.deltaX > 0 ? next() : prev();
}}, {{passive:false}});

// 启动
goTo(startIdx);
</script>
</body></html>"""


# ── 书籍管理 ──────────────────────────────────────────────────────────────────

books = {}  # id -> { name, dir, files, index }


def find_7z() -> str:
    """查找 7z/7za 命令"""
    for cmd in ["7z", "7za"]:
        path = shutil.which(cmd)
        if path:
            return path
    raise RuntimeError("未找到 7z/7za 命令，请先安装 p7zip: brew install p7zip")


def extract_chm(chm_path: str, filename: str) -> str:
    """解压 .chm，返回 book_id。使用 7z 解压。"""
    book_id = str(len(books) + 1)
    out_dir = os.path.join(DATA_DIR, book_id)
    os.makedirs(out_dir, exist_ok=True)

    sevenz = find_7z()
    result = subprocess.run(
        [sevenz, "x", chm_path, f"-o{out_dir}", "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise RuntimeError(f"解压失败: {result.stderr}")

    # 统计
    total_files = sum(len(f) for _, _, f in os.walk(out_dir))
    index_page = find_index(out_dir)

    books[book_id] = {
        "name": filename,
        "dir": out_dir,
        "files": total_files,
        "index": index_page,
    }
    return book_id


def find_index(root_dir: str) -> str:
    candidates = ["index.htm", "index.html", "default.htm", "default.html",
                  "toc.htm", "contents.htm"]
    for root, dirs, files in os.walk(root_dir):
        lower = {f.lower(): f for f in files}
        for c in candidates:
            if c.lower() in lower:
                return os.path.relpath(os.path.join(root, lower[c.lower()]), root_dir)
    return ""


IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')


def collect_images(root_dir: str, book_id: str, sub_dir: str = "") -> list:
    """收集目录下所有图片，返回 URL 列表。"""
    base = os.path.join(root_dir, sub_dir) if sub_dir else root_dir
    urls = []
    for root, dirs, files in os.walk(base):
        dirs.sort()
        for fn in sorted(files):
            if fn.lower().endswith(IMAGE_EXTS):
                rel = os.path.relpath(os.path.join(root, fn), root_dir)
                urls.append("/book/" + book_id + "/" + urllib.parse.quote(rel))
    return urls


def build_tree_html(root_dir: str, book_id: str) -> str:
    """生成可交互的目录树 HTML，含画廊模式入口。"""
    lines = []
    total_dirs = 0

    def walk(d, prefix=""):
        nonlocal total_dirs
        entries = sorted(os.listdir(d))
        dirs_list = [e for e in entries if os.path.isdir(os.path.join(d, e)) and not e.startswith('#') and not e.startswith('$')]
        files_list = [e for e in entries if os.path.isfile(os.path.join(d, e))
                      and not e.startswith('#') and not e.startswith('$')
                      and (e.lower().endswith(('.htm', '.html')) or e.lower().endswith(IMAGE_EXTS))]

        # 当前目录图片数
        img_count = sum(1 for f in files_list if f.lower().endswith(IMAGE_EXTS))
        if img_count > 0:
            rel_sub = os.path.relpath(d, root_dir)
            sub_param = urllib.parse.quote(rel_sub) if rel_sub != '.' else ''
            lines.append(f'<a class="gallery-btn" href="/book/{book_id}/gallery?sub={sub_param}">🖼️ 画廊模式（{img_count} 张）</a>')

        for fn in files_list:
            rel = os.path.relpath(os.path.join(d, fn), root_dir)
            safe = urllib.parse.quote(rel)
            display = html.escape(fn)
            icon = "🖼️" if fn.lower().endswith(IMAGE_EXTS) else "📄"
            lines.append(f'<a class="file-link" href="/book/{book_id}/{safe}" target="_parent">{icon} {display}</a>')

        for dn in dirs_list:
            total_dirs += 1
            sub = os.path.join(d, dn)
            display = html.escape(dn)
            lines.append(f'<div class="folder">')
            lines.append(f'  <div class="folder-name"><span class="arrow">▶️</span> 📁 {display}</div>')
            lines.append(f'  <div class="folder-content">')
            walk(sub, prefix + dn + "/")
            lines.append(f'  </div></div>')

    walk(root_dir)
    return "\n".join(lines), total_dirs


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class CHMHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # 静默日志

    def do_GET(self):
        path = urllib.parse.unquote(self.path)

        if path == "/" or path == "":
            self.send_html(200, LANDING_HTML)

        elif path == "/api/books":
            import json
            data = [{"id": k, "name": v["name"], "files": v["files"]} for k, v in books.items()]
            self.send_json(200, data)

        elif path.startswith("/book/"):
            # 分离 query string
            qs = ""
            if "?" in path:
                path, qs = path.split("?", 1)
            qs_dict = dict(urllib.parse.parse_qsl(qs))

            parts = path.split("/", 3)  # ['', 'book', id, ...]
            if len(parts) < 3:
                self.send_error(404)
                return
            book_id = parts[2]
            if book_id not in books:
                self.send_error(404, "文档不存在")
                return
            book = books[book_id]

            # 目录页
            if len(parts) == 3 or parts[3] == "":
                tree_html, total_dirs = build_tree_html(book["dir"], book_id)
                total_files = sum(len(f) for _, _, f in os.walk(book["dir"]))
                page = DIR_INDEX_HTML.format(
                    title=html.escape(book["name"]),
                    total_files=total_files, total_dirs=total_dirs,
                    tree_html=tree_html
                )
                self.send_html(200, page)
                return

            # 画廊模式
            if parts[3] == "gallery":
                import json
                sub = qs_dict.get("sub", "")
                imgs = collect_images(book["dir"], book_id, sub)
                folder_display = sub if sub else book["name"]
                page = GALLERY_HTML.format(
                    title=html.escape(book["name"]),
                    book_id=book_id,
                    folder_name=html.escape(folder_display),
                    images_json=json.dumps(imgs, ensure_ascii=False),
                    start_idx=0
                )
                self.send_html(200, page)
                return

            # 导航框架 (首次打开 index)
            if parts[3] == "__nav__":
                page = NAV_FRAME_HTML.format(
                    title=html.escape(book["name"]),
                    book_id=book_id,
                    index_page=book["index"] or ""
                )
                self.send_html(200, page)
                return

            # 静态文件
            rel = parts[3]
            fpath = os.path.join(book["dir"], rel)
            fpath = os.path.normpath(fpath)
            if not fpath.startswith(os.path.normpath(book["dir"])):
                self.send_error(403, "禁止访问")
                return
            if os.path.isfile(fpath):
                self.send_file(fpath)
            else:
                self.send_error(404, f"文件不存在: {rel}")

        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path

        if path == "/upload":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_error(400, "需要 multipart/form-data")
                return

            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 500 * 1024 * 1024:
                self.send_error(413, "文件过大（最大 500MB）")
                return

            # 读取原始 body，用 email 模块解析 multipart
            raw_body = self.rfile.read(content_length)
            # 构造完整 MIME 消息供 email 解析
            headers_str = f"Content-Type: {content_type}\r\n\r\n"
            msg = email.message_from_bytes(headers_str.encode() + raw_body)

            filename = None
            file_data = None
            for part in msg.walk():
                disp = part.get("Content-Disposition", "")
                if "form-data" in disp and 'name="chm_file"' in disp:
                    # 从 Content-Disposition 提取文件名
                    import re
                    m = re.search(r'filename="([^"]+)"', disp)
                    if m:
                        filename = m.group(1)
                    file_data = part.get_payload(decode=True)
                    break

            if not filename or not file_data:
                self.send_error(400, "未选择文件")
                return

            # 保存到临时文件
            tmp_path = os.path.join(DATA_DIR, "_upload_tmp.chm")
            with open(tmp_path, "wb") as f:
                f.write(file_data)

            try:
                book_id = extract_chm(tmp_path, filename)
                self.send_response(302)
                self.send_header("Location", f"/book/{book_id}/__nav__")
                self.end_headers()
            except Exception as e:
                self.send_html(500, f"<h1>错误</h1><p>{html.escape(str(e))}</p><a href='/'>返回首页</a>")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            self.send_error(404)

    # ── 响应工具 ──

    def send_html(self, code, content):
        data = content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, obj):
        import json
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    MIME_MAP = {
        ".htm": "text/html; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif", ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
        ".txt": "text/plain; charset=utf-8",
    }

    def send_file(self, fpath):
        ext = os.path.splitext(fpath)[1].lower()
        mime = self.MIME_MAP.get(ext, "application/octet-stream")
        with open(fpath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    global DATA_DIR, PORT
    parser = argparse.ArgumentParser(description="📖 CHM 文件 Web 查看器")
    parser.add_argument("--port", type=int, default=8899, help="端口 (默认 8899)")
    args = parser.parse_args()
    PORT = args.port

    DATA_DIR = tempfile.mkdtemp(prefix="chm_web_")

    import webbrowser
    url = f"http://127.0.0.1:{PORT}"
    print(f"📖 CHM Web 查看器")
    print(f"   地址: {url}")
    print(f"   数据: {DATA_DIR}")
    print(f"   按 Ctrl+C 退出\n")

    webbrowser.open(url)

    server = HTTPServer(("127.0.0.1", PORT), CHMHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 已退出")
    finally:
        server.server_close()
        shutil.rmtree(DATA_DIR, ignore_errors=True)
        print("🧹 临时文件已清理")


if __name__ == "__main__":
    main()

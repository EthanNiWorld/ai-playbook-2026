#!/usr/bin/env python3
"""
html2video.py — 将任意 HTML 页面动画录制为 PPT 兼容的 MP4 视频

原理：Chrome Headless CDP 逐帧截图 + ffmpeg 编码 H.264 MP4

用法：
  # 录制本地 HTTP 服务上的页面（默认 1920x1080, 12fps, 15秒）
  python html2video.py http://localhost:8090/demo.html -o demo.mp4

  # 自定义分辨率、帧率、时长
  python html2video.py http://localhost:8090/demo.html -o demo.mp4 -w 1280 -h 720 --fps 24 -d 10

  # 录制 file:// 本地文件
  python html2video.py file:///path/to/page.html -o output.mp4

  # 自定义帧质量和背景色（用于 padding）
  python html2video.py http://localhost:8090/demo.html -o demo.mp4 --quality 95 --bg 0x000000

  # 跳过 ffmpeg 编码（只保留截图帧）
  python html2video.py http://localhost:8090/demo.html -o demo.mp4 --frames-only

依赖：
  - Google Chrome（自动检测路径）
  - ffmpeg（编码 MP4，系统需安装）
  - websocket-client（pip install websocket-client）

注意：
  - macOS 自带 Chrome 路径已内置，Linux/Windows 需通过 --chrome 指定
  - 页面加载后默认等待 3 秒再开始录制，可通过 --wait 调整
  - 输出视频编码为 H.264 + yuv420p，PowerPoint / Keynote / WPS 均兼容
"""
import argparse
import subprocess
import json
import time
import os
import sys
import shutil
import base64
import random
from pathlib import Path
from urllib.request import urlopen

# ── Chrome 自动检测 ──
CHROME_SEARCH_PATHS = [
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    # Linux
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    # Windows (常见路径，用户可通过 --chrome 覆盖)
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome(custom_path=None):
    if custom_path and os.path.exists(custom_path):
        return custom_path
    for p in CHROME_SEARCH_PATHS:
        if os.path.exists(p):
            return p
    return None


def find_tab(debug_port, url_hint=""):
    """从 CDP 调试端口找到目标页面的 WebSocket URL"""
    resp = json.loads(urlopen(f"http://localhost:{debug_port}/json").read())
    # 优先匹配 URL 中包含关键词的 page tab
    if url_hint:
        for t in resp:
            if t.get("type") == "page" and url_hint in t.get("url", ""):
                return t["webSocketDebuggerUrl"]
    # 回退：第一个 page tab（跳过 extension background pages）
    for t in resp:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError(f"No page tab found on debug port {debug_port}")


def capture_frames(chrome, url, output_dir, width, height, fps, duration,
                   wait, quality, debug_port):
    """启动 Chrome Headless，通过 CDP WebSocket 逐帧截图"""
    import websocket

    total_frames = int(fps * duration)
    url_hint = Path(url.split("?")[0]).stem  # 用文件名做 tab 匹配关键词

    # 清理帧目录
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # 启动 Chrome
    proc = subprocess.Popen([
        chrome, "--headless=new", "--disable-gpu",
        f"--remote-debugging-port={debug_port}",
        f"--window-size={width},{height}",
        "--hide-scrollbars", "--no-sandbox",
        "--remote-allow-origins=*",
        "--disable-extensions", "--no-first-run",
        "--disable-background-networking",
        "--disable-software-rasterizer",
        url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"  Chrome pid={proc.pid}, 等待 {wait}s 页面加载...")
    time.sleep(wait)

    # 连接 CDP
    ws_url = find_tab(debug_port, url_hint)
    ws = websocket.create_connection(ws_url, timeout=5)
    print(f"  CDP 连接成功，开始录制 {total_frames} 帧 ({duration}s @ {fps}fps)...")

    msg_id = 1
    captured = 0
    start = time.time()

    for i in range(total_frames):
        try:
            msg = json.dumps({
                "id": msg_id,
                "method": "Page.captureScreenshot",
                "params": {"format": "jpeg", "quality": quality},
            })
            ws.send(msg)

            # 读取响应，跳过 CDP 事件消息
            data = None
            while True:
                try:
                    raw = ws.recv()
                    resp_data = json.loads(raw)
                    if resp_data.get("id") == msg_id:
                        data = resp_data
                        break
                except websocket.WebSocketTimeoutException:
                    break

            if data and "result" in data and "data" in data["result"]:
                img = base64.b64decode(data["result"]["data"])
                with open(os.path.join(output_dir, f"frame_{captured:04d}.jpg"), "wb") as f:
                    f.write(img)
                captured += 1

            msg_id += 1

        except Exception:
            # 断线重连
            try:
                ws.close()
                ws = websocket.create_connection(ws_url, timeout=5)
            except Exception:
                pass

        # 精确帧间隔
        elapsed = time.time() - start
        target = (i + 1) / fps
        sleep_t = target - elapsed
        if sleep_t > 0:
            time.sleep(sleep_t)

        # 进度报告
        if (i + 1) % (fps * 3) == 0:
            pct = (i + 1) * 100 // total_frames
            print(f"  [{pct:3d}%] {i+1}/{total_frames} 帧 (成功 {captured})")

    ws.close()
    proc.terminate()
    proc.wait()

    wall_time = time.time() - start
    print(f"  录制完成: {captured}/{total_frames} 帧, 耗时 {wall_time:.1f}s")
    return captured


def encode_mp4(frames_dir, output, width, height, fps, bg_color, crf, preset):
    """用 ffmpeg 将帧序列编码为 H.264 MP4"""
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={bg_color}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%04d.jpg"),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", preset, "-crf", str(crf),
        "-movflags", "+faststart",
        output,
    ]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0, r.stderr.decode()[-400:] if r.returncode != 0 else ""


def main():
    parser = argparse.ArgumentParser(
        description="将 HTML 页面动画录制为 PPT 兼容的 MP4 视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="HTML 页面 URL（http:// 或 file://）")
    parser.add_argument("-o", "--output", required=True, help="输出 MP4 文件路径")
    parser.add_argument("-w", "--width", type=int, default=1920, help="视口宽度（默认 1920）")
    parser.add_argument("--height", type=int, default=1080, help="视口高度（默认 1080）")
    parser.add_argument("--fps", type=int, default=12, help="帧率（默认 12）")
    parser.add_argument("-d", "--duration", type=float, default=15, help="录制时长/秒（默认 15）")
    parser.add_argument("--wait", type=float, default=3, help="页面加载等待时间/秒（默认 3）")
    parser.add_argument("--quality", type=int, default=88, help="JPEG 质量 1-100（默认 88）")
    parser.add_argument("--bg", default="0x000000", help="padding 背景色（默认 0x000000 黑色）")
    parser.add_argument("--crf", type=int, default=18, help="ffmpeg CRF 值，越小质量越高（默认 18）")
    parser.add_argument("--preset", default="slow", choices=["ultrafast","fast","medium","slow","veryslow"],
                        help="ffmpeg 编码速度预设（默认 slow）")
    parser.add_argument("--chrome", default=None, help="Chrome 可执行文件路径（默认自动检测）")
    parser.add_argument("--port", type=int, default=None, help="CDP 调试端口（默认随机）")
    parser.add_argument("--frames-only", action="store_true", help="只截图不编码（保留帧目录）")
    parser.add_argument("--keep-frames", action="store_true", help="编码后保留帧目录")

    args = parser.parse_args()

    # 校验依赖
    chrome = find_chrome(args.chrome)
    if not chrome:
        print("❌ 未找到 Chrome，请通过 --chrome 指定路径"); sys.exit(1)

    if not args.frames_only:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        if r.returncode != 0:
            print("❌ 未找到 ffmpeg，请安装: brew install ffmpeg"); sys.exit(1)

    try:
        import websocket  # noqa: F401
    except ImportError:
        print("❌ 缺少 websocket-client，请安装: pip install websocket-client"); sys.exit(1)

    debug_port = args.port or random.randint(19300, 19400)
    frames_dir = f"/tmp/html2video_frames_{debug_port}"

    print(f"📹 html2video")
    print(f"   URL:      {args.url}")
    print(f"   输出:     {args.output}")
    print(f"   分辨率:   {args.width}x{args.height}")
    print(f"   帧率:     {args.fps} fps")
    print(f"   时长:     {args.duration}s")
    print(f"   Chrome:   {chrome}")
    print(f"   CDP端口:  {debug_port}")
    print()

    # Step 1-3: 截图
    captured = capture_frames(
        chrome, args.url, frames_dir,
        args.width, args.height, args.fps, args.duration,
        args.wait, args.quality, debug_port,
    )

    if captured == 0:
        print("❌ 未捕获到任何帧，请检查 URL 和网络连接")
        shutil.rmtree(frames_dir, ignore_errors=True)
        sys.exit(1)

    if args.frames_only:
        print(f"\n✅ 帧已保存到: {frames_dir}")
        print(f"   手动编码: ffmpeg -framerate {args.fps} -i {frames_dir}/frame_%04d.jpg -c:v libx264 -pix_fmt yuv420p output.mp4")
        return

    # Step 4: 编码
    print(f"\n[编码] ffmpeg → {args.output}")
    ok, err = encode_mp4(frames_dir, args.output, args.width, args.height,
                         args.fps, args.bg, args.crf, args.preset)
    if ok:
        sz = os.path.getsize(args.output) / (1024 * 1024)
        dur = captured / args.fps
        print(f"\n✅ 视频已生成: {args.output}")
        print(f"   📦 {sz:.1f} MB | ⏱ {dur:.1f}s | 📐 {args.width}x{args.height} | 🎞 {args.fps}fps")
        print(f"   💡 PPT 插入: 插入 → 视频 → 此设备上的视频 → 选择此文件")
    else:
        print(f"❌ ffmpeg 编码失败:\n{err}")
        sys.exit(1)

    # 清理
    if not args.keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
        print("🧹 临时帧已清理")
    else:
        print(f"📁 帧保留在: {frames_dir}")


if __name__ == "__main__":
    main()

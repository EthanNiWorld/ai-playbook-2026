#!/usr/bin/env python3
"""Record mining-safety-ai-demo.html as MP4 — robust v2 using CDP via HTTP."""
import subprocess, json, time, os, sys, shutil, base64
from urllib.request import urlopen, Request

HTML_URL = "http://localhost:8090/mining-safety-ai-demo.html"
OUTPUT_DIR = "/tmp/mineguard_frames"
OUTPUT_VIDEO = "/Users/nizhen/Documents/ai-knowledge-base/alibaba-ai-hub/ai-industry-solutions/mining-safety-ai-demo-20260716.mp4"
W, H = 1920, 1080
FPS = 12
DURATION = 19  # just under the 20s loop
TOTAL = FPS * DURATION

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DBG_PORT = 19334

# Clean
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR)
print(f"[1/4] Frames dir ready")

# Launch Chrome
proc = subprocess.Popen([
    CHROME, "--headless=new", "--disable-gpu",
    f"--remote-debugging-port={DBG_PORT}",
    f"--window-size={W},{H}", "--hide-scrollbars",
    "--no-sandbox", "--remote-allow-origins=*",
    "--disable-extensions", "--no-first-run",
    "--disable-background-networking",
    "--disable-software-rasterizer",
    HTML_URL,
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"[2/4] Chrome launched (pid={proc.pid})")
time.sleep(3)  # wait for page + fonts to load

# Find our tab
def get_tab_ws():
    resp = json.loads(urlopen(f"http://localhost:{DBG_PORT}/json").read())
    for t in resp:
        if t.get("type") == "page" and "mining-safety" in t.get("url", ""):
            return t["webSocketDebuggerUrl"]
    for t in resp:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page tab found")

# Use websocket with timeout per recv
import websocket
ws_url = get_tab_ws()
ws = websocket.create_connection(ws_url, timeout=5)
print(f"[3/4] Capturing {TOTAL} frames at {FPS}fps ({DURATION}s)...")

msg_id = 1
captured = 0
start = time.time()

for i in range(TOTAL):
    try:
        msg = json.dumps({"id": msg_id, "method": "Page.captureScreenshot",
                          "params": {"format": "jpeg", "quality": 88}})
        ws.send(msg)

        # Read responses until we get our answer
        while True:
            try:
                raw = ws.recv()
                data = json.loads(raw)
                if data.get("id") == msg_id:
                    break
            except websocket.WebSocketTimeoutException:
                # Skip this frame
                data = None
                break

        if data and "result" in data and "data" in data["result"]:
            img = base64.b64decode(data["result"]["data"])
            with open(os.path.join(OUTPUT_DIR, f"frame_{captured:04d}.jpg"), "wb") as f:
                f.write(img)
            captured += 1

        msg_id += 1
    except Exception as e:
        # Reconnect if needed
        try:
            ws.close()
            ws = websocket.create_connection(ws_url, timeout=5)
        except:
            pass

    # Timing: sleep until next frame slot
    elapsed = time.time() - start
    target = (i + 1) / FPS
    sleep_t = target - elapsed
    if sleep_t > 0:
        time.sleep(sleep_t)

    if (i + 1) % (FPS * 3) == 0:
        print(f"  ... {i+1}/{TOTAL} frames ({captured} captured)")

ws.close()
proc.terminate()
proc.wait()
print(f"  Done: {captured}/{TOTAL} frames captured in {time.time()-start:.1f}s")

# Encode
print(f"[4/4] Encoding MP4...")
actual_dur = captured / FPS
cmd = [
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(OUTPUT_DIR, "frame_%04d.jpg"),
    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x080C18",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-preset", "slow", "-crf", "18",
    "-movflags", "+faststart",
    OUTPUT_VIDEO,
]
r = subprocess.run(cmd, capture_output=True)
if r.returncode == 0:
    sz = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print(f"\n✅ Video: {OUTPUT_VIDEO}")
    print(f"   {sz:.1f} MB | {actual_dur:.1f}s | {W}x{H} | {FPS}fps")
else:
    print(f"❌ ffmpeg error: {r.stderr.decode()[-300:]}")

shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
print("🧹 Cleaned up")

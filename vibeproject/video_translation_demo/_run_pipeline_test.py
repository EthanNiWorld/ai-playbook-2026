"""
端到端测试脚本：直接调用 VideoDubbingPipeline（不通过 Gradio UI）
"""
import os
import sys
import glob
from datetime import datetime

# 把项目目录加入 path
PROJECT_DIR = "/Users/nizhen/Documents/ai-knowledge-base/vibeproject/video_translation_demo"
sys.path.insert(0, PROJECT_DIR)

# 列出 testfile 中的文件
testfile_dir = os.path.join(PROJECT_DIR, "testfile")
print(f"=== testfile 内容 ===")
for f in os.listdir(testfile_dir):
    full = os.path.join(testfile_dir, f)
    print(f"  {f}  ({os.path.getsize(full)} bytes)")

# 找视频和音频（过滤掉之前的输出产物，只用原始素材）
video_files = [
    f for f in glob.glob(os.path.join(testfile_dir, "*.mp4"))
    if "_dubbed_" not in os.path.basename(f) and "_en_full_" not in os.path.basename(f)
]
vocal_files = [
    f for f in glob.glob(os.path.join(testfile_dir, "*.mp3"))
    if "_dubbed_" not in os.path.basename(f) and "_en_full_" not in os.path.basename(f)
]

video_path = video_files[0] if video_files else None
vocal_path = vocal_files[0] if vocal_files else None

print(f"\n=== 选用 ===")
print(f"  video: {os.path.basename(video_path)}")
print(f"  vocal: {os.path.basename(vocal_path)}")

if not video_path or not vocal_path:
    print("❌ 缺少素材")
    sys.exit(1)

# 验证 API key 是否纯 ASCII
API_KEY = "sk-7e41d5d2f93e4d569f136428fa36d7e6"
print(f"\n=== API Key 校验 ===")
print(f"  starts_with_sk-: {API_KEY.startswith('sk-')}")
print(f"  length: {len(API_KEY)}")
try:
    API_KEY.encode("latin-1")
    print("  ASCII: OK")
except UnicodeEncodeError as e:
    print(f"  ❌ Non-ASCII at {e.start}-{e.end}")
    sys.exit(1)

# 导入并运行 pipeline
print(f"\n=== Pipeline 调用 ===")
from video_dubbing_zh2en import VideoDubbingPipeline

pipeline = VideoDubbingPipeline(api_key=API_KEY, region="intl")
print(f"  base_url: {pipeline.base_url}")

output_video, asr_text, trans_text = pipeline.run(
    video_path=video_path,
    vocal_mp3_path=vocal_path,
)

print(f"\n=== ✅ 全部完成 ===")
print(f"  output: {output_video}")
print(f"  output size: {os.path.getsize(output_video)} bytes")
print(f"\n=== ASR 识别结果 ===\n{asr_text}")
print(f"\n=== 中英翻译对照 ===\n{trans_text}")

# 复制输出到 testfile 目录（避免 temp 目录被系统清理丢失）
# 命名规则：{源视频stem}_dubbed_{YYYYMMDD}.{ext}
# 重名时自动加版本号：v1.0, v1.1, v1.2, ...
import shutil

date_str = datetime.now().strftime("%Y%m%d")
video_stem = os.path.splitext(os.path.basename(video_path))[0]


def _versioned_path(directory, stem, suffix, ext):
    """
    生成带版本号的唯一文件名。
    - 首次: {stem}_{suffix}.mp4
    - 重名: {stem}_{suffix}_v1.0.mp4, v1.1, v1.2, ...
    """
    base_name = f"{stem}_{suffix}.{ext}"
    candidate = os.path.join(directory, base_name)
    if not os.path.exists(candidate):
        return candidate
    for major in range(1, 100):
        for minor in range(10):
            ver_name = f"{stem}_{suffix}_v{major}.{minor}.{ext}"
            candidate = os.path.join(directory, ver_name)
            if not os.path.exists(candidate):
                return candidate
    raise RuntimeError("版本号用尽")


final_path = _versioned_path(testfile_dir, video_stem, f"dubbed_{date_str}", "mp4")
shutil.copy2(output_video, final_path)
print(f"\n=== 输出已复制到 testfile 目录 ===")
print(f"  → {final_path}")
print(f"  size: {os.path.getsize(final_path)} bytes")

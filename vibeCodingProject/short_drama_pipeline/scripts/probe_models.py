"""北京节点模型可用性探测：验证配额申请清单中各模型在本 workspace 的可用状态。

探测项（均以最小成本试探）：
1. qwen4-max：OpenAI 兼容 chat 一次（max_tokens=20）
2. 图像模型候选（qwen-image-3.0-pro → 2.1-pro → 2.1-turbo → wan2.7-image-pro）：
   提交最小文生图任务，task_id 返回即视为可用
3. 视频模型候选（wan3.0-video → prime → wan2.7-i2v/t2v）：提交最小文生视频任务
4. wan2.7-videoedit：仅校验模型名是否可提交（探测用 t2v 相同路径 + videoedit 模型，
   提交一次最小任务）

输出各模型可用性结论表，供配额申请答复口径参考。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bailian_client import BailianAsyncClient, ModelNotAvailableError
from llm_client import Qwen4MaxClient

def probe_llm():
    print("\n[1/4] qwen4-max（OpenAI 兼容端点）")
    if not config.OPENAI_BASE_URL:
        print("  ❌ 未配置 OPENAI_BASE_URL")
        return False
    try:
        c = Qwen4MaxClient()
        reply = c.chat([{"role": "user", "content": "回复两个字：可用"}], max_tokens=20)
        print(f"  ✅ 可用，模型 {c.model}，回复: {reply.strip()[:30]}")
        return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False

def probe_image(client):
    print("\n[2/4] 图像模型候选（qwen-image 同步接口 / wan-image 异步接口）")
    for model in [config.IMAGE_MODEL] + config.IMAGE_MODEL_FALLBACKS:
        try:
            url, used = client.text2image(
                "一只橘猫，极简风格",
                [model],
                size="1024*1024",
            )
            print(f"  ✅ {used}: 已生成图片 URL={url[:60]}...")
            return used
        except ModelNotAvailableError as e:
            print(f"  ❌ {model}: 不可用（{str(e)[:100]}）")
        except Exception as e:
            print(f"  ⚠️ {model}: 其他错误（{str(e)[:120]}）")
    return None

def probe_video(client):
    print("\n[3/4] 视频模型候选（文生视频最小任务）")
    results = {}
    for model in list(dict.fromkeys([config.VIDEO_MODEL] + config.VIDEO_MODEL_FALLBACKS)):
        for reso, dur in [("480P", 5), ("480P", 2), ("720P", 5)]:
            try:
                task_id, _ = client._post_task({
                    "_kind": "video",
                    "model": model,
                    "input": {"prompt": "一只橘猫在窗台上晒太阳，镜头缓慢推近"},
                    "parameters": {"resolution": reso, "duration": dur},
                })
                print(f"  ✅ {model}@{reso}/{dur}s: task_id={task_id[:18]}...")
                results[model] = (task_id, reso, dur)
                break
            except ModelNotAvailableError as e:
                print(f"  ❌ {model}: 不可用（{str(e)[:100]}）")
                break
            except Exception as e:
                msg = str(e)[:130]
                print(f"  ⚠️ {model}@{reso}/{dur}s: {msg}")
                continue
    return results

def probe_videoedit(client, video_task_results):
    print("\n[4/4] wan2.7-videoedit（生成式编辑，提交最小任务）")
    # 用一个可公开访问的短样例视频测试模型是否可提交
    try:
        task_id, _ = client._post_task({
            "_kind": "video",
            "model": config.VIDEOEDIT_MODEL,
            "input": {
                "prompt": "把画面风格调整为雨夜霓虹",
                "video_url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20260402/fwjpqf/wan2.7-videoedit-input.mp4",
            },
            "parameters": {"resolution": "480P"},
        })
        print(f"  ✅ {config.VIDEOEDIT_MODEL}: 任务已受理 task_id={task_id[:18]}...")
        return task_id
    except Exception as e:
        print(f"  ⚠️ {config.VIDEOEDIT_MODEL}: {str(e)[:150]}（可能样例视频 URL 失效，或模型未开通）")
        return None

if __name__ == "__main__":
    if not config.check_credentials():
        sys.exit(1)
    print(f"原生端点: {config.NATIVE_BASE_URL}")
    client = BailianAsyncClient()
    probe_llm()
    probe_image(client)
    video_ok = probe_video(client)
    probe_videoedit(client, video_ok)
    print("\n=== 探测完成 ===")
    print("提示: 已受理的探测任务会正常执行产生少量费用；结果 URL 24h 有效。")

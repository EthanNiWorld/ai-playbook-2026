import os
import time
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置API URL（新加坡地域）
dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
# 如果需要使用北京地域，请替换为以下URL:
# dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# 获取API密钥
api_key = os.getenv("DASHSCOPE_API_KEY_WAN")
if not api_key:
    raise ValueError("请设置DASHSCOPE_API_KEY_WAN环境变量")

# 配置关闭内容安全检测(绿网)的headers
DISABLE_INSPECTION_HEADERS = {
    'X-DashScope-DataInspection': '{"input":"disable", "output":"disable"}'
}

# 视频生成参数
# 如果需要图片到视频，加上这条以及修改model name以及去掉img_url=IMG_URL注释 IMG_URL = "https://cdn77-pic.xvideos-cdn.com/videos/thumbs169poster/4e/9d/f6/4e9df642593c9a96848d07afb0be62b3/4e9df642593c9a96848d07afb0be62b3.30.jpg"
# AUDIO_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250925/ozwpvi/rap.mp3"  # 可选的音频URL


def sample_async_call_i2v():
    """异步调用图像到视频转换API"""
    try:
        print("正在发起视频生成请求...")
        
        # 异步调用视频合成API，添加关闭绿网的headers
        rsp = VideoSynthesis.async_call(
            api_key=api_key,
            model='wan2.7-t2v',
            prompt='极致特写，微距摄影，奥黛丽赫本的脸庞与身体，大量*****。',

            #img_url=IMG_URL,
            # audio_url=AUDIO_URL,  # 可选，不提供则自动生成背景音乐
            resolution="720P",
            duration=15,
            prompt_extend=True,
            watermark=False,
            negative_prompt="",
            seed=12345,
            headers=DISABLE_INSPECTION_HEADERS  # 关键：添加关闭绿网的header
        )
        
        print("API响应:", rsp)
        
        if rsp.status_code == HTTPStatus.OK:
            task_id = rsp.output.task_id
            print(f"任务已成功提交，task_id: {task_id}")
            
            # 定期轮询任务状态直到完成
            while True:
                # fetch方法不支持headers参数，只在async_call时使用
                status = VideoSynthesis.fetch(
                    task=rsp,
                    api_key=api_key
                )
                
                if status.status_code == HTTPStatus.OK:
                    task_status = status.output.task_status
                    print(f"当前任务状态: {task_status}")
                    
                    if task_status in ["SUCCEEDED", "FAILED"]:
                        break
                else:
                    print(f"获取任务状态失败，状态码: {status.status_code}, 错误码: {status.code}, 消息: {status.message}")
                    break
                
                # 等待一段时间后再次检查
                time.sleep(30)
            
            # 获取最终结果
            if task_status == "SUCCEEDED":
                # wait方法也不支持headers参数，只在async_call时使用
                result = VideoSynthesis.wait(
                    task=rsp,
                    api_key=api_key
                )
                
                if result.status_code == HTTPStatus.OK:
                    video_url = result.output.video_url
                    print(f"视频生成成功！下载地址: {video_url}")
                    return video_url
                else:
                    print(f"获取结果失败，状态码: {result.status_code}, 错误码: {result.code}, 消息: {result.message}")
            elif task_status == "FAILED":
                print(f"任务执行失败，错误信息: {status.output.message}")
        else:
            print(f"API调用失败，状态码: {rsp.status_code}, 错误码: {rsp.code}, 消息: {rsp.message}")
            
    except Exception as e:
        print(f"发生异常: {str(e)}")
        raise


if __name__ == '__main__':
    sample_async_call_i2v()
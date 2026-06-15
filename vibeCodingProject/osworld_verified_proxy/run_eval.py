"""对指定模型跑 OSWorld-Verified 单步 action prediction 评测。"""
import argparse
import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI

import config


# DashScope 百炼定价（¥ / 1M tokens），用于成本估算
# 以 2026-06-12 官方公示价格为基线；Max 若仍处 5 折期，请手动调低。
PRICING_CNY = {
    "qwen3.7-plus": {"input": 2.0, "output": 8.0},
    "qwen3.7-max-2026-06-08": {"input": 12.0, "output": 36.0},
}

# 1024x768 PNG 在 Qwen vision encoder 下的 token 估算（单张约 1500–2500 tokens）
# 这里取保守中位数 2000 tokens 作为成本估算依据。
IMAGE_TOKEN_ESTIMATE = 2000


SYSTEM_PROMPT = """You are a GUI automation agent. Given a screenshot and a task instruction, predict the single next action to take.

Use the following action space:
- click(x, y): click at screen coordinates (x, y)
- double_click(x, y): double click at screen coordinates (x, y)
- type(text): type the given text
- hotkey(key): press a keyboard shortcut (e.g., "enter", "ctrl+c")
- scroll(x, y, direction): scroll up/down at coordinates (x, y), direction is "up" or "down"
- drag(start_x, start_y, end_x, end_y): drag from start coordinates to end coordinates

Return ONLY a JSON object with this exact schema:
{
  "action": "click",
  "target": "brief description of the UI element",
  "coords": [x, y],
  "value": "optional text or key",
  "reasoning": "one sentence explaining why this action is appropriate"
}

Rules:
1. Coordinates must be within the image dimensions.
2. Choose the action most likely to make progress on the task.
3. If the task appears already completed, return action "done".
"""


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_action_json(text: str) -> dict[str, Any]:
    """从模型输出中解析 JSON，兼容 ```json 代码块包裹。"""
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # 如果模型只输出部分 JSON，尝试提取第一个 { ... } 块
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        clean = clean[start : end + 1]
    return json.loads(clean)


def estimate_cost_cny(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING_CNY.get(model)
    if not pricing:
        return 0.0
    return (
        input_tokens * pricing["input"] / 1_000_000
        + output_tokens * pricing["output"] / 1_000_000
    )


def _eval_one_task(client: OpenAI, model: str, task: dict, idx: int, total: int) -> dict:
    """评测单个任务，支持并发调用。"""
    task_id = task["id"]
    instruction = task["instruction"]
    image_path = task["image"]

    # 支持相对路径（相对于项目根目录）和绝对路径
    if not os.path.isabs(image_path):
        image_path = os.path.join(config.PROJECT_ROOT, image_path)

    if not os.path.exists(image_path):
        print(f"[{idx}/{total}] ⚠️ 跳过 {task_id}: 截图不存在 {image_path}")
        return {
            "id": task_id,
            "instruction": instruction,
            "domain": task.get("domain", "unknown"),
            "predicted": {"action": "error", "reasoning": "Image not found"},
            "latency_seconds": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_cny": 0.0,
        }

    b64_image = encode_image(image_path)
    user_text = f"Task: {instruction}\n\nPredict the next action based on the current screenshot."

    start_time = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
            top_p=config.TOP_P,
        )
        latency = time.time() - start_time

        raw_text = resp.choices[0].message.content or ""
        usage = resp.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        # 如果 API 没返回 usage，用估算兜底
        if input_tokens == 0:
            input_tokens = IMAGE_TOKEN_ESTIMATE + len(SYSTEM_PROMPT) // 4 + len(user_text) // 4
        if output_tokens == 0:
            output_tokens = len(raw_text) // 4

        cost = estimate_cost_cny(model, input_tokens, output_tokens)

        try:
            predicted = parse_action_json(raw_text)
        except json.JSONDecodeError as e:
            predicted = {
                "action": "error",
                "target": "",
                "coords": [0, 0],
                "value": "",
                "reasoning": f"Failed to parse JSON: {e}",
                "raw": raw_text,
            }

        result = {
            "id": task_id,
            "instruction": instruction,
            "domain": task.get("domain", "unknown"),
            "predicted": predicted,
            "latency_seconds": round(latency, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_cny": round(cost, 6),
        }

    except Exception as e:
        result = {
            "id": task_id,
            "instruction": instruction,
            "domain": task.get("domain", "unknown"),
            "predicted": {"action": "error", "reasoning": str(e)},
            "latency_seconds": round(time.time() - start_time, 2),
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_cny": 0.0,
        }

    action = result["predicted"].get("action", "N/A")
    target = result["predicted"].get("target", "")
    print(f"[{idx}/{total}] {task_id:20s} -> {action:12s} | {target[:40]:40s} | ¥{result['cost_cny']:.4f}")
    return result


def run_eval(model: str, tasks_file: str, output_dir: str, workers: int = 1) -> str:
    if not config.DASHSCOPE_API_KEY:
        raise RuntimeError("请先设置环境变量 DASHSCOPE_API_KEY")

    client = OpenAI(
        api_key=config.DASHSCOPE_API_KEY,
        base_url=config.DASHSCOPE_BASE_URL,
    )

    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    print(f"开始评测模型: {model}")
    print(f"任务数: {len(tasks)} | 并发数: {workers}")
    print("-" * 60)

    results = []
    if workers <= 1:
        results = [_eval_one_task(client, model, task, i + 1, len(tasks)) for i, task in enumerate(tasks)]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_eval_one_task, client, model, task, i + 1, len(tasks)): task["id"]
                for i, task in enumerate(tasks)
            }
            for future in as_completed(futures):
                results.append(future.result())
        # 按原始顺序排序，方便对比
        results.sort(key=lambda r: next((i for i, t in enumerate(tasks) if t["id"] == r["id"]), 0))

    total_cost_cny = sum(r["cost_cny"] for r in results)
    total_input_tokens = sum(r["input_tokens"] for r in results)
    total_output_tokens = sum(r["output_tokens"] for r in results)

    summary = {
        "model": model,
        "total_tasks": len(tasks),
        "completed_tasks": len([r for r in results if r["predicted"].get("action") != "error"]),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cost_cny": round(total_cost_cny, 4),
        "tasks": results,
    }

    safe_model_name = model.replace("/", "_")
    output_path = os.path.join(output_dir, f"{safe_model_name}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print(f"评测完成: {model}")
    print(f"总任务数: {summary['total_tasks']}")
    print(f"成功解析: {summary['completed_tasks']}")
    print(f"总 tokens: {total_input_tokens + total_output_tokens}")
    print(f"预估成本: ¥{summary['total_cost_cny']:.4f}")
    print(f"结果保存: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="OSWorld-Verified 单步 action prediction 评测")
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3.7-plus",
        help="测试模型名，如 qwen3.7-plus 或 qwen3.7-max-2026-06-08",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default=config.TASKS_FILE,
        help=f"任务清单 JSON 路径，默认 {config.TASKS_FILE}",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=config.RESULTS_DIR,
        help=f"结果输出目录，默认 {config.RESULTS_DIR}",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并发请求数，默认 1；扩展到 100 个样本时可设为 5–10 加速",
    )
    args = parser.parse_args()

    run_eval(args.model, args.tasks, args.output_dir, args.workers)


if __name__ == "__main__":
    main()

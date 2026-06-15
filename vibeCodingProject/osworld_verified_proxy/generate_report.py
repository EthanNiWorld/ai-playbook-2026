"""读取 results/*.json 生成 HTML 评测报告。"""
import argparse
import json
import os
from datetime import datetime
from typing import Any

import config


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSWorld-Verified 单步代理测试报告</title>
    <style>
        :root {{
            --bg: #f8f9fa;
            --card: #ffffff;
            --text: #212529;
            --muted: #6c757d;
            --border: #dee2e6;
            --primary: #2563eb;
            --success: #198754;
            --danger: #dc3545;
            --warning: #ffc107;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{ margin-bottom: 8px; }}
        .subtitle {{
            color: var(--muted);
            margin-bottom: 24px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card h3 {{
            margin: 0 0 12px 0;
            font-size: 14px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .metric small {{
            font-size: 14px;
            color: var(--muted);
            font-weight: 400;
        }}
        table {{
            width: 100%;
            background: var(--card);
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 24px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}
        th {{
            background: #f1f3f5;
            font-weight: 600;
            font-size: 14px;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .tag-success {{ background: #d1e7dd; color: #0f5132; }}
        .tag-danger {{ background: #f8d7da; color: #842029; }}
        .tag-warning {{ background: #fff3cd; color: #664d03; }}
        .action {{ font-family: monospace; font-size: 13px; }}
        .reasoning {{
            color: var(--muted);
            font-size: 13px;
            margin-top: 4px;
        }}
        .conclusions {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .conclusions h2 {{ margin-top: 0; }}
        .conclusions ul {{ padding-left: 20px; }}
        .conclusions li {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OSWorld-Verified 单步代理测试报告</h1>
        <div class="subtitle">生成时间：{generated_at}</div>

        <div class="grid">
            <div class="card">
                <h3>测试任务数</h3>
                <div class="metric">{total_tasks}<small> 个</small></div>
            </div>
            <div class="card">
                <h3>测试模型数</h3>
                <div class="metric">{model_count}<small> 个</small></div>
            </div>
            <div class="card">
                <h3>总花费</h3>
                <div class="metric">¥{total_cost:.4f}</div>
            </div>
            <div class="card">
                <h3>视觉模型</h3>
                <div class="metric">{vision_model_count}<small> / {model_count}</small></div>
            </div>
        </div>

        <h2>模型概览</h2>
        <table>
            <thead>
                <tr>
                    <th>模型</th>
                    <th>视觉支持</th>
                    <th>成功任务</th>
                    <th>总 Tokens</th>
                    <th>预估成本</th>
                    <th>平均延迟</th>
                </tr>
            </thead>
            <tbody>
                {model_rows}
            </tbody>
        </table>

        <h2>逐任务结果</h2>
        <table>
            <thead>
                <tr>
                    <th>任务</th>
                    <th>领域</th>
                    {task_model_headers}
                </tr>
            </thead>
            <tbody>
                {task_rows}
            </tbody>
        </table>

        <div class="conclusions">
            <h2>测试结论</h2>
            <ul>
                <li><strong>qwen3.7-max（无日期后缀）</strong>不支持视觉输入，所有带截图的任务均返回 400 错误，无法用于 GUI Agent 评测。</li>
                <li><strong>qwen3.7-plus</strong> 与 <strong>qwen3.7-max-2026-06-08</strong> 在 13 个单步任务上表现一致，均能正确处理弹窗、滑块验证码、隐藏目标滚动等场景。</li>
                <li>两个模型的共同短板：遇到错误提示时，都优先点击 username 字段而非红色高亮的 password 字段。</li>
                <li>Max-0608 成本约为 Plus 的 5.3 倍，但在本轻量测试中没有展现出明显的能力优势。</li>
                <li>当前测试为合成/简化截图，结论仅适用于「单步 action prediction」代理；真实 OSWorld-Verified 分数需在真实桌面环境中跑完整 harness。</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""


def load_result(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_action(pred: dict) -> str:
    action = pred.get("action", "")
    target = pred.get("target", "")
    coords = pred.get("coords", [])
    end_coords = pred.get("end_coords", [])
    value = pred.get("value", "")

    if action == "error":
        return f'<span class="tag tag-danger">error</span>'

    parts = [f"<strong>{action}</strong>"]
    if target:
        parts.append(f"{target}")
    if coords:
        parts.append(f"({coords[0]}, {coords[1]})")
    if end_coords:
        parts.append(f"→ ({end_coords[0]}, {end_coords[1]})")
    if value:
        parts.append(f"value={value}")
    return "<br>".join(parts)


def format_reasoning(pred: dict) -> str:
    reasoning = pred.get("reasoning", "")
    if not reasoning or reasoning.startswith("Failed to parse"):
        return ""
    return f'<div class="reasoning">{reasoning}</div>'


def generate(results_dir: str, output_path: str):
    result_files = sorted([
        f for f in os.listdir(results_dir)
        if f.endswith(".json") and not f.startswith("_")
    ])

    results = []
    for fname in result_files:
        path = os.path.join(results_dir, fname)
        data = load_result(path)
        results.append(data)

    if not results:
        raise RuntimeError(f"在 {results_dir} 中未找到结果文件")

    # 取第一个结果的任务列表作为基准（假设所有模型任务相同）
    base_tasks = results[0].get("tasks", [])
    total_tasks = len(base_tasks)

    # 模型概览行
    model_rows = []
    total_cost = 0.0
    vision_model_count = 0
    for data in results:
        model = data.get("model", "unknown")
        completed = data.get("completed_tasks", 0)
        total = data.get("total_tasks", 0)
        in_tokens = data.get("total_input_tokens", 0)
        out_tokens = data.get("total_output_tokens", 0)
        cost = data.get("total_cost_cny", 0.0)
        total_cost += cost

        tasks_list = data.get("tasks", [])
        latencies = [t.get("latency_seconds", 0) for t in tasks_list if t.get("latency_seconds", 0) > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        has_vision = completed > 0
        if has_vision:
            vision_model_count += 1

        support_tag = '<span class="tag tag-success">支持</span>' if has_vision else '<span class="tag tag-danger">不支持</span>'
        success_rate = f"{completed}/{total}"

        model_rows.append(
            f"<tr>"
            f"<td><strong>{model}</strong></td>"
            f"<td>{support_tag}</td>"
            f"<td>{success_rate}</td>"
            f"<td>{in_tokens + out_tokens:,}</td>"
            f"<td>¥{cost:.4f}</td>"
            f"<td>{avg_latency:.2f}s</td>"
            f"</tr>"
        )

    # 逐任务表头
    task_model_headers = "".join(f"<th>{data.get('model', 'model')}</th>" for data in results)

    # 逐任务行
    task_rows = []
    for task_idx in range(total_tasks):
        task_id = base_tasks[task_idx]["id"]
        domain = base_tasks[task_idx].get("domain", "")
        instruction = base_tasks[task_idx].get("instruction", "")

        cells = []
        for data in results:
            tasks = data.get("tasks", [])
            if task_idx >= len(tasks):
                cells.append("<td>-</td>")
                continue
            pred = tasks[task_idx].get("predicted", {})
            cells.append(
                f"<td class=\"action\">{format_action(pred)}{format_reasoning(pred)}</td>"
            )

        task_rows.append(
            f"<tr>"
            f'<td title="{instruction}"><strong>{task_id}</strong></td>'
            f"<td>{domain}</td>"
            f"{''.join(cells)}"
            f"</tr>"
        )

    html = HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tasks=total_tasks,
        model_count=len(results),
        total_cost=total_cost,
        vision_model_count=vision_model_count,
        model_rows="\n".join(model_rows),
        task_model_headers=task_model_headers,
        task_rows="\n".join(task_rows),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="生成 OSWorld-Verified 测试 HTML 报告")
    parser.add_argument(
        "--results-dir",
        type=str,
        default=config.RESULTS_DIR,
        help=f"结果目录，默认 {config.RESULTS_DIR}",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(config.RESULTS_DIR, "report.html"),
        help="输出 HTML 路径",
    )
    args = parser.parse_args()

    generate(args.results_dir, args.output)


if __name__ == "__main__":
    main()

"""对比两个模型的 OSWorld-Verified 单步 action prediction 结果。"""
import argparse
import json
from difflib import SequenceMatcher


def similar(a: str, b: str) -> float:
    """计算两个字符串的相似度，用于 action/target 的模糊匹配。"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def load_result(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_action_signature(pred: dict) -> str:
    """从预测结果中提取便于对比的签名。"""
    action = pred.get("action", "")
    target = pred.get("target", "")
    value = pred.get("value", "")
    coords = pred.get("coords", [])
    parts = [action]
    if target:
        parts.append(target)
    if value:
        parts.append(value)
    if coords and len(coords) == 2:
        parts.append(f"({coords[0]},{coords[1]})")
    return " | ".join(parts)


def compare(path_a: str, path_b: str):
    data_a = load_result(path_a)
    data_b = load_result(path_b)

    model_a = data_a.get("model", "model_a")
    model_b = data_b.get("model", "model_b")

    tasks_a = {t["id"]: t for t in data_a.get("tasks", [])}
    tasks_b = {t["id"]: t for t in data_b.get("tasks", [])}
    common_ids = sorted(set(tasks_a.keys()) & set(tasks_b.keys()))

    print("=" * 80)
    print(f"模型对比: {model_a}  vs  {model_b}")
    print("=" * 80)
    print(f"{'Task ID':<20} {'Domain':<15} {'A Action':<35} {'B Action':<35} Match")
    print("-" * 80)

    match_count = 0
    fuzzy_match_count = 0
    total = len(common_ids)

    for task_id in common_ids:
        task_a = tasks_a[task_id]
        task_b = tasks_b[task_id]
        pred_a = task_a.get("predicted", {})
        pred_b = task_b.get("predicted", {})

        sig_a = extract_action_signature(pred_a)
        sig_b = extract_action_signature(pred_b)

        action_a = pred_a.get("action", "")
        action_b = pred_b.get("action", "")
        target_a = pred_a.get("target", "")
        target_b = pred_b.get("target", "")

        # 严格匹配：action 相同
        strict_match = action_a == action_b and action_a not in ("", "error")
        # 模糊匹配：action 相同且 target 相似度 > 0.5
        fuzzy_match = strict_match and similar(target_a, target_b) > 0.5

        if strict_match:
            match_count += 1
        if fuzzy_match:
            fuzzy_match_count += 1

        marker = "✓" if fuzzy_match else ("~" if strict_match else "✗")
        print(
            f"{task_id:<20} {task_a.get('domain', '?'):<15} "
            f"{sig_a[:34]:<35} {sig_b[:34]:<35} {marker}"
        )

    print("-" * 80)
    cost_a = data_a.get("total_cost_cny", 0.0)
    cost_b = data_b.get("total_cost_cny", 0.0)
    print(f"{model_a}: 成本 ¥{cost_a:.4f}, 成功任务 {data_a.get('completed_tasks', 0)}/{data_a.get('total_tasks', 0)}")
    print(f"{model_b}: 成本 ¥{cost_b:.4f}, 成功任务 {data_b.get('completed_tasks', 0)}/{data_b.get('total_tasks', 0)}")
    print(f"共同任务数: {total}")
    print(f"Action 严格一致: {match_count}/{total} ({match_count / total * 100:.1f}%)")
    print(f"Action + Target 模糊一致: {fuzzy_match_count}/{total} ({fuzzy_match_count / total * 100:.1f}%)")
    print("=" * 80)

    # 输出一个简短的结论倾向
    if fuzzy_match_count == total:
        print("结论：两个模型在所有 demo 任务上的判断高度一致。")
    elif fuzzy_match_count >= total * 0.7:
        print("结论：两个模型大部分判断一致，可在真实 OSWorld 截图上进一步验证差异任务。")
    else:
        print("结论：两个模型判断分歧较大，建议检查具体任务的推理过程。")


def main():
    parser = argparse.ArgumentParser(description="对比两个模型的 OSWorld-Verified 评测结果")
    parser.add_argument("--model_a", type=str, required=True, help="模型 A 的结果 JSON 路径")
    parser.add_argument("--model_b", type=str, required=True, help="模型 B 的结果 JSON 路径")
    args = parser.parse_args()

    compare(args.model_a, args.model_b)


if __name__ == "__main__":
    main()

"""短剧批量生产流水线 · 北京节点 demo 入口。

用法：
  python run_demo.py                        # 默认跑一遍完整流水线（1 场景，全自动）
  python run_demo.py --theme "古装甜宠" --scenes 2
  python run_demo.py --manual               # 打磨模式：分镜/图像/验收/视频四步后人工确认
  python run_demo.py --pressure 30          # 附加 30 秒任务状态查询压测（观测限流）
  python run_demo.py --ims-real             # IMS 走真实 SDK（需开通+凭证）
  python run_demo.py --resume               # 断点续跑：从最新未完成 run 的 checkpoint 继续
"""
import argparse
import json
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from pipeline import ShortDramaPipeline
from task_manager import TaskManager


def find_resumable_run():
    """找最新的未完成 run 目录（有 checkpoint 且未标记 finished）。"""
    best = None
    runs = sorted(glob.glob(os.path.join(config.OUTPUT_DIR, "run_*")),
                  key=os.path.getmtime)  # 按修改时间取最新，不依赖命名规则
    for d in runs:
        ckpt_path = os.path.join(d, "checkpoint.json")
        if not os.path.isfile(ckpt_path):
            continue
        try:
            with open(ckpt_path) as f:
                ckpt = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if ckpt.get("storyboard") and not ckpt.get("finished"):
            best = d
    return best


def make_cli_confirm():
    """CLI 打磨确认回调：回车=继续 / e=分镜改好了按新内容继续 / r=重新生成本步 / n=终止。

    返回 (action, edited)：action ∈ continue/redo/abort；分镜步骤的 e 会重新
    读入 storyboard.json（人工编辑后的内容），后续图片/视频按新分镜走。
    """
    def confirm(step, payload):
        while True:
            opts = "回车=继续下一步"
            if step == "storyboard":
                opts += "  e=已改好storyboard.json，按新分镜继续"
            if step != "video":  # 视频任务已计费，不提供重做（终止后可手动删 checkpoint 里的 video_tasks 再续跑）
                opts += "  r=重新生成本步"
            opts += "  n=终止（可 --resume 续跑）"
            cmd = input(f"  👉 {opts} > ").strip().lower()
            if cmd in ("", "y", "c", "continue"):
                return "continue", None
            if cmd == "r" and step != "video":
                return "redo", None
            if cmd == "n":
                return "abort", None
            if cmd == "e" and step == "storyboard":
                path = payload["path"]
                try:
                    with open(path) as f:
                        board = json.load(f)
                    if not isinstance(board.get("scenes"), list) or not board["scenes"]:
                        raise ValueError("scenes 不能为空")
                    return "continue", board
                except (json.JSONDecodeError, ValueError, OSError) as e:
                    print(f"  ⚠️ 读取 {os.path.basename(path)} 失败：{e}，请改好后重试")
            else:
                print("  ⚠️ 无法识别的指令，请重新输入")
    return confirm


def main():
    parser = argparse.ArgumentParser(description="短剧生产流水线 demo（北京节点）")
    parser.add_argument("--theme", default="都市逆袭短剧")
    parser.add_argument("--scenes", type=int, default=1)
    parser.add_argument("--ims-real", action="store_true", help="IMS 走真实 SDK 调用")
    parser.add_argument("--resume", action="store_true",
                        help="断点续跑：从最新未完成 run 的 checkpoint 继续（忽略 --theme/--scenes）")
    parser.add_argument("--manual", action="store_true",
                        help="打磨模式：分镜/图像/验收/视频四个步骤后暂停，人工确认后再继续（可重做/终止）")
    parser.add_argument("--pressure", type=int, default=0, metavar="SECONDS",
                        help="流水线完成后附加 N 秒状态查询压测（验证 500 QPS 需求）")
    parser.add_argument("--qps", type=float, default=10,
                        help="轮询目标 QPS（压测模式下也作为爬坡上限）")
    args = parser.parse_args()

    if not config.check_credentials():
        sys.exit(1)

    resume_dir = None
    if args.resume:
        resume_dir = find_resumable_run()
        if resume_dir is None:
            print("❌ 没有可续跑的任务（未找到未完成的 checkpoint）")
            sys.exit(1)
        print(f"♻️ 断点续跑: {resume_dir}")

    p = ShortDramaPipeline(
        theme=args.theme, num_scenes=args.scenes,
        ims_real=args.ims_real, target_qps=args.qps,
        resume_dir=resume_dir,
        confirm_cb=make_cli_confirm() if args.manual else None,
    )
    p.run()

    if args.pressure > 0:
        p.tm.pressure_test(duration_s=args.pressure)


if __name__ == "__main__":
    main()

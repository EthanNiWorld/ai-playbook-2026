#!/usr/bin/env python3
"""Run native vLLM workload sweep, plots, and TPM/TTFT/TPOT recommendations."""

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vllm-bin", default="/root/.conda/envs/qwen3.8/bin/vllm")
    parser.add_argument("--server-wrapper", default="/data/vllm_sweep_server.sh")
    parser.add_argument("--reset-script", default="/data/vllm_sweep_reset.sh")
    parser.add_argument("--model-path", default="/data/Qwen3.8-27B-NVFP4")
    parser.add_argument("--model-name", default="Qwen3.8-27B-NVFP4")
    parser.add_argument("--tokenizer", default="")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--tensor-parallel-size", type=int, default=2)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--max-num-batched-tokens", type=int, default=32768)
    parser.add_argument("--max-num-seqs", type=int, default=32)
    parser.add_argument("--gpu-memory-utilization", default="0.90")
    parser.add_argument("--kv-cache-dtype", default="fp8")
    parser.add_argument("--spec-tokens", type=int, default=3)
    parser.add_argument("--input-len", type=int, default=8192)
    parser.add_argument("--output-len", type=int, default=512)
    parser.add_argument("--num-prompts", type=int, default=40)
    parser.add_argument("--workload-iters", type=int, default=8)
    parser.add_argument("--num-runs", type=int, default=1)
    parser.add_argument("--warmup-num-prompts", type=int, default=4)
    parser.add_argument("--seed", type=int, default=23000)
    parser.add_argument("--output-dir", default="/data/benchmark-results/native-sweep")
    parser.add_argument("--experiment-name", default="")
    parser.add_argument("--experiment-dir", default="")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--skip-plots", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--balanced-ratio", type=float, default=0.99)
    return parser.parse_args()


def run_command(command, env, log_path=None):
    if log_path:
        with open(log_path, "w") as log:
            return subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    return subprocess.run(command, env=env)


def build_commands(args, experiment_dir):
    tokenizer = args.tokenizer or args.model_path
    base_url = f"http://{args.host}:{args.port}"
    serve_cmd = (
        f"{args.server_wrapper} serve {args.model_path} "
        f"--served-model-name {args.model_name} "
        f"--host {args.host} --port {args.port} "
        f"--tensor-parallel-size {args.tensor_parallel_size} "
        f"--max-model-len {args.max_model_len} "
        f"--max-num-batched-tokens {args.max_num_batched_tokens} "
        f"--max-num-seqs {args.max_num_seqs} "
        f"--gpu-memory-utilization {args.gpu_memory_utilization} "
        f"--kv-cache-dtype {args.kv_cache_dtype} "
        f"--reasoning-parser qwen3 "
        f"--speculative-config.method mtp "
        f"--speculative-config.num_speculative_tokens {args.spec_tokens} -O2"
    )
    bench_cmd = (
        f"vllm bench serve --backend openai-chat "
        f"--base-url {base_url} --endpoint /v1/chat/completions "
        f"--model {args.model_name} --tokenizer {tokenizer} "
        f"--dataset-name random --input-len {args.input_len} "
        f"--output-len {args.output_len} --num-prompts {args.num_prompts} "
        f"--ignore-eos --seed {args.seed} "
        f"--percentile-metrics ttft,tpot,itl,e2el "
        f"--metric-percentiles 50,95,99"
    )
    command = [
        args.vllm_bin, "bench", "sweep", "serve_workload",
        "--serve-cmd", serve_cmd,
        "--bench-cmd", bench_cmd,
        "--after-bench-cmd", args.reset_script,
        "--workload-var", "max_concurrency",
        "--workload-iters", str(args.workload_iters),
        "--num-runs", str(args.num_runs),
        "--warmup-num-prompts", str(args.warmup_num_prompts),
        "--continue-on-error",
        "--server-ready-timeout", "600",
        "--output-dir", str(experiment_dir.parent),
        "--experiment-name", experiment_dir.name,
    ]
    if args.resume:
        command.append("--resume")
    return command


def generate_plots(args, experiment_dir):
    plots = [
        ("max_concurrency", "median_ttft_ms", "ttft_curve"),
        ("max_concurrency", "median_tpot_ms", "tpot_curve"),
        ("max_concurrency", "total_token_throughput", "throughput_curve"),
        ("total_token_throughput", "median_ttft_ms", "latency_throughput"),
    ]
    env = os.environ.copy()
    env["PATH"] = f"{Path(args.vllm_bin).parent}:/usr/local/bin:/usr/bin:/bin"
    for var_x, var_y, name in plots:
        command = [
            args.vllm_bin, "bench", "sweep", "plot", str(experiment_dir),
            "--var-x", var_x, "--var-y", var_y, "--fig-name", name,
        ]
        subprocess.run(command, env=env, check=True)
    subprocess.run(
        [
            args.vllm_bin, "bench", "sweep", "plot_pareto", str(experiment_dir),
            "--label-by", "max_concurrency,max_num_seqs,max_num_batched_tokens",
        ],
        env=env,
        check=True,
    )


def summarize(experiment_dir, balanced_ratio):
    rows = []
    for result_file in experiment_dir.rglob("summary.json"):
        with open(result_file) as handle:
            rows.extend(json.load(handle))
    if not rows:
        raise RuntimeError(f"No summary.json found under {experiment_dir}")

    for row in rows:
        duration_minutes = row["duration"] / 60
        row["input_tpm"] = row["total_input_tokens"] / duration_minutes
        row["output_tpm"] = row["total_output_tokens"] / duration_minutes
        row["total_tpm"] = row["total_token_throughput"] * 60
        row["sla_pass"] = row["p50_ttft_ms"] <= 8000 and row["p95_ttft_ms"] <= 30000
    rows.sort(key=lambda row: row["max_concurrency"])

    raw_max = max(rows, key=lambda row: row["total_tpm"])
    sla_rows = [row for row in rows if row["sla_pass"]]
    sla_max = max(sla_rows, key=lambda row: row["total_tpm"]) if sla_rows else None
    balanced = None
    if sla_max:
        candidates = [
            row for row in sla_rows
            if row["total_tpm"] >= sla_max["total_tpm"] * balanced_ratio
        ]
        balanced = min(candidates, key=lambda row: row["p50_ttft_ms"])

    fields = [
        "max_concurrency", "completed", "failed", "duration",
        "p50_ttft_ms", "p95_ttft_ms", "p50_tpot_ms", "p95_tpot_ms",
        "request_throughput", "input_tpm", "output_tpm", "total_tpm",
        "spec_decode_acceptance_rate", "sla_pass",
    ]
    with open(experiment_dir / "summary.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    def compact(row):
        if row is None:
            return None
        return {
            "max_concurrency": row["max_concurrency"],
            "total_tpm": round(row["total_tpm"], 2),
            "p50_ttft_ms": round(row["p50_ttft_ms"], 2),
            "p95_ttft_ms": round(row["p95_ttft_ms"], 2),
            "p50_tpot_ms": round(row["p50_tpot_ms"], 2),
            "sla_pass": row["sla_pass"],
        }

    recommendations = {
        "total_tpm_semantics": "All successful requests are included, regardless of TTFT SLA.",
        "raw_max_tpm": compact(raw_max),
        "sla_max_tpm": compact(sla_max),
        "balanced_lowest_ttft_within_ratio": compact(balanced),
        "balanced_ratio_of_sla_max": balanced_ratio,
    }
    with open(experiment_dir / "recommendations.json", "w") as handle:
        json.dump(recommendations, handle, indent=2)

    print("concurrency,total_tpm,ttft_p50_ms,tpot_p50_ms,sla_pass")
    for row in rows:
        print(
            f"{row['max_concurrency']},{row['total_tpm']:.2f},"
            f"{row['p50_ttft_ms']:.2f},{row['p50_tpot_ms']:.2f},{row['sla_pass']}"
        )
    print(json.dumps(recommendations, indent=2))
    return recommendations


def main():
    args = parse_args()
    if args.experiment_dir:
        experiment_dir = Path(args.experiment_dir)
    else:
        name = args.experiment_name or time.strftime("nvfp4-tp2-mtp3-%Y%m%d-%H%M%S")
        experiment_dir = Path(args.output_dir) / name

    if not args.summary_only:
        for path in (args.vllm_bin, args.server_wrapper, args.reset_script, args.model_path):
            if not Path(path).exists():
                raise FileNotFoundError(path)
        command = build_commands(args, experiment_dir)
        env = os.environ.copy()
        env["PATH"] = f"{Path(args.vllm_bin).parent}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        experiment_dir.parent.mkdir(parents=True, exist_ok=True)
        result = run_command(command, env, experiment_dir.parent / f"{experiment_dir.name}-driver.log")
        if result.returncode != 0:
            raise RuntimeError(f"Sweep failed; see {experiment_dir.parent / f'{experiment_dir.name}-driver.log'}")
        if not args.skip_plots:
            generate_plots(args, experiment_dir)

    summarize(experiment_dir, args.balanced_ratio)


if __name__ == "__main__":
    main()

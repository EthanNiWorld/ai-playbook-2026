#!/usr/bin/env python3
"""Qwen3.8 vLLM benchmark matrix with TPM, cache and GPU metrics."""

import argparse
import csv
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--metrics-ports", default="8000,8001")
    parser.add_argument("--model", default="Qwen3.8-27B-FP8")
    parser.add_argument("--tokenizer", default="/data/Qwen3.8-27B-FP8")
    parser.add_argument("--vllm-bin", default="/root/.conda/envs/qwen3.8/bin/vllm")
    parser.add_argument("--result-dir", default="/data/benchmark-results/matrix")
    parser.add_argument("--label", required=True)
    parser.add_argument("--dataset-name", choices=["random", "prefix_repetition"], default="random")
    parser.add_argument("--input-len", type=int, default=8192)
    parser.add_argument("--output-len", type=int, default=128)
    parser.add_argument("--concurrencies", default="1,4,8,12,16,20,24,32,48,64")
    parser.add_argument("--num-prompts", type=int, default=80)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--prefix-len", type=int, default=4096)
    parser.add_argument("--suffix-len", type=int, default=128)
    parser.add_argument("--num-prefixes", type=int, default=8)
    parser.add_argument("--request-rate", default="inf")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def metric_value(text, name):
    pattern = rf"^{re.escape(name)}(?:\{{[^}}]*\}})?\s+([0-9eE+.-]+)$"
    match = re.search(pattern, text, re.MULTILINE)
    return float(match.group(1)) if match else 0.0


def scrape_metrics(ports):
    result = {}
    for port in ports:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=10) as response:
            text = response.read().decode()
        result[str(port)] = {
            "cache_hits": metric_value(text, "vllm:prefix_cache_hits_total"),
            "cache_queries": metric_value(text, "vllm:prefix_cache_queries_total"),
            "preemptions": metric_value(text, "vllm:num_preemptions_total"),
            "spec_accepted": metric_value(text, "vllm:spec_decode_num_accepted_tokens_total"),
            "spec_draft": metric_value(text, "vllm:spec_decode_num_draft_tokens_total"),
            "kv_usage": metric_value(text, "vllm:kv_cache_usage_perc"),
            "running": metric_value(text, "vllm:num_requests_running"),
            "waiting": metric_value(text, "vllm:num_requests_waiting"),
        }
    return result


def metrics_delta(before, after):
    hits = sum(after[p]["cache_hits"] - before[p]["cache_hits"] for p in before)
    queries = sum(after[p]["cache_queries"] - before[p]["cache_queries"] for p in before)
    preemptions = sum(after[p]["preemptions"] - before[p]["preemptions"] for p in before)
    spec_accepted = sum(after[p]["spec_accepted"] - before[p]["spec_accepted"] for p in before)
    spec_draft = sum(after[p]["spec_draft"] - before[p]["spec_draft"] for p in before)
    return {
        "spec_accepted_tokens": spec_accepted,
        "spec_draft_tokens": spec_draft,
        "spec_acceptance_rate": spec_accepted / spec_draft if spec_draft > 0 else 0.0,
        "prefix_cache_hit_tokens": hits,
        "prefix_cache_query_tokens": queries,
        "prefix_cache_hit_rate": hits / queries if queries > 0 else 0.0,
        "preemptions": preemptions,
        "kv_usage_end_by_port": {p: after[p]["kv_usage"] for p in after},
    }


class GpuSampler:
    def __init__(self):
        self.samples = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=10)

    def _run(self):
        while not self.stop_event.is_set():
            command = [
                "nvidia-smi",
                "--query-gpu=index,utilization.gpu,memory.used,power.draw,temperature.gpu,clocks.sm",
                "--format=csv,noheader,nounits",
            ]
            output = subprocess.check_output(command, text=True)
            for line in output.strip().splitlines():
                fields = [item.strip() for item in line.split(",")]
                self.samples.append({
                    "gpu": int(fields[0]),
                    "util": float(fields[1]),
                    "memory": float(fields[2]),
                    "power": float(fields[3]),
                    "temperature": float(fields[4]),
                    "clock": float(fields[5]),
                })
            self.stop_event.wait(2)

    def summary(self):
        result = {}
        for gpu in sorted({sample["gpu"] for sample in self.samples}):
            rows = [sample for sample in self.samples if sample["gpu"] == gpu]
            result[str(gpu)] = {
                "samples": len(rows),
                "util_mean": sum(row["util"] for row in rows) / len(rows),
                "util_max": max(row["util"] for row in rows),
                "memory_max_mib": max(row["memory"] for row in rows),
                "power_max_w": max(row["power"] for row in rows),
                "temperature_max_c": max(row["temperature"] for row in rows),
                "clock_min_mhz": min(row["clock"] for row in rows),
                "clock_max_mhz": max(row["clock"] for row in rows),
            }
        return result


def percentile_sla(result):
    return {
        "sla_p50_ttft_le_8s": result["p50_ttft_ms"] <= 8000,
        "sla_p95_ttft_le_30s": result["p95_ttft_ms"] <= 30000,
    }


def enrich_result(result, cache_metrics, gpu_metrics, experiment, command):
    duration_minutes = result["duration"] / 60
    ttfts = result.get("ttfts", [])
    input_lens = result.get("input_lens", [])
    output_lens = result.get("output_lens", [])
    good_indices = [index for index, ttft in enumerate(ttfts) if ttft <= 8.0]
    good_input = sum(input_lens[index] for index in good_indices)
    good_output = sum(output_lens[index] for index in good_indices)
    result.update({
        "experiment": experiment,
        "benchmark_command": command,
        "input_tpm": result["total_input_tokens"] / duration_minutes,
        "output_tpm": result["total_output_tokens"] / duration_minutes,
        "total_tpm": (result["total_input_tokens"] + result["total_output_tokens"]) / duration_minutes,
        "good_requests_ttft_le_8s": len(good_indices),
        "goodput_req_per_s_ttft_le_8s": len(good_indices) / result["duration"],
        "effective_input_tpm_ttft_le_8s": good_input / duration_minutes,
        "effective_output_tpm_ttft_le_8s": good_output / duration_minutes,
        "effective_total_tpm_ttft_le_8s": (good_input + good_output) / duration_minutes,
        "cache_metrics": cache_metrics,
        "gpu_metrics": gpu_metrics,
    })
    result.update(percentile_sla(result))
    return result


def append_summary(path, result):
    cache = result["cache_metrics"]
    gpu = result.get("gpu_metrics", {})
    row = {
        "name": result["experiment"]["name"],
        "dataset": result["experiment"]["dataset_name"],
        "input_len": result["experiment"]["input_len"],
        "output_len": result["experiment"]["output_len"],
        "concurrency": result["max_concurrency"],
        "num_prompts": result["num_prompts"],
        "completed": result["completed"],
        "failed": result["failed"],
        "seed": result["experiment"]["seed"],
        "duration_s": round(result["duration"], 3),
        "ttft_p50_ms": round(result["p50_ttft_ms"], 2),
        "ttft_p95_ms": round(result["p95_ttft_ms"], 2),
        "tpot_p50_ms": round(result["p50_tpot_ms"], 2),
        "tpot_p95_ms": round(result["p95_tpot_ms"], 2),
        "request_throughput": round(result["request_throughput"], 4),
        "input_tpm": round(result["input_tpm"], 2),
        "output_tpm": round(result["output_tpm"], 2),
        "total_tpm": round(result["total_tpm"], 2),
        "effective_total_tpm_ttft_le_8s": round(result["effective_total_tpm_ttft_le_8s"], 2),
        "goodput_req_per_s_ttft_le_8s": round(result["goodput_req_per_s_ttft_le_8s"], 4),
        "prefix_cache_hit_rate": round(cache["prefix_cache_hit_rate"], 6),
        "prefix_cache_hit_tokens": round(cache["prefix_cache_hit_tokens"]),
        "prefix_cache_query_tokens": round(cache["prefix_cache_query_tokens"]),
        "preemptions": round(cache["preemptions"]),
        "spec_accepted_tokens": round(cache["spec_accepted_tokens"]),
        "spec_draft_tokens": round(cache["spec_draft_tokens"]),
        "spec_acceptance_rate": round(cache["spec_acceptance_rate"], 6),
        "sla_p50_ttft_le_8s": result["sla_p50_ttft_le_8s"],
        "sla_p95_ttft_le_30s": result["sla_p95_ttft_le_30s"],
    }
    for gpu_id, metrics in gpu.items():
        row[f"gpu{gpu_id}_util_mean"] = round(metrics["util_mean"], 2)
        row[f"gpu{gpu_id}_util_max"] = round(metrics["util_max"], 2)
        row[f"gpu{gpu_id}_power_max_w"] = round(metrics["power_max_w"], 2)
    exists = path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run_experiment(args, concurrency, ports):
    seed = args.seed_base + concurrency
    name = f"{args.label}-{args.dataset_name}-i{args.input_len}-o{args.output_len}-c{concurrency}-s{seed}"
    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)
    raw_path = result_dir / f"{name}.json"
    enriched_path = result_dir / f"{name}.enriched.json"
    if enriched_path.exists() and not args.overwrite:
        print(f"SKIP {name}", flush=True)
        return

    command = [
        args.vllm_bin, "bench", "serve",
        "--backend", "openai-chat",
        "--base-url", args.base_url,
        "--endpoint", "/v1/chat/completions",
        "--model", args.model,
        "--tokenizer", args.tokenizer,
        "--dataset-name", args.dataset_name,
        "--output-len", str(args.output_len),
        "--num-prompts", str(args.num_prompts),
        "--num-warmups", "0",
        "--max-concurrency", str(concurrency),
        "--request-rate", str(args.request_rate),
        "--seed", str(seed),
        "--ignore-eos",
        "--percentile-metrics", "ttft,tpot,itl,e2el",
        "--metric-percentiles", "50,95,99",
        "--save-result", "--save-detailed",
        "--result-dir", str(result_dir),
        "--result-filename", raw_path.name,
        "--disable-tqdm",
    ]
    if args.dataset_name == "random":
        command.extend(["--input-len", str(args.input_len)])
    else:
        command.extend([
            "--prefix-repetition-prefix-len", str(args.prefix_len),
            "--prefix-repetition-suffix-len", str(args.suffix_len),
            "--prefix-repetition-num-prefixes", str(args.num_prefixes),
        ])

    experiment = {
        "name": name,
        "dataset_name": args.dataset_name,
        "input_len": args.input_len,
        "output_len": args.output_len,
        "seed": seed,
        "prefix_len": args.prefix_len if args.dataset_name == "prefix_repetition" else None,
        "suffix_len": args.suffix_len if args.dataset_name == "prefix_repetition" else None,
        "num_prefixes": args.num_prefixes if args.dataset_name == "prefix_repetition" else None,
    }
    print(f"START {name}", flush=True)
    before = scrape_metrics(ports)
    sampler = GpuSampler()
    sampler.start()
    started = time.time()
    try:
        completed = subprocess.run(command, text=True, capture_output=True)
        (result_dir / f"{name}.log").write_text(completed.stdout + completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(f"Benchmark failed: {name}; see {name}.log")
        cache_metrics = metrics_delta(before, scrape_metrics(ports))
    finally:
        sampler.stop()
    gpu_metrics = sampler.summary()
    with raw_path.open() as handle:
        result = json.load(handle)
    result = enrich_result(result, cache_metrics, gpu_metrics, experiment, command)
    result["wall_seconds"] = time.time() - started
    enriched_path.write_text(json.dumps(result, indent=2))
    append_summary(result_dir / "summary.csv", result)
    print(
        f"DONE {name} TTFT_P50={result['p50_ttft_ms']:.0f}ms "
        f"TTFT_P95={result['p95_ttft_ms']:.0f}ms "
        f"TOTAL_TPM={result['total_tpm']:.0f} "
        f"CACHE_HIT={result['cache_metrics']['prefix_cache_hit_rate']:.2%} "
        f"SPEC_ACCEPT={result['cache_metrics']['spec_acceptance_rate']:.2%}",
        flush=True,
    )


def main():
    args = parse_args()
    ports = [int(port) for port in args.metrics_ports.split(",")]
    for concurrency in [int(item) for item in args.concurrencies.split(",")]:
        run_experiment(args, concurrency, ports)


if __name__ == "__main__":
    main()

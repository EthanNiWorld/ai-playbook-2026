#!/usr/bin/env python3
"""US(Virginia ECS) -> SG Bailian TTFT benchmark for deepseek-v4.1-flash.

Goal: quantify network-jitter impact on TTFT with a fixed ~200k-token input.
Design:
  - identical payload for all requests (server-side variance minimized;
    repeated payload likely hits implicit cache -> prefill stable)
  - fresh TCP+TLS connection per request (new curl process, --no-keepalive)
  - per-request phase timing via curl -w: dns/tcp/tls/pretransfer/ttfb/total
  - first-token timestamp from SSE stream (first non-empty content OR
    reasoning_content delta; same "first any token" convention as prior tests)
  - background TCP-connect RTT sampler (0.5s interval) for jitter correlation
  - max_tokens=64 so each request completes fast; no early-kill needed,
    curl -w timing stays intact. Output cost negligible.

Stdlib only. API key from env DASHSCOPE_API_KEY (never written to disk).
Outputs: requests.csv, rtt.csv, summary.json, payload.json in --out-dir.
"""
import argparse
import csv
import json
import os
import random
import socket
import statistics
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone

WORDS = (
    "system network latency throughput request response token model inference "
    "cache memory compute cluster scheduling queue batch prefill decode tensor "
    "parallel pipeline gradient attention context window embedding vector "
    "database transaction commit rollback index query optimizer execution plan "
    "kernel driver interrupt buffer socket packet routing gateway firewall "
    "encryption certificate handshake protocol stream frame segment offset"
).split()


def build_text(n_chars, seed=42):
    rng = random.Random(seed)
    parts = []
    total = 0
    i = 0
    while total < n_chars:
        i += 1
        sent = " ".join(rng.choice(WORDS) for _ in range(rng.randint(8, 18)))
        line = f"Document section {i}: {sent}. "
        parts.append(line)
        total += len(line)
    return "".join(parts)[:n_chars]


def make_payload(text, model, max_tokens, include_usage=False, nonce=None):
    content = text + "\n\nReply with the single word: ok"
    if nonce:
        # unique prefix invalidates implicit prefix cache from token ~0
        content = f"Unique request nonce: {nonce}\n\n" + content
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "stream": True,
    }
    if include_usage:
        body["stream_options"] = {"include_usage": True}
    return json.dumps(body)


def run_curl(url, key, payload_path, max_time=180):
    """Return (phase_timings dict, first_token_ms, http_code, err)."""
    wfmt = (
        "\n@@T@@%{time_namelookup}|%{time_connect}|%{time_appconnect}|"
        "%{time_pretransfer}|%{time_starttransfer}|%{time_total}|"
        "%{http_code}|%{size_upload}|%{speed_upload}"
    )
    cmd = [
        "curl", "-sS", "-N", "--no-keepalive",
        "--connect-timeout", "15", "--max-time", str(max_time),
        "-X", "POST", url,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "--data-binary", "@" + payload_path,
        "-w", wfmt,
    ]
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         universal_newlines=True, bufsize=1)  # py3.6 compat
    first_token_ms = None
    timing = None
    usage = None
    errlines = []
    for line in p.stdout:
        line = line.rstrip("\n")
        if line.startswith("@@T@@"):
            f = line[5:].split("|")
            timing = {
                "dns_ms": float(f[0]) * 1000,
                "tcp_ms": (float(f[1]) - float(f[0])) * 1000,
                "tls_ms": (float(f[2]) - float(f[1])) * 1000,
                "pretransfer_ms": float(f[3]) * 1000,
                "ttfb_ms": float(f[4]) * 1000,
                "total_ms": float(f[5]) * 1000,
                "http_code": int(f[6]),
                "size_upload": int(float(f[7])),
                "speed_upload": float(f[8]),
            }
            continue
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            continue
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if obj.get("usage"):
            usage = obj["usage"]
        if first_token_ms is None:
            for ch in obj.get("choices", []):
                d = ch.get("delta", {})
                if d.get("content") or d.get("reasoning_content"):
                    first_token_ms = (time.monotonic() - t0) * 1000
                    break
    _, err = p.communicate(timeout=30)
    if p.returncode != 0:
        errlines.append(f"curl rc={p.returncode}: {err.strip()[:300]}")
    return timing, first_token_ms, usage, "; ".join(errlines)


class RttSampler(threading.Thread):
    """TCP-connect RTT to host:443 every 0.5s (handshake ~ 1 RTT)."""

    def __init__(self, host, out_path):
        super().__init__(daemon=True)
        self.host = host
        self.out_path = out_path
        self.stop_flag = threading.Event()
        self.samples = []

    def run(self):
        while not self.stop_flag.is_set():
            t0 = time.monotonic()
            try:
                s = socket.create_connection((self.host, 443), timeout=5)
                dt = (time.monotonic() - t0) * 1000
                s.close()
                self.samples.append((time.time(), dt))
            except OSError:
                self.samples.append((time.time(), -1.0))
            self.stop_flag.wait(0.5)

    def stop(self):
        self.stop_flag.set()
        self.join(timeout=10)
        with open(self.out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["epoch_s", "tcp_connect_ms"])
            w.writerows(self.samples)


def pct(vals, p):
    if not vals:
        return None
    vals = sorted(vals)
    k = (len(vals) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def stats(vals):
    vals = [v for v in vals if v is not None and v >= 0]
    if not vals:
        return {}
    return {
        "n": len(vals), "mean": round(statistics.mean(vals), 1),
        "stddev": round(statistics.pstdev(vals), 1),
        "min": round(min(vals), 1), "max": round(max(vals), 1),
        "p50": round(pct(vals, 50), 1), "p75": round(pct(vals, 75), 1),
        "p90": round(pct(vals, 90), 1), "p99": round(pct(vals, 99), 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url",
                    default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--target-tokens", type=int, default=200000)
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--cold", action="store_true",
                    help="unique nonce prefix per request -> force cache miss")
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        raise SystemExit("DASHSCOPE_API_KEY env missing")
    os.makedirs(args.out_dir, exist_ok=True)
    url = args.base_url.rstrip("/") + "/chat/completions"
    host = args.base_url.split("//")[1].split("/")[0]
    payload_path = os.path.join(args.out_dir, "payload.json")

    # ---- calibrate payload to target prompt tokens (tokenizer-agnostic) ----
    n_chars = args.target_tokens * 4  # first guess ~4 chars/token
    prompt_tokens = None
    for attempt in range(3):
        text = build_text(n_chars)
        with open(payload_path, "w") as f:
            f.write(make_payload(text, args.model, 8, include_usage=True))
        print(f"[probe {attempt+1}] chars={n_chars} body={os.path.getsize(payload_path)}B",
              flush=True)
        timing, ftok, usage, err = run_curl(url, key, payload_path)
        if err or not timing or timing["http_code"] != 200 or not usage:
            raise SystemExit(f"probe failed: http={timing and timing['http_code']} "
                             f"err={err} usage={usage}")
        prompt_tokens = usage["prompt_tokens"]
        print(f"[probe {attempt+1}] prompt_tokens={prompt_tokens} "
              f"ttfb={timing['ttfb_ms']:.0f}ms", flush=True)
        if abs(prompt_tokens - args.target_tokens) <= args.target_tokens * 0.01:
            break
        n_chars = int(n_chars * args.target_tokens / prompt_tokens)
    # final payload with run-time max_tokens (warm mode base text;
    # cold mode rewrites payload per request with a unique nonce prefix)
    text = build_text(n_chars)
    with open(payload_path, "w") as f:
        f.write(make_payload(text, args.model, args.max_tokens,
                             include_usage=args.cold))
    print(f"[payload] final chars={n_chars} prompt_tokens~{prompt_tokens} "
          f"body={os.path.getsize(payload_path)}B cold={args.cold}", flush=True)

    # ---- main loop ----
    sampler = RttSampler(host, os.path.join(args.out_dir, "rtt.csv"))
    sampler.start()
    rows = []
    failures = 0
    t_start = datetime.now(timezone.utc).isoformat()
    for i in range(1, args.samples + 1):
        if args.cold:
            with open(payload_path, "w") as f:
                f.write(make_payload(text, args.model, args.max_tokens,
                                     include_usage=True,
                                     nonce=f"{i}-{uuid.uuid4()}"))
        row = None
        for retry in range(4):
            timing, ftok, usage, err = run_curl(url, key, payload_path)
            code = timing["http_code"] if timing else 0
            if timing and code == 200 and ftok is not None:
                pt = (usage or {}).get("prompt_tokens", -1)
                ct = (usage or {}).get("prompt_tokens_details", {}).get(
                    "cached_tokens", -1)
                row = {
                    "idx": i, "epoch_s": round(time.time(), 3), "http_code": code,
                    "retries": retry,
                    "dns_ms": round(timing["dns_ms"], 1),
                    "tcp_ms": round(timing["tcp_ms"], 1),
                    "tls_ms": round(timing["tls_ms"], 1),
                    "ttfb_ms": round(timing["ttfb_ms"], 1),
                    "ttft_ms": round(ftok, 1),
                    "upload_est_ms": round(
                        timing["size_upload"] / timing["speed_upload"] * 1000, 1)
                    if timing["speed_upload"] > 0 else -1,
                    "total_ms": round(timing["total_ms"], 1),
                    "size_upload": timing["size_upload"],
                    "prompt_tokens": pt, "cached_tokens": ct, "error": "",
                }
                break
            wait = 5 * (retry + 1)
            print(f"[req {i}] http={code} err={err[:150]} retry in {wait}s",
                  flush=True)
            time.sleep(wait)
        if row is None:
            failures += 1
            row = {"idx": i, "epoch_s": round(time.time(), 3), "http_code": code,
                   "retries": 3, "error": err[:300]}
        rows.append(row)
        if i % 10 == 0:
            ok = [r["ttft_ms"] for r in rows if r.get("ttft_ms")]
            print(f"[{i}/{args.samples}] ttft p50={pct(ok,50):.0f}ms "
                  f"max={max(ok):.0f}ms failures={failures}", flush=True)
        time.sleep(args.interval)
    sampler.stop()

    # ---- outputs ----
    cols = ["idx", "epoch_s", "http_code", "retries", "dns_ms", "tcp_ms",
            "tls_ms", "ttfb_ms", "ttft_ms", "upload_est_ms", "total_ms",
            "size_upload", "prompt_tokens", "cached_tokens", "error"]
    with open(os.path.join(args.out_dir, "requests.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if r.get("ttft_ms")]
    summary = {
        "start_utc": t_start,
        "end_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": url, "model": args.model, "cold_mode": args.cold,
        "prompt_tokens_approx": prompt_tokens,
        "payload_bytes": os.path.getsize(payload_path),
        "samples": args.samples, "success": len(ok), "failures": failures,
        "cached_tokens_values": sorted(set(r.get("cached_tokens", -1) for r in ok)),
        "ttft_ms": stats([r["ttft_ms"] for r in ok]),
        "ttfb_ms": stats([r["ttfb_ms"] for r in ok]),
        "upload_est_ms": stats([r["upload_est_ms"] for r in ok]),
        "tcp_ms": stats([r["tcp_ms"] for r in ok]),
        "tls_ms": stats([r["tls_ms"] for r in ok]),
        "rtt_tcp_connect_ms": stats([v for _, v in sampler.samples]),
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("SUMMARY " + json.dumps(summary), flush=True)
    print("BENCH_DONE", flush=True)


if __name__ == "__main__":
    main()
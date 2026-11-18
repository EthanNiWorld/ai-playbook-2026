#!/usr/bin/env python3
"""Local analysis of US->SG TTFT run: decomposition + jitter correlation.

Reads results/requests.csv + results/rtt.csv, writes results/analysis.json.
- server_residual = ttft - upload_est (prefill/queue/measurement noise)
- per-request RTT window stats (mean/max of TCP-connect samples during request)
- Pearson correlations: ttft vs rtt_mean / rtt_max / upload_est
- quartile drift + 500ms histogram + effective upload throughput
"""
import csv
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGION = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv \
    else "us-east-1"
SUFFIX = "-cold" if "--cold" in sys.argv else ""
RES = os.path.join(HERE, "results", REGION + SUFFIX)


def load():
    with open(os.path.join(RES, "requests.csv")) as f:
        reqs = [r for r in csv.DictReader(f)]
    for r in reqs:
        for k in ("idx", "http_code", "retries", "size_upload"):
            r[k] = int(r[k])
        for k in ("epoch_s", "dns_ms", "tcp_ms", "tls_ms", "ttfb_ms",
                  "ttft_ms", "upload_est_ms", "total_ms"):
            r[k] = float(r[k]) if r[k] else None
    with open(os.path.join(RES, "rtt.csv")) as f:
        rtt = [(float(a), float(b)) for a, b in list(csv.reader(f))[1:]]
    return reqs, rtt


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    return round(statistics.correlation([p[0] for p in pairs],
                                        [p[1] for p in pairs]), 3)


def main():
    reqs, rtt = load()
    ok = [r for r in reqs if r["http_code"] == 200 and r["ttft_ms"]]

    for r in ok:
        r["residual_ms"] = round(r["ttft_ms"] - r["upload_est_ms"], 1)
        r["up_mbps"] = round(r["size_upload"] * 8 / (r["upload_est_ms"] / 1000)
                             / 1e6, 2)
        start = r["epoch_s"] - r["total_ms"] / 1000
        win = [v for t, v in rtt if start <= t <= r["epoch_s"] and v > 0]
        r["rtt_mean"] = round(statistics.mean(win), 1) if win else None
        r["rtt_max"] = round(max(win), 1) if win else None

    ttft = [r["ttft_ms"] for r in ok]
    quart = []
    n = len(ok)
    for q in range(4):
        seg = ok[q * n // 4:(q + 1) * n // 4]
        quart.append({
            "idx_range": f"{seg[0]['idx']}-{seg[-1]['idx']}",
            "ttft_p50_ms": round(statistics.median([r["ttft_ms"] for r in seg]), 1),
            "ttft_mean_ms": round(statistics.mean([r["ttft_ms"] for r in seg]), 1),
            "up_mbps_mean": round(statistics.mean([r["up_mbps"] for r in seg]), 2),
        })

    hist = {}
    for v in ttft:
        b = int(v // 500) * 500
        hist[b] = hist.get(b, 0) + 1

    analysis = {
        "n_success": len(ok),
        "residual_ms": {
            "mean": round(statistics.mean([r["residual_ms"] for r in ok]), 1),
            "stddev": round(statistics.pstdev([r["residual_ms"] for r in ok]), 1),
            "min": min(r["residual_ms"] for r in ok),
            "max": max(r["residual_ms"] for r in ok),
        },
        "upload_mbps": {
            "mean": round(statistics.mean([r["up_mbps"] for r in ok]), 2),
            "min": min(r["up_mbps"] for r in ok),
            "max": max(r["up_mbps"] for r in ok),
        },
        "correlations": {
            "ttft_vs_rtt_mean": pearson(ttft, [r["rtt_mean"] for r in ok]),
            "ttft_vs_rtt_max": pearson(ttft, [r["rtt_max"] for r in ok]),
            "ttft_vs_upload_est": pearson(ttft, [r["upload_est_ms"] for r in ok]),
            "upload_vs_rtt_mean": pearson([r["upload_est_ms"] for r in ok],
                                          [r["rtt_mean"] for r in ok]),
        },
        "quartile_drift": quart,
        "ttft_hist_500ms": {str(k): hist[k] for k in sorted(hist)},
        "top5_slowest": [
            {k: r[k] for k in ("idx", "ttft_ms", "upload_est_ms", "residual_ms",
                               "rtt_mean", "rtt_max", "up_mbps")}
            for r in sorted(ok, key=lambda r: -r["ttft_ms"])[:5]
        ],
    }
    with open(os.path.join(RES, "analysis.json"), "w") as f:
        json.dump(analysis, f, indent=2)
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
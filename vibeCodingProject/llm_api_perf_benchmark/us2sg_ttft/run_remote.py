#!/usr/bin/env python3
"""Drive the US->SG TTFT bench on the Virginia ECS via Cloud Assistant (no SSH).

Subcommands:
  upload  - gzip+base64 ship bench_us2sg.py to /root/us2sg/, sanity-check
  launch  - start bench in background (API key injected via env, never on disk)
  poll    - tail run.log, report progress / BENCH_DONE
  fetch   - pull requests.csv / summary.json / rtt.csv back to ./results/

Key is read from repo .env (DASHSCOPE_API_KEY_SGP) at launch time only.
"""
import base64
import gzip
import io
import json
import os
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


REGION = _arg("--region", "us-east-1")
COLD = "--cold" in sys.argv
TAG = "us2sg_cold" if COLD else "us2sg"
STATE = os.path.join(HERE, f"state_{REGION}.json")
ENV = os.path.normpath(os.path.join(HERE, "../../../.env"))
PROFILE = "ecsdeploy"


def cli(*args):
    r = subprocess.run(["aliyun", *args, "--profile", PROFILE],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"cli failed: {' '.join(args[:3])}\n{r.stderr[:500]}")
    return json.loads(r.stdout)


def instance_id():
    with open(STATE) as f:
        return json.load(f)["instance_id"]


def run_cmd(script, timeout=120):
    b64 = base64.b64encode(script.encode()).decode()
    d = cli("ecs", "RunCommand", "--RegionId", REGION, "--Type", "RunShellScript",
            "--ContentEncoding", "Base64", "--CommandContent", b64,
            "--InstanceId.1", instance_id(), "--Timeout", str(timeout),
            "--Username", "root")
    invoke_id = d["InvokeId"]
    for _ in range(timeout // 3 + 20):
        time.sleep(3)
        r = cli("ecs", "DescribeInvocationResults", "--RegionId", REGION,
                "--InvokeId", invoke_id)
        res = r["Invocation"]["InvocationResults"]["InvocationResult"][0]
        st = res["InvokeRecordStatus"]
        if st in ("Finished", "Failed", "Stopped", "PartialFailed"):
            out = base64.b64decode(res.get("Output", "")).decode(
                "utf-8", "replace")
            return st, res.get("ExitCode"), out
    raise RuntimeError("invocation timeout")


def get_key():
    with open(ENV) as f:
        for line in f:
            if line.startswith("DASHSCOPE_API_KEY_SGP="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("DASHSCOPE_API_KEY_SGP not found in .env")


def upload():
    with open(os.path.join(HERE, "bench_us2sg.py"), "rb") as f:
        blob = base64.b64encode(gzip.compress(f.read())).decode()
    script = (
        "mkdir -p /root/us2sg && "
        f"echo '{blob}' | base64 -d | gunzip > /root/us2sg/bench_us2sg.py && "
        "python3 -c \"import ast;ast.parse(open('/root/us2sg/bench_us2sg.py').read())\" && "
        "echo UPLOAD_OK && python3 --version && curl --version | head -1"
    )
    st, code, out = run_cmd(script)
    print(st, code, out)


def launch():
    key = get_key()
    if not key:
        raise SystemExit("empty key")
    cold_flag = " --cold" if COLD else ""
    script = (
        f"mkdir -p /root/{TAG} && cd /root/{TAG} && "
        f"nohup env DASHSCOPE_API_KEY='{key}' python3 /root/us2sg/bench_us2sg.py "
        f"--out-dir /root/{TAG}{cold_flag} > run.log 2>&1 & echo LAUNCHED_PID $!"
    )
    st, code, out = run_cmd(script)
    print(st, code, out)  # never print the script itself (contains key)


def poll():
    st, code, out = run_cmd(
        f"tail -6 /root/{TAG}/run.log; "
        f"grep -q BENCH_DONE /root/{TAG}/run.log && echo ===DONE=== || echo ===RUNNING===")
    print(out)


def fetch():
    suffix = "-cold" if COLD else ""
    dest = os.path.join(HERE, "results", REGION + suffix)
    os.makedirs(dest, exist_ok=True)
    # per-file gzip+base64: Cloud Assistant output is capped (~24KB),
    # a combined tar exceeds it and gets truncated
    for name in ("requests.csv", "summary.json", "rtt.csv"):
        st, code, out = run_cmd(
            f"gzip -c /root/{TAG}/{name} | base64 -w0", timeout=120)
        if st != "Finished" or not out.strip():
            raise SystemExit(f"fetch {name} failed: {st} {out[:200]}")
        raw = gzip.decompress(base64.b64decode(out.strip()))
        with open(os.path.join(dest, name), "wb") as f:
            f.write(raw)
        print("fetched", name, len(raw), "bytes")
    st, code, out = run_cmd(f"tail -3 /root/{TAG}/run.log")
    print(out)


if __name__ == "__main__":
    argv = [a for i, a in enumerate(sys.argv)
            if a not in ("--region", "--cold")
            and (i == 0 or sys.argv[i - 1] != "--region")]
    {"upload": upload, "launch": launch, "poll": poll, "fetch": fetch}[argv[1]]()
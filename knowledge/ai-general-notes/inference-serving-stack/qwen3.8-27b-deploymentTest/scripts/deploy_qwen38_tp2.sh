#!/usr/bin/env bash
set -Eeuo pipefail

# Qwen3.8-27B single-instance TP2 deployment for dual Blackwell 72GB GPUs.
# Defaults to the measured NVFP4 configuration; FP8 can be selected with
# MODEL_PATH and MODEL_NAME environment variables.

CONDA_ENV="${CONDA_ENV:-/root/.conda/envs/qwen3.8}"
VLLM_BIN="${VLLM_BIN:-${CONDA_ENV}/bin/vllm}"
MODEL_PATH="${MODEL_PATH:-/data/Qwen3.8-27B-NVFP4}"
MODEL_NAME="${MODEL_NAME:-Qwen3.8-27B-NVFP4}"

CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-2}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-32}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
KV_CACHE_DTYPE="${KV_CACHE_DTYPE:-fp8}"
NUM_SPECULATIVE_TOKENS="${NUM_SPECULATIVE_TOKENS:-3}"

LOG_FILE="${LOG_FILE:-/data/vllm-qwen38-tp2.log}"
PID_FILE="${PID_FILE:-/data/vllm-qwen38-tp2.pid}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-600}"

usage() {
    cat <<EOF
Usage: $0 {start|stop|restart|status|logs}

Default deployment:
  Single TP2 + NVFP4 + FP8 KV Cache + MTP=3 + CUDA Graph -O2

Examples:
  $0 start
  $0 status
  $0 logs
  $0 restart
  $0 stop

Deploy FP8 instead:
  MODEL_PATH=/data/Qwen3.8-27B-FP8 \
  MODEL_NAME=Qwen3.8-27B-FP8 \
  LOG_FILE=/data/vllm-fp8-tp2.log \
  PID_FILE=/data/vllm-fp8-tp2.pid \
  $0 start

Common overrides:
  PORT=8001
  MAX_MODEL_LEN=65536
  MAX_NUM_BATCHED_TOKENS=32768
  MAX_NUM_SEQS=32
  NUM_SPECULATIVE_TOKENS=3
  GPU_MEMORY_UTILIZATION=0.90

Warning:
  The default HOST is 127.0.0.1. If HOST=0.0.0.0 is used, add API
  authentication and restrict access with the ECS security group/firewall.
EOF
}

require_files() {
    if [[ ! -x "$VLLM_BIN" ]]; then
        echo "ERROR: vLLM executable not found: $VLLM_BIN" >&2
        exit 1
    fi
    if [[ ! -f "$MODEL_PATH/config.json" ]]; then
        echo "ERROR: model config not found: $MODEL_PATH/config.json" >&2
        exit 1
    fi
    if ! command -v curl >/dev/null 2>&1; then
        echo "ERROR: curl is required" >&2
        exit 1
    fi
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo "ERROR: nvidia-smi is required" >&2
        exit 1
    fi
}

pid_is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

wait_for_health() {
    local deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
    while ((SECONDS < deadline)); do
        if curl -fsS --max-time 3 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
            return 0
        fi
        if ! pid_is_running; then
            echo "ERROR: vLLM exited during startup. Last log lines:" >&2
            tail -80 "$LOG_FILE" >&2 || true
            return 1
        fi
        sleep 5
    done
    echo "ERROR: timed out waiting for http://${HOST}:${PORT}/health" >&2
    tail -80 "$LOG_FILE" >&2 || true
    return 1
}

start_server() {
    require_files
    if pid_is_running; then
        echo "vLLM is already running with PID $(cat "$PID_FILE")"
        exit 0
    fi

    echo "Starting $MODEL_NAME on GPUs $CUDA_VISIBLE_DEVICES"
    echo "Model path: $MODEL_PATH"
    echo "Log file: $LOG_FILE"

    nohup env \
        CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
        PATH="$CONDA_ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
        "$VLLM_BIN" serve "$MODEL_PATH" \
        --served-model-name "$MODEL_NAME" \
        --host "$HOST" \
        --port "$PORT" \
        --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
        --max-model-len "$MAX_MODEL_LEN" \
        --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
        --max-num-seqs "$MAX_NUM_SEQS" \
        --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
        --kv-cache-dtype "$KV_CACHE_DTYPE" \
        --reasoning-parser qwen3 \
        --speculative-config "{\"method\":\"mtp\",\"num_speculative_tokens\":${NUM_SPECULATIVE_TOKENS}}" \
        -O2 \
        >"$LOG_FILE" 2>&1 </dev/null &

    echo $! >"$PID_FILE"
    echo "Started PID $(cat "$PID_FILE"), waiting for health check..."
    wait_for_health
    echo "Service is ready: http://${HOST}:${PORT}/v1"
}

stop_server() {
    if ! pid_is_running; then
        echo "vLLM is not running"
        exit 0
    fi

    local pid
    pid="$(cat "$PID_FILE")"
    echo "Stopping PID $pid..."
    kill "$pid"

    local deadline=$((SECONDS + 60))
    while ((SECONDS < deadline)); do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "vLLM stopped"
            exit 0
        fi
        sleep 2
    done

    echo "ERROR: PID $pid did not stop within 60 seconds" >&2
    exit 1
}

status_server() {
    if pid_is_running; then
        echo "vLLM process is running with PID $(cat "$PID_FILE")"
        ps -p "$(cat "$PID_FILE")" -o pid,etime,%cpu,%mem,cmd
    else
        echo "vLLM process is not running"
    fi

    if curl -fsS --max-time 3 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
        echo "Health check: OK"
        curl -fsS --max-time 5 "http://${HOST}:${PORT}/v1/models"
        printf '\n'
    else
        echo "Health check: FAILED"
    fi
    nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu,power.draw,temperature.gpu --format=csv
}

case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        start_server
        ;;
    status)
        status_server
        ;;
    logs)
        tail -f "$LOG_FILE"
        ;;
    *)
        usage
        exit 1
        ;;
esac

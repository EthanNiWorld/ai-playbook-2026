#!/usr/bin/env bash
# 线上问答只读日报：供 launchd/cron 调用，不修改线上服务与代码。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "$ROOT"
mkdir -p "$ROOT/data/eval" "$ROOT/data/reports"
"$ROOT/.venv/bin/python" -u "$ROOT/tests/e2e/daily_audit.py" "$@"
status=$?
if [[ $status -eq 0 ]] && command -v osascript >/dev/null 2>&1; then
  osascript -e 'display notification "报告位于项目 data/reports，代码建议未自动执行" with title "问答交付日报已生成"' || true
fi
exit "$status"

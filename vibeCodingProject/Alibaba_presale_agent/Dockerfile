# syntax=docker/dockerfile:1
#
# 基础镜像与软件源可用 build-arg 覆盖（国内网络环境必备）：
#   docker build \
#     --build-arg APT_MIRROR=mirrors.aliyun.com \
#     --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
#     -t alibaba-presale-agent .
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""

# git 供知识库 sparse clone/pull 使用；curl 供健康检查
RUN set -eux; \
    if [ -n "$APT_MIRROR" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
            if [ -f "$f" ]; then \
                sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" "$f"; \
            fi; \
        done; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends git curl; \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai

WORKDIR /app

COPY requirements.txt .
RUN set -eux; \
    if [ -n "$PIP_INDEX_URL" ]; then \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# 非 root 运行：先建用户与 /app/data，named volume 首次挂载会继承该属主
RUN set -eux; \
    groupadd -g 10001 appuser; \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser; \
    mkdir -p /app/data; \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser static ./static
COPY --chown=appuser:appuser run.py .

USER appuser

# data 卷：SQLite 交付记录 + 知识库克隆 + 定价页缓存
VOLUME ["/app/data"]
EXPOSE 8000

# start-period 放宽到 90s：首次启动需 sparse clone 知识库并建索引
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -sf http://127.0.0.1:8000/api/health || exit 1

CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000"]

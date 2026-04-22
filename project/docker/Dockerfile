# 心理诊疗室数字人系统 - Dockerfile
# 多阶段构建，优化镜像大小

# ==================== 基础镜像 ====================
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# ==================== 后端构建 ====================
FROM base AS backend-builder

COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# ==================== 前端构建 ====================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ==================== 最终镜像 ====================
FROM base AS production

# 复制后端代码
COPY backend/ /app/backend/
COPY --from=backend-builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# 复制数据目录
COPY data/ /app/data/

# 复制启动脚本
COPY project/docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app/backend

# 暴露端口
EXPOSE 8010 12345

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8010/health || curl -f http://localhost:12345/health || exit 1

# 启动命令
CMD ["/app/start.sh"]

# Docker 部署指南

## 快速启动

### 1. 准备环境变量

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑 .env 文件，填入 API Key
vim backend/.env
```

### 2. 构建并启动

```bash
# 基础启动（使用云端 ASR/TTS）
docker-compose up -d

# 启用本地 ASR
docker-compose --profile local-asr up -d

# 启用缓存
docker-compose --profile cache up -d

# 全部启用
docker-compose --profile local-asr --profile cache up -d
```

### 3. 查看日志

```bash
docker-compose logs -f livetalking
```

### 4. 停止服务

```bash
docker-compose down
```

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8010 | LiveTalking | 数字人渲染服务 |
| 12345 | FastAPI | 后端 API 服务 |
| 9000 | ASR Service | 本地语音识别（可选） |
| 6379 | Redis | 缓存服务（可选） |

## GPU 支持

确保已安装 NVIDIA Docker Runtime：

```bash
# 测试 GPU 访问
docker run --rm --gpus all nvidia/cuda:11.8-base nvidia-smi
```

## 数据持久化

- `data/` - 数字人数据目录
- `avatar_cache` - 模型缓存
- `asr_models` - ASR 模型缓存
- `redis_data` - Redis 数据

## 故障排查

### 容器无法启动
```bash
# 查看详细日志
docker-compose logs livetalking

# 进入容器调试
docker-compose exec livetalking bash
```

### GPU 未识别
```bash
# 检查 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:11.8-base nvidia-smi
```

### 网络问题
```bash
# 重建网络
docker-compose down
docker network prune
docker-compose up -d
```

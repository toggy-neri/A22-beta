FROM python:3.10-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY asr_service.py .

ENV MODEL_NAME=paraformer-large
ENV DEVICE=cpu

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

CMD ["python", "asr_service.py", "--model", "funasr", "--model_name", "${MODEL_NAME}", "--device", "${DEVICE}", "--port", "9000"]

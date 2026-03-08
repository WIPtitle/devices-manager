FROM python:3.10

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV YOLO_CONFIG_DIR=/tmp/yolo_config
RUN mkdir -p /tmp/yolo_config/Ultralytics && chmod -R 777 /tmp/yolo_config

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

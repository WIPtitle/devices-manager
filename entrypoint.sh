#!/bin/sh

cd /app

pip install --upgrade pip

apt-get update && apt-get install -y libpq-dev git ffmpeg libsm6 libxext6
pip install --no-cache-dir -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000

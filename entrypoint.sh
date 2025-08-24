#!/bin/sh

cd /app

pip install --upgrade pip

apt-get update && apt-get install -y libpq-dev git ffmpeg libsm6 libxext6 libxrender1 libglib2.0-0 libgomp1 libgl1-mesa-glx libglu1-mesa
pip install --no-cache-dir -r requirements.txt

mkdir -p /var/lib/devices-manager/data/alarm_recordings
mkdir -p /var/lib/devices-manager/data/recordings

uvicorn app.main:app --host 0.0.0.0 --port 8000 &

while true; do
    response=$(curl --write-out "%{http_code}" --silent --output /dev/null http://0.0.0.0:8000)
    if [ "$response" -eq 404 ]; then
        break
    else
        sleep 1
    fi
done

wait
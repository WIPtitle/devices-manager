#!/bin/sh

cd /app

pip install --upgrade pip

apt-get update && apt-get install -y libpq-dev git ffmpeg libsm6 libxext6
pip install --no-cache-dir -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Loop until server up to force initialization
while true; do
    response=$(curl --write-out "%{http_code}" --silent --output /dev/null http://0.0.0.0:8000)
    if [ "$response" -eq 404 ]; then
        break
    else
        sleep 1
    fi
done

wait

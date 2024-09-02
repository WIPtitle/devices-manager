#!/bin/sh

cd /app

pip install --upgrade pip

apt-get update && apt-get install -y libpq-dev git
pip install --no-cache-dir -r requirements.txt

pip install git+https://github.com/WIPtitle/rabbitmq-sdk.git

uvicorn app.main:app --host 0.0.0.0 --port 8000

#!/bin/sh

mkdir -p /var/lib/devices-manager/data/alarm_recordings
mkdir -p /var/lib/devices-manager/data/recordings

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

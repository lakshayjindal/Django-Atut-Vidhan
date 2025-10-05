#!/usr/bin/env bash
set -o errexit

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🧩 Applying database migrations..."
python manage.py migrate --noinput

echo "🚀 Starting ASGI server (Uvicorn)..."
uvicorn myproject.asgi:application --host 0.0.0.0 --port $PORT --workers 3

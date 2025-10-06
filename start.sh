#!/usr/bin/env bash
set -o errexit

cd main

echo "📦 Collecting static files..."
python3 manage.py collectstatic --noinput

echo "🧩 Applying database migrations..."
python3 manage.py migrate --noinput

echo "🚀 Starting ASGI server (Daphne)..."
daphne -b 0.0.0.0 -p $PORT main.asgi:application

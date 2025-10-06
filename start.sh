#!/usr/bin/env bash
set -o errexit

cd main

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🧩 Applying migrations..."
python manage.py migrate --noinput

echo "🚀 Starting Daphne ASGI server..."
daphne -b 0.0.0.0 -p $PORT main.asgi:application

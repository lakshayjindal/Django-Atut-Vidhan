#!/usr/bin/env bash
# Exit on any error
set -o errexit

cd main

# ---- 1. Collect static files ----
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# ---- 2. Apply database migrations ----
echo "🧩 Applying database migrations..."
python manage.py migrate --noinput

# ---- 3. Start ASGI server ----
echo "🚀 Starting ASGI server (Daphne)..."
# Replace `myproject` with your Django project folder name
daphne -b 0.0.0.0 -p $PORT myproject.asgi:application

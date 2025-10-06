#!/usr/bin/env bash
# Exit on any error
set -o errexit

cd main

# ---- 1. Collect static files ----
echo "📦 Collecting static files..."
python3 manage.py collectstatic --noinput

# ---- 2. Apply database migrations ----
echo "🧩 Applying database migrations..."
python3 manage.py migrate --noinput

# ---- 3. Start ASGI server ----
echo "🚀 Starting ASGI server (Daphne)..."
daphne -b 0.0.0.0 -p $PORT main.asgi:application

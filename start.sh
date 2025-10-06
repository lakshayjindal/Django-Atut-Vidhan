#!/bin/bash
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Daphne ASGI server..."
# Use the port provided by Railway
exec daphne -b 0.0.0.0 -p ${PORT:-8000} main.asgi:application

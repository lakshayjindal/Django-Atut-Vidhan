#!/bin/bash

# Exit on error
set -e

echo "🔥 Starting Atut Vidhan Django ASGI Server..."

# Apply database migrations
echo "🗃️ Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# (Optional) Create superuser automatically (if you want)
# echo "👤 Creating default superuser..."
# python manage.py shell -c "
# from django.contrib.auth import get_user_model;
# User = get_user_model();
# User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
# "

# Start Daphne ASGI server
echo "🚀 Launching Daphne server..."
daphne -b 0.0.0.0 -p ${PORT:-8000} main.asgi:application

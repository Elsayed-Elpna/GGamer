#!/bin/sh

echo "Waiting for PostgreSQL..."

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

echo "PostgreSQL started successfully"

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Running Django migrations..."
  python manage.py migrate --noinput
fi

if [ "$COLLECT_STATIC" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Starting Gunicorn server..."

exec gunicorn core.wsgi:application --bind 0.0.0.0:8000

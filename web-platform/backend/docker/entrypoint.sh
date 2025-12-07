#!/bin/sh
echo "=== Starting entrypoint ==="
echo "DB_HOST: localhost"
echo "DB_PORT: 5432"

echo "Waiting for Postgres..."
until nc -z localhost 5432; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done
echo "Postgres is up - continuing"

echo "Applying migrations"
python manage.py makemigrations
python manage.py migrate

echo "Starting Daphne"
exec daphne -b 0.0.0.0 -p 4864 backend.asgi:application

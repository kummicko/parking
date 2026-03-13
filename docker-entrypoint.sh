#!/bin/bash
set -e

echo "Checking database directory..."
if [ ! -w /app/src/db ]; then
  echo "ERROR: /app/src/db is not writable by user $(whoami)!"
  exit 1
fi

echo "Running database migrations..."
python src/manage.py makemigrations --noinput
python src/manage.py migrate --noinput

exec "$@"

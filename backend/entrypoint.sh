#!/bin/sh
set -e

case "$1" in
  django)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers "${GUNICORN_WORKERS:-2}"
    ;;
  api)
    exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
    ;;
  celery)
    exec celery -A config worker -l info -c "${CELERY_CONCURRENCY:-2}"
    ;;
  makemigrations)
    shift
    exec python manage.py makemigrations "$@"
    ;;
  manage)
    shift
    exec python manage.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac

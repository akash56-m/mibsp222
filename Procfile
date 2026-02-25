web: gunicorn wsgi:app --workers 2 --timeout 120
worker: celery -A app.celery worker --loglevel=info
beat: celery -A app.celery beat --loglevel=info

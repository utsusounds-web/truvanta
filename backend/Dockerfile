FROM python:3.12-slim

# psycopg2-binary needs libpq at runtime; build-essential covers any
# package here that needs to compile (pillow's C extensions, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles

EXPOSE 8000

# Runs migrations and collects static files every time the container
# starts — safe to run repeatedly (migrate is idempotent), and means
# a `docker compose up` after a code change never needs a separate
# manual migration step.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]

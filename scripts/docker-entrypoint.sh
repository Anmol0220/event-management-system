#!/bin/sh
set -eu

python - <<'PY'
import os
import time

import psycopg

host = os.getenv("DATABASE_HOST", "db")
port = int(os.getenv("DATABASE_PORT", "5432"))
dbname = os.getenv("DATABASE_NAME", "event_management")
user = os.getenv("DATABASE_USER", "postgres")
password = os.getenv("DATABASE_PASSWORD", "postgres")

max_attempts = 30
for attempt in range(1, max_attempts + 1):
    try:
        connection = psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=3,
        )
        connection.close()
        print(f"Database connection established on attempt {attempt}.")
        break
    except Exception as exc:
        print(f"Waiting for PostgreSQL ({attempt}/{max_attempts}): {exc}")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL did not become available in time.")
PY

alembic upgrade head

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --proxy-headers

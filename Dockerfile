FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY README.md ./README.md

RUN mkdir -p /app/app/static/uploads/products \
    && chmod +x /app/scripts/docker-entrypoint.sh \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

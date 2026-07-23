FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPENV_NOSPIN=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

RUN pip install --no-cache-dir pipenv==2026.6.2

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY --chown=app:app app.py README.md ./
COPY --chown=app:app data_processing ./data_processing
COPY --chown=app:app input_handling ./input_handling
RUN chown app:app /app

USER app

EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8050/', timeout=5)"]

CMD ["gunicorn", "--bind=0.0.0.0:8050", "--workers=2", "--threads=2", "--timeout=120", "app:server"]

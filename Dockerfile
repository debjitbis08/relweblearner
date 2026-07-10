# The reading app — a single deploy-ready container.
# Build:  docker build -t relweb .
# Run:    docker run -p 8000:8000 -v relweb-data:/data relweb
# State persists in the /data volume (the append-only session log).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    RELWEB_DATA=/data/session.jsonl \
    RELWEB_HOST=0.0.0.0 \
    RELWEB_PORT=8000

WORKDIR /app
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# deps first (layer-cached), then the source
COPY pyproject.toml poetry.lock README.md ./
COPY src ./src
RUN poetry install --only main --no-interaction

VOLUME /data
EXPOSE 8000
CMD ["python", "-m", "relweblearner.serve"]

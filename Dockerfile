FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY server.py ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --no-build-isolation .

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000 8001

VOLUME ["/app/data"]

ENTRYPOINT ["ssh-todolist-service"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--ws-port", "8001", "--db", "/app/data/todos.db"]

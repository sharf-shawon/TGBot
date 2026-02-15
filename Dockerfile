FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY pyproject.toml uv.lock /app/

# Install runtime dependencies only with uv.
RUN pip install --upgrade pip \
    && pip install uv \
    && uv sync --frozen --no-dev

COPY src/ /app/src/

# Use a non-root user for runtime.
RUN useradd -m appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app/data

USER appuser

CMD ["/app/.venv/bin/python", "src/main.py"]

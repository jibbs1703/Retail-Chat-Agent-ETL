FROM python:3.14-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "*.pyo" -delete

FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    TORCH_HOME=/tmp/torch_cache \
    HF_HOME=/tmp/hf_cache

RUN adduser --disabled-password --gecos "" appuser || true

COPY --chown=appuser:appuser app /app/app

EXPOSE 8000

USER appuser

CMD ["uvicorn", "app.v1.server.server:app", "--host", "0.0.0.0", "--port", "8000"]
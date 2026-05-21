# =============================================================================
# MatRisk AI v1.0 — Production Dockerfile (multi-stage)
#
# Stage 1 ("builder")  → installs deps and the matrisk package into a venv.
# Stage 2 ("runtime")  → minimal slim image with only the venv + source.
# Default command runs the FastAPI service on port 8000. Override with
# `command: matrisk pipeline run` to use the container as a batch job.
# =============================================================================

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-deps .


# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system matrisk \
    && useradd --system --gid matrisk --home ${APP_HOME} --shell /bin/bash matrisk

WORKDIR ${APP_HOME}

COPY --from=builder /opt/venv /opt/venv
COPY --chown=matrisk:matrisk src/        ./src/
COPY --chown=matrisk:matrisk configs/    ./configs/
COPY --chown=matrisk:matrisk dashboard/  ./dashboard/
COPY --chown=matrisk:matrisk data/raw/   ./data/raw/
COPY --chown=matrisk:matrisk pyproject.toml README.md ./

RUN mkdir -p ${APP_HOME}/data/processed ${APP_HOME}/models ${APP_HOME}/mlruns ${APP_HOME}/reports \
    && chown -R matrisk:matrisk ${APP_HOME}

USER matrisk

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD curl -fsS http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "matrisk.serve.app:app", "--host", "0.0.0.0", "--port", "8000"]

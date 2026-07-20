# syntax=docker/dockerfile:1.7
# ============================================================================
# Stage 1 – Builder (install dependencies)
# ============================================================================
# Note: gcc is a build-time dependency only - not included in final image
# Version pinning ensures reproducible builds
FROM python:3.12-alpine3.23 AS builder

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

WORKDIR /build

COPY src/app/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip==25.3 \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================================
# Stage 2 – Security runtimedocker
# ============================================================================
FROM python:3.12-alpine3.23 AS runtime

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.opencontainers.image.title="SecureApp" \
      org.opencontainers.image.description="DevSecOps demo FastAPI application" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/${GITHUB_REPOSITORY}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="DevSecOps POC" \
      org.opencontainers.image.authors="DevSecOps Team" \
      org.opencontainers.image.ref.name="main"

WORKDIR /app

COPY --from=builder /install /usr/local

COPY src/app/ ./src/app/

RUN addgroup -g 1000 appgroup && adduser -u 1000 -G appgroup -D -s /bin/sh appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')"]

CMD ["python", "-m", "uvicorn", "src.app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-trixie AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
# Optional build secret for networks that inspect TLS (a corporate or sandbox proxy CA).
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir uv==0.11.32 && uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    uv sync --frozen --no-dev --no-editable
# YuNet face detector (MIT); the checksum pins the exact file the tests ran against.
ADD --chmod=644 --checksum=sha256:8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4 \
    https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx \
    models/face_detection_yunet_2023mar.onnx

FROM python:3.13-slim-trixie
RUN useradd --system --uid 10001 --home-dir /app sadu
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/models /app/models
COPY alembic.ini ./
COPY alembic ./alembic
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 SADU_REGION_PACKS_DIR=/region-packs SADU_DEMO_CACHE_DIR=/app/demo-cache
RUN mkdir -p /app/demo-cache && chown sadu /app/demo-cache
USER sadu
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/healthz')"]
CMD ["uvicorn", "sadu.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

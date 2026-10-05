FROM node:24.13.0-alpine3.23 AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13.12-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements-lock.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --uid 1000 --create-home app
COPY backend/ ./backend/
COPY scripts/web_gateway.py ./scripts/web_gateway.py
COPY workflows/*.api.json ./workflows/
COPY evaluation/*.json ./evaluation/
COPY evaluation/*.py ./evaluation/
COPY evaluation/prompts/ ./evaluation/prompts/
COPY deployment/logging.json ./deployment/logging.json
COPY --from=frontend /build/dist ./frontend/dist
RUN mkdir -p /data /srv/comfy/input /srv/comfy/output && chown -R 1000:1000 /data /srv/comfy
RUN pip check && python -m pytest backend/tests -q -p no:cacheprovider --basetemp=/tmp/comfyfitter-build-tests
USER 1000:1000
EXPOSE 8000
CMD ["python","-m","uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--no-access-log","--log-config","deployment/logging.json"]

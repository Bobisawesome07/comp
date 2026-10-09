FROM oven/bun:1.4.2 AS frontend
WORKDIR /web
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
RUN bun run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /web/dist ./frontend/dist/
RUN useradd --create-home game
USER game
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --ws-max-size 4096 --ws-ping-interval 15 --ws-ping-timeout 30"]

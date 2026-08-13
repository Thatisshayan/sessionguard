# Multi-stage Dockerfile for SessionGuard
# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend + Staged Frontend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (FFmpeg & Tesseract OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-eng \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Copy static frontend dist into backend/static
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose backend port
EXPOSE 8000

ENV SESSIONGUARD_DEV_MODE=false
ENV PORT=8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.127", "--port", "8000"]

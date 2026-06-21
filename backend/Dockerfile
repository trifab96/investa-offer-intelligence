# syntax=docker/dockerfile:1
FROM python:3.12-slim

# System deps: Tesseract for optional OCR fallback on scanned PDFs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-deu \
        libtesseract-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy the project, then install it with its dependencies (incl. optional OCR).
# PYTHONPATH=/app ensures the in-tree source is imported, so non-Python assets
# (prompt templates, scoring.yaml, seed CSV) resolve via __file__ at runtime
# regardless of whether the install is editable.
COPY . .
RUN pip install --upgrade pip && pip install ".[ocr]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

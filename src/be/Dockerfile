FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY src/be/pyproject.toml src/be/
RUN pip install --no-cache-dir ./src/be \
    && rm -rf /root/.cache

# Copy backend application code
COPY src/be/app/ src/be/app/

# Create runtime directories (mounted as volumes in production)
RUN mkdir -p /app/documents /app/data

EXPOSE 8000

# Run from /app/src/be so PROJECT_ROOT (parents[4]) resolves to /app
WORKDIR /app/src/be
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

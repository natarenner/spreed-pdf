FROM python:3.11-slim

# Install system dependencies for WeasyPrint and UV
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --frozen ensures we use the exact versions from uv.lock
# --no-cache avoids bloating the image with uv's internal cache
RUN uv sync --frozen --no-cache

# Copy the rest of the application
COPY . .

# Expose port (FastAPI default)
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
CMD ["uv", "run", "fastapi", "run", "api/main.py"]

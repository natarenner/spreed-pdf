# Use a stable Debian-based image matching project python version
FROM python:3.13-slim-bookworm

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for WeasyPrint and environment
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fontconfig \
    libnss3 \
    libfreetype6 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv using the official binary from their image (Astral)
# This is more reliable inside Docker than the curl script
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Optimize uv for Docker
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (using system python)
RUN uv sync --frozen --no-cache --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync --frozen --no-cache

# Expose port (FastAPI default)
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
CMD ["uv", "run", "fastapi", "run", "api/main.py"]

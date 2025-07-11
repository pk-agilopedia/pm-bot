# ---------------------------------------------
# Stage 1: Base image
# ---------------------------------------------
    FROM python:3.11-slim AS base

    # Set environment variables
    ENV PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1 \
        ENVIRONMENT=production
    
    # Set working directory
    WORKDIR /app
    
    # Install system dependencies
    RUN apt-get update \
        && apt-get install -y --no-install-recommends \
            build-essential \
            default-libmysqlclient-dev \
            pkg-config \
            curl \
        && rm -rf /var/lib/apt/lists/*
    
    # Copy requirements first to leverage Docker cache
    COPY requirements.txt .
    
    # Install Python dependencies
    RUN pip install --no-cache-dir --upgrade pip \
        && pip install --no-cache-dir -r requirements.txt \
        && pip install --no-cache-dir gunicorn==21.2.0
    
    # Copy application code
    COPY . .
    
    # Create logs directory
    RUN mkdir -p logs
    
    # Create non-root user
    RUN useradd --create-home --shell /bin/bash app \
        && chown -R app:app /app
    
    USER app
    
    # Expose the application port
    EXPOSE 5000
    
    # Health check
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
        CMD curl -f http://localhost:5000/api/v1/health || exit 1
    
    # Start the application
    CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "wsgi:app"]
    
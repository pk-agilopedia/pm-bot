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
            netcat-openbsd \
        && rm -rf /var/lib/apt/lists/*
    
    # Copy requirements first to leverage Docker cache
    COPY requirements.txt .
    
    # Install Python dependencies
    RUN pip install --no-cache-dir --upgrade pip \
        && pip install --no-cache-dir -r requirements.txt \
        && pip install --no-cache-dir gunicorn==21.2.0
    
    # Copy application code
    COPY . .
 
    RUN chmod +x /app/entrypoint.sh
    
    # Create app user and logs directory, set permissions
    RUN useradd --create-home --shell /bin/bash app \
        && mkdir -p /app/logs \
        && chown -R app:app /app \
        && chmod -R 755 /app/logs

    USER app
    
    # Expose the application port
    EXPOSE 5000
    
    # Health check
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
        CMD curl -f http://localhost:5000/api/v1/health || exit 1   

    ENTRYPOINT ["/app/entrypoint.sh"]
    
    
   
    
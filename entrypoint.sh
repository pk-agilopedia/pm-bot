#!/bin/bash
set -e

echo "🚀 Running database initialization..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
timeout=60
counter=0
while ! nc -z db 3306; do
    if [ $counter -ge $timeout ]; then
        echo "❌ Database connection timeout after ${timeout} seconds"
        exit 1
    fi
    echo "Database not ready yet, waiting... (${counter}/${timeout})"
    sleep 2
    counter=$((counter + 2))
done

echo "✅ Database is ready!"

# Set environment variables
export FLASK_APP=app.py
export PYTHONPATH=/app:$PYTHONPATH

# Run database initialization with retry logic
echo "🔄 Initializing database..."
max_retries=3
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if python -m flask init_db; then
        echo "✅ Database initialization complete!"
        break
    else
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            echo "⚠️  Database initialization failed, retrying in 5 seconds... (attempt $retry_count/$max_retries)"
            sleep 5
        else
            echo "❌ Database initialization failed after $max_retries attempts"
            exit 1
        fi
    fi
done

# Now start Gunicorn
echo "🚀 Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --access-logfile - --error-logfile - wsgi:app
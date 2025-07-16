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
export PYTHONPATH=/app:$PYTHONPATH

# Run database initialization using your existing init_db.py file
echo "🔄 Initializing database..."
python /app/init_db.py

echo "✅ Database initialization complete!"

# Now start Gunicorn (your wsgi.py already exists)
echo "🚀 Starting Gunicorn server..."
exec gunicorn \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi:app
#!/bin/bash
set -e

echo "🚀 Running database initialization..."

# Run your DB init code
flask --app app init_db

echo "✅ Database initialization complete!"

# Now start Gunicorn
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app

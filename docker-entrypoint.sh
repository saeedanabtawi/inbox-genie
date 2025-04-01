#!/bin/bash
set -e

# Wait for Postgres to be ready
echo "Waiting for PostgreSQL to start..."
# Get postgres credentials from environment variables
PGPASSWORD=${POSTGRES_PASSWORD:-inbox-genie-pass}
PGUSER=${POSTGRES_USER:-postgres}
PGDATABASE=${POSTGRES_DB:-inboxgenie}

# Export password so psql can use it
export PGPASSWORD

# Wait until we can connect to PostgreSQL
until psql -h db -U $PGUSER -d $PGDATABASE -c '\q'; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL started"

# Run database migrations
echo "Creating/updating database tables..."
python -c "from src.app import app; from src.models import db; app.app_context().push(); db.create_all()"

echo "Database setup complete"

# Start the application
echo "Starting application..."
exec "$@"

FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PostgreSQL client
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && pip install psycopg2==2.9.5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py

# Make the entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]

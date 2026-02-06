FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (e.g., for OpenCV or others if needed)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port (internal)
EXPOSE 5000

# Command is handled by docker-compose, but add default
CMD ["gunicorn", "-w", "1", "--timeout", "300", "-b", "0.0.0.0:5000", "app:app"]

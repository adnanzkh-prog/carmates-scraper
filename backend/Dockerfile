FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies FIRST (before Playwright install)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify playwright is installed, then install browsers
RUN python -m playwright install chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

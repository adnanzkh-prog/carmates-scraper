#!/bin/bash
set -e

if [ "$SERVICE_MODE" = "worker" ]; then
    echo "========================================"
    echo "  Starting Celery Worker"
    echo "========================================"
    exec celery -A celery_app worker --loglevel=info --concurrency=2
else
    echo "========================================"
    echo "  Starting FastAPI Server"
    echo "========================================"
    exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
fi

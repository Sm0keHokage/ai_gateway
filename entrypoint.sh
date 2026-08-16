#!/bin/bash
set -e

echo "Waiting for database..."
until python -c "
import asyncio
import asyncpg
import os

async def check():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'db'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        database=os.getenv('DB_NAME', 'ai_gateway'),
    )
    await conn.close()

asyncio.run(check())
" 2>/dev/null; do
    echo "DB not ready, retrying in 2s..."
    sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn main:app \
    --host "${SERVICE_HOST:-0.0.0.0}" \
    --port "${SERVICE_PORT:-8100}" \
    --workers "${WORKERS:-1}"

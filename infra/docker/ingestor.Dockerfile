FROM python:3.11-slim

WORKDIR /app

COPY data-pipeline/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY data-pipeline /app

# Default command executes daily ingest bundle (SteamDB + YouTube + Reddit refresh).
CMD ["python", "-m", "jobs.run_daily_update"]

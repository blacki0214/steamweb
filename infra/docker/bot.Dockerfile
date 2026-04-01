FROM python:3.11-slim
WORKDIR /app
COPY backend/bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/bot /app
CMD ["python", "bot.py"]

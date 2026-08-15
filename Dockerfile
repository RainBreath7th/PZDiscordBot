FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY config/ config/

ENV PYTHONUNBUFFERED=1
ENV CONFIG_DIR=/app/config
ENV HEALTH_STATE_PATH=/tmp/pz-bot-health.json

CMD ["python", "-m", "bot"]

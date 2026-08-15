FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY config/ config.defaults/
COPY config/ config/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV CONFIG_DIR=/app/config
ENV HEALTH_STATE_PATH=/tmp/pz-bot-health.json

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "-m", "bot"]

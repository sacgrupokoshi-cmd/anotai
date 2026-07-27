FROM python:3.11-slim

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir python-telegram-bot==20.7 anthropic python-dotenv psycopg2-binary

COPY . .

CMD ["python", "bot.py"]
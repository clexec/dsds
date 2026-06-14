FROM python:3.11-slim

WORKDIR /app

COPY модератор/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY модератор/ .

CMD ["python", "bot.py"]

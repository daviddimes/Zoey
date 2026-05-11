FROM python:3.11-slim

WORKDIR /app
RUN mkdir -p /data

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "messaging.py"]
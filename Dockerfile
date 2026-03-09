FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY oref_monitor.py .
COPY phone_caller.py .
COPY phone_store.py .
COPY web_app.py .
COPY main.py .
COPY templates/ ./templates/

EXPOSE 8080

CMD ["python", "main.py"]

# Baseera frontend — NiceGUI
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# BACKEND_URL is set by docker-compose.yml to the backend service name,
# e.g. http://backend:8000 — containers reach each other by service name,
# not localhost.
CMD ["python", "app.py"]

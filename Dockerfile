FROM python:3.12-slim

WORKDIR /app

# Copy backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Port from Railway
ENV PORT=8000
EXPOSE $PORT

CMD ["sh", "-c", "python -m uvicorn main:socket_app --host 0.0.0.0 --port ${PORT}"]

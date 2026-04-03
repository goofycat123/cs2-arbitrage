FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets PORT at runtime
CMD sh -c "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"

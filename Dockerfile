FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    IDCOLIS_ENV=production \
    IDCOLIS_BACKEND_URL=http://127.0.0.1:8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x start.sh

EXPOSE 8501
CMD ["./start.sh"]

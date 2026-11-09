#!/bin/sh
set -e

python -m backend.serve &

for i in $(seq 1 20); do
  python -c "import httpx; httpx.get('http://127.0.0.1:8000/docs', timeout=1)" 2>/dev/null && break
  sleep 1
done

exec python -m streamlit run app.py \
  --server.port "${PORT:-8501}" \
  --server.address 0.0.0.0 \
  --server.headless true

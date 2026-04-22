FROM python:3.12-slim

WORKDIR /app

# jq + flock are needed by init-prototype.sh / allocate-port.sh.
RUN apt-get update && apt-get install -y --no-install-recommends jq util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi==0.115.0 "uvicorn[standard]==0.32.0"

COPY server.py /app/server.py

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]

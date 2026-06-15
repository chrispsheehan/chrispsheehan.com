FROM python:3.12-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /repo

COPY get_changes.py /app/get_changes.py
COPY test_get_changes.py /app/test_get_changes.py

ENTRYPOINT ["python3", "/app/get_changes.py"]

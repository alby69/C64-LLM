FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    binutils \
    libc6-dev \
    gcc \
    make \
    git \
    vim \
    curl \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "--version"]
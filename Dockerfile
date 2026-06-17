FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    git \
    curl \
    unzip \
    zip \
    gcc \
    build-essential \
    acme \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Assicura la creazione delle cartelle persistenti/data
RUN mkdir -p data/input data/output data/tmp data/models data/src data/vectorstore knowledge_base

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download del modello LoRA (0.5B) per training CPU immediato
RUN python -c "\
from transformers import AutoModelForCausalLM, AutoTokenizer; \
AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-Coder-0.5B-Instruct'); \
AutoTokenizer.from_pretrained('Qwen/Qwen2.5-Coder-0.5B-Instruct'); \
print('✅ Modello 0.5B pre-scaricato'); \
"

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 7860

CMD ["python", "--version"]

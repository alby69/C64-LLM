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
RUN mkdir -p data/raw data/kb data/logs data/models data/db data/models data/kb/manuali

# Layer 1: dipendenze stabili (cambiano raramente)
# --only-binary :all: evita compilazioni da sorgente (scikit-learn, ecc.)
RUN pip install --no-cache-dir --only-binary :all: \
    torch>=2.0.0 \
    transformers>=4.37.0 \
    sentence-transformers>=2.2.0 \
    accelerate>=0.27.0 \
    sentencepiece>=0.1.99 \
    numpy>=1.24.0

# Layer 2: dipendenze di progetto (cambiano più spesso)
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

FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système pour compiler numpy/pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r scrapper/requirements.txt

CMD ["python", "scrapper/main.py"]


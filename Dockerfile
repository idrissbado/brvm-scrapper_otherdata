FROM python:3.11-slim

# Dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app

# Copier requirements
COPY scraper/requirements.txt ./requirements.txt

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code
COPY . .

# Exécuter tous les scripts dans le dossier "scrapper"
CMD ["sh", "-c", "for f in scrapper/*.py; do python $f; done"]

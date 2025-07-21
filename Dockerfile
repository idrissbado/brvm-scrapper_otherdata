FROM python:3.11-slim

WORKDIR /app

# Copier uniquement les requirements d'abord pour optimiser le cache Docker
COPY scrapper/requirements.txt .

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && pip install --no-cache-dir -r requirements.txt

# Copier tous les fichiers dans le conteneur
COPY scrapper/ ./scrapper/

# Lancer tous les scripts .py du dossier scrapper
CMD ["sh", "-c", "for f in scrapper/*.py; do python \"$f\"; done"]

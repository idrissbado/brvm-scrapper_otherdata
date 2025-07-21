FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier tous les fichiers dans le conteneur
COPY . .

# Installer les dépendances depuis scrapper/requirements.txt
RUN pip install --no-cache-dir -r scrapper/requirements.txt

# Lancer main.py (qui exécute les autres fichiers .py si besoin)
CMD ["python", "scrapper/main.py"]


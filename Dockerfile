# Utilise l'image Python 3.11
FROM python:3.11-slim

# Installe les dépendances nécessaires
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    chromium \
    chromium-driver

# Définit les variables d'environnement pour Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/lib/chromium/chromedriver

# Crée le dossier de travail
WORKDIR /app

# Copie le projet
COPY . /app

# Installe les dépendances Python
RUN pip install --no-cache-dir -r scrapper/requirements.txt

# Lance le script principal
CMD ["python", "scrapper/main.py"]

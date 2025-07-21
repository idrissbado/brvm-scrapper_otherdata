# Utilise une image Python 3.11 légère
FROM python:3.11-slim

# Installe les dépendances système nécessaires pour Chromium + Selenium
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
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Variables d’environnement pour Chrome/Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/lib/chromium/chromedriver

# Définir le répertoire de travail
WORKDIR /app

# Copier tout le projet
COPY . .

# Installer les dépendances Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r scrapper/requirements.txt

# Lancer le script principal
CMD ["python", "scrapper/main.py"]

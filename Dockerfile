FROM python:3.11-slim

# Installer les dépendances système nécessaires à Chrome et Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Installer Google Chrome stable
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Installer webdriver-manager
RUN pip install webdriver-manager

# Définir le dossier de travail
WORKDIR /app/scrapper

# Copier requirements.txt et installer les dépendances
COPY scrapper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le contenu du dossier scrapper
COPY scrapper/ .

# Commande pour exécuter tous les fichiers .py un par un
CMD find . -name "*.py" | sort | xargs -n 1 python

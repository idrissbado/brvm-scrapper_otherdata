import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Lister tous les fichiers .py dans scrapper/ sauf main.py
files = sorted([f for f in os.listdir(BASE_DIR) if f.endswith(".py") and f != "main.py"])

for filename in files:
    filepath = os.path.join(BASE_DIR, filename)
    print(f"🟢 Exécution de {filename}...")
    try:
        subprocess.run(["python", filepath], check=True)
    except subprocess.CalledProcessError as e:
        print(f"🔴 Erreur lors de l'exécution de {filename} : {e}")

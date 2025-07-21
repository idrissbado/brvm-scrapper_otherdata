import os
import time
import re
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL connection using SQLAlchemy
target_postgres_engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Configure headless Chrome
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.binary_location = "/usr/bin/chromium"  # Utilisation de chromium système

# Setup WebDriver avec ChromeDriver système
driver = webdriver.Chrome(
    service=Service("/usr/lib/chromium/chromedriver"),
    options=options
)

# URL à scraper
url = "https://www.brvm.org/en/volumes/0"
driver.get(url)
time.sleep(7)

# Récupération de la date de mise à jour
try:
    last_update_elem = driver.find_element(By.XPATH, "//*[contains(text(),'Last update')]")
    last_update_text = last_update_elem.text.strip()
except:
    last_update_text = "Unknown update date"

# Parsing de la date
update_date = None
date_match = re.search(r"Last update:\s*(.*)", last_update_text)
if date_match:
    update_date = date_match.group(1)

# Récupération des lignes du tableau
rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
print(f"Found {len(rows)} rows")

data = []
for row in rows:
    cols = row.find_elements(By.TAG_NAME, "td")
    if len(cols) >= 6:
        symbol = cols[0].text.strip()
        name = cols[1].text.strip()
        number_of_transactions = cols[2].text.strip().replace('\xa0', '').replace(' ', '')
        traded_value = cols[3].text.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        per = cols[4].text.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        percent_global_value = cols[5].text.strip().replace('%', '').replace(',', '.')
        data.append([
            symbol, name, number_of_transactions, traded_value, per, percent_global_value
        ])

driver.quit()

# Transformation en DataFrame
df = pd.DataFrame(data, columns=[
    "SYMBOL", "NAME", "NUMBER_OF_TRANSACTIONS", "TRADED_VALUE", "PER", "PERCENT_GLOBAL_TRADED_VALUE"
])

# Conversion des colonnes numériques
for col in ["NUMBER_OF_TRANSACTIONS", "TRADED_VALUE", "PER", "PERCENT_GLOBAL_TRADED_VALUE"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df["UPDATE_DATE"] = update_date

def parse_date(date_str):
    try:
        date_part = date_str.split('-', 1)[0].strip()
        return datetime.strptime(date_part, '%A, %d %B, %Y').date()
    except:
        return pd.NaT

df['UPDATE_DATE'] = df['UPDATE_DATE'].apply(parse_date)
if df['UPDATE_DATE'].isna().any():
    df['UPDATE_DATE'] = df['UPDATE_DATE'].fillna(df['UPDATE_DATE'].mode()[0])

df['ID'] = df['NAME'] + df['UPDATE_DATE'].astype(str)

# Insertion dans PostgreSQL
with target_postgres_engine.begin() as connection:
    for _, row in df.iterrows():
        connection.execute(
            text("""
                INSERT INTO volumes (
                    id, symbol, name, number_of_transactions, 
                    traded_value, per, percent_global_traded_value, update_date
                ) VALUES (
                    :id, :symbol, :name, :number_of_transactions, 
                    :traded_value, :per, :percent_global_traded_value, :update_date
                )
                ON CONFLICT (id) DO UPDATE SET
                    symbol = EXCLUDED.symbol,
                    name = EXCLUDED.name,
                    number_of_transactions = EXCLUDED.number_of_transactions,
                    traded_value = EXCLUDED.traded_value,
                    per = EXCLUDED.per,
                    percent_global_traded_value = EXCLUDED.percent_global_traded_value,
                    update_date = EXCLUDED.update_date
            """),
            {
                'id': row['ID'],
                'symbol': row['SYMBOL'],
                'name': row['NAME'],
                'number_of_transactions': row['NUMBER_OF_TRANSACTIONS'],
                'traded_value': row['TRADED_VALUE'],
                'per': row['PER'],
                'percent_global_traded_value': row['PERCENT_GLOBAL_TRADED_VALUE'],
                'update_date': row['UPDATE_DATE']
            }
        )

print("✅ Volume data successfully inserted into 'volumes' table.")

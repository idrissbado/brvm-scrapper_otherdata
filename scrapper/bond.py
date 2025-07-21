import os
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de la connexion à PostgreSQL
target_postgres_engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Configuration options Chrome pour Docker headless
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

# Définir explicitement le chemin du binaire Chromium
options.binary_location = os.getenv('CHROME_BIN', '/usr/bin/chromium')

# Chemin du chromedriver
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/lib/chromium/chromedriver")

# Initialisation du driver Chrome
driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)

# URL à scraper (obligations)
url = "https://www.brvm.org/en/cours-obligations/0"
driver.get(url)

# Attendre que le tableau soit chargé (max 10s)
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr"))
)

# Récupérer les lignes du tableau
rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")

# Extraction des données
data = []
for row in rows:
    cols = row.find_elements(By.TAG_NAME, "td")
    if len(cols) >= 7:
        symbol = cols[0].text.strip()
        name = cols[1].text.strip()
        issue_date = cols[2].text.strip()
        maturity_date = cols[3].text.strip()
        daily_price = cols[4].text.strip().replace('\xa0', ' ').replace(',', '.')
        interest = cols[5].text.strip().replace('\xa0', ' ').replace(',', '.')
        last_payment = cols[6].text.strip()
        data.append([symbol, name, issue_date, maturity_date, daily_price, interest, last_payment])

driver.quit()

df = pd.DataFrame(data, columns=[
    "SYMBOL", "NAME", "ISSUE_DATE", "MATURITY_DATE", "DAILY_PRICE", "INTEREST", "LAST_PAYMENT_DATE_VALUE"
])

# Nettoyage des colonnes numériques
for col in ["DAILY_PRICE", "INTEREST"]:
    df[col] = df[col].str.replace(' ', '').astype(float)

# Extraction détails obligations
def extract_bond_details(name):
    try:
        match = re.search(r'^(.*?)\s+(\d+[,.]\d+)%\s+(\d{4})-(\d{4})$', str(name))
        if match:
            return pd.Series({
                'BOND_TYPE': match.group(1).strip(),
                'COUPON_RATE': float(match.group(2).replace(',', '.')),
                'ISSUE_YEAR': int(match.group(3)),
                'MATURITY_YEAR': int(match.group(4))
            })
        alt_match = re.search(r'^(.*?)\s+(\d+[,.]\d+)%\s+(\d{4})\s*-\s*(\d{4})$', str(name))
        if alt_match:
            return pd.Series({
                'BOND_TYPE': alt_match.group(1).strip(),
                'COUPON_RATE': float(alt_match.group(2).replace(',', '.')),
                'ISSUE_YEAR': int(alt_match.group(3)),
                'MATURITY_YEAR': int(alt_match.group(4))
            })
    except:
        pass
    return pd.Series({'BOND_TYPE': None, 'COUPON_RATE': None, 'ISSUE_YEAR': None, 'MATURITY_YEAR': None})

bond_details = df['NAME'].apply(extract_bond_details)
df = pd.concat([df, bond_details], axis=1)

df['ISSUE_YEAR'] = df['ISSUE_YEAR'].astype('Int64')
df['MATURITY_YEAR'] = df['MATURITY_YEAR'].astype('Int64')

# Extraction détails paiement
def extract_payment_details(payment_str):
    try:
        if pd.isna(payment_str):
            return pd.Series({'LAST_PAYMENT_DATE_ONLY': None, 'LAST_PAYMENT_VALUE': None})
        parts = payment_str.split(' / ')
        value = float(parts[1].replace(',', '.').strip()) if len(parts) > 1 and parts[1].strip() else None
        return pd.Series({
            'LAST_PAYMENT_DATE_ONLY': pd.to_datetime(parts[0].strip(), format='%m/%d/%Y', errors='coerce'),
            'LAST_PAYMENT_VALUE': value
        })
    except:
        return pd.Series({'LAST_PAYMENT_DATE_ONLY': None, 'LAST_PAYMENT_VALUE': None})

payment_details = df['LAST_PAYMENT_DATE_VALUE'].apply(extract_payment_details)
df = pd.concat([df, payment_details], axis=1)

df = (df
        .drop(columns=['MATURITY_DATE', 'LAST_PAYMENT_DATE_VALUE'])
        .rename(columns={
            'MATURITY_YEAR': 'MATURITY_DATE',
            'LAST_PAYMENT_DATE_ONLY': 'LAST_PAYMENT_DATE',
            'LAST_PAYMENT_VALUE': 'VALUE'
        }))

# Création ID unique obligation
def create_bond_id(row):
    try:
        bond_type = str(row['BOND_TYPE']).replace(' ', '')
        payment_date = str(row['LAST_PAYMENT_DATE']).replace(' ', '')
        return f"{bond_type}-{payment_date}"
    except:
        return None

df['ID'] = df.apply(create_bond_id, axis=1)

def clean_data(value):
    return None if pd.isna(value) else value

df = df.rename(columns={
    'SYMBOL': 'symbol',
    'NAME': 'name',
    'ISSUE_DATE': 'issue_date',
    'DAILY_PRICE': 'daily_price',
    'INTEREST': 'interest',
    'LAST_PAYMENT_DATE': 'last_payment_date',
    'VALUE': 'value'
})

date_cols = ['issue_date', 'maturity_date', 'last_payment_date']
for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce')
    df[col] = df[col].dt.strftime('%Y-%m-%d').replace('NaT', None)

numeric_cols = ['daily_price', 'interest', 'value', 'coupon_rate']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].apply(clean_data)

if 'ISSUE_YEAR' in df.columns:
    df['ISSUE_YEAR'] = df['ISSUE_YEAR'].astype('Int64').astype(object).where(df['ISSUE_YEAR'].notna(), None)

# Requête d'insertion PostgreSQL avec gestion des conflits (upsert)
insert_query = """
INSERT INTO obligations (
    id, symbol, name, issue_date, maturity_date, 
    daily_price, interest, last_payment_date, value,
    coupon_rate, issue_year, bond_type
) VALUES (
    :id, :symbol, :name, :issue_date, :maturity_date,
    :daily_price, :interest, :last_payment_date, :value,
    :coupon_rate, :issue_year, :bond_type
)
ON CONFLICT (id) DO UPDATE SET
    symbol = EXCLUDED.symbol,
    name = EXCLUDED.name,
    issue_date = EXCLUDED.issue_date,
    maturity_date = EXCLUDED.maturity_date,
    daily_price = EXCLUDED.daily_price,
    interest = EXCLUDED.interest,
    last_payment_date = EXCLUDED.last_payment_date,
    value = EXCLUDED.value,
    coupon_rate = EXCLUDED.coupon_rate,
    issue_year = EXCLUDED.issue_year,
    bond_type = EXCLUDED.bond_type
"""

# Insertion des données dans la base
with target_postgres_engine.begin() as connection:
    for _, row in df.iterrows():
        params = {
            'id': clean_data(row['ID']),
            'symbol': clean_data(row['symbol']),
            'name': clean_data(row['name']),
            'issue_date': clean_data(row['issue_date']),
            'maturity_date': clean_data(row['maturity_date']),
            'daily_price': clean_data(row['daily_price']),
            'interest': clean_data(row['interest']),
            'last_payment_date': clean_data(row['last_payment_date']),
            'value': clean_data(row['value']),
            'coupon_rate': clean_data(row['COUPON_RATE']),
            'issue_year': clean_data(row['ISSUE_YEAR']),
            'bond_type': clean_data(row['BOND_TYPE'])
        }
        connection.execute(text(insert_query), params)

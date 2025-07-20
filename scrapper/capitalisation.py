import os
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Database connection parameters
target_db_params_postgres = {
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

# Configure headless Chrome
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Scrape URL
url = "https://www.brvm.org/en/capitalisations/0"
driver.get(url)
time.sleep(7)

# Try to extract the last update date
try:
    last_update_elem = driver.find_element(By.XPATH, "//*[contains(text(),'Last update')]")
    last_update_text = last_update_elem.text.strip()
except:
    last_update_text = "Unknown update date"

# Use regex to extract date
update_date = None
match = re.search(r"Last update:\s*(.*)", last_update_text)
if match:
    update_date = match.group(1)

# Table extraction
rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
print(f"Found {len(rows)} rows")

data = []
for row in rows:
    cols = row.find_elements(By.TAG_NAME, "td")
    if len(cols) >= 7:
        symbol = cols[0].text.strip()
        name = cols[1].text.strip()
        number_of_shares = cols[2].text.strip().replace('\xa0', '').replace(' ', '')
        daily_price = cols[3].text.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        floating_cap = cols[4].text.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        global_cap = cols[5].text.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        global_cap_pct = cols[6].text.strip().replace('%', '').replace(',', '.')
        data.append([
            symbol, name, number_of_shares, daily_price,
            floating_cap, global_cap, global_cap_pct
        ])

driver.quit()

# Convert to DataFrame
df = pd.DataFrame(data, columns=[
    "SYMBOL", "NAME", "NUMBER_OF_SHARES", "DAILY_PRICE",
    "FLOATING_CAPITALIZATION", "GLOBAL_CAPITALIZATION", "GLOBAL_CAPITALIZATION_PERCENT"
])

# Convert numeric fields
for col in ["NUMBER_OF_SHARES", "DAILY_PRICE", "FLOATING_CAPITALIZATION", "GLOBAL_CAPITALIZATION", "GLOBAL_CAPITALIZATION_PERCENT"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Process UPDATE_DATE
df["UPDATE_DATE"] = pd.to_datetime(update_date, errors='coerce')
if df["UPDATE_DATE"].isnull().all():
    df["UPDATE_DATE"] = pd.Timestamp.today().normalize()
else:
    df["UPDATE_DATE"] = df["UPDATE_DATE"].fillna(df["UPDATE_DATE"].mode()[0])

df["UPDATE_DATE"] = df["UPDATE_DATE"].dt.strftime('%Y-%m-%d')
df["ID"] = df["SYMBOL"] + "-" + df["UPDATE_DATE"].str.replace(" ", "")
df = df.rename(columns={"GLOBAL_CAPITALIZATION_PERCENT": "GLOBAL_CAPITALIZATION_PER"})

# Connect to DB
engine = create_engine(
    f"postgresql://{target_db_params_postgres['user']}:{target_db_params_postgres['password']}@"
    f"{target_db_params_postgres['host']}:{target_db_params_postgres['port']}/"
    f"{target_db_params_postgres['database']}",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Insert in batches
def batch_insert(df, batch_size=1000, max_retries=3):
    insert_query = text("""
        INSERT INTO capitalisation (
            id, symbol, name, number_of_shares, daily_price,
            floating_capitalization, global_capitalization,
            global_capitalization_per, update_date
        ) VALUES (
            :id, :symbol, :name, :number_of_shares, :daily_price,
            :floating_capitalization, :global_capitalization,
            :global_capitalization_per, :update_date
        )
        ON CONFLICT (id) DO UPDATE SET
            symbol = EXCLUDED.symbol,
            name = EXCLUDED.name,
            number_of_shares = EXCLUDED.number_of_shares,
            daily_price = EXCLUDED.daily_price,
            floating_capitalization = EXCLUDED.floating_capitalization,
            global_capitalization = EXCLUDED.global_capitalization,
            global_capitalization_per = EXCLUDED.global_capitalization_per,
            update_date = EXCLUDED.update_date
    """)
    with engine.begin() as connection:
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            for retry in range(max_retries):
                try:
                    for _, row in batch.iterrows():
                        connection.execute(insert_query, {
                            'id': row['ID'],
                            'symbol': row['SYMBOL'],
                            'name': row['NAME'],
                            'number_of_shares': row['NUMBER_OF_SHARES'],
                            'daily_price': row['DAILY_PRICE'],
                            'floating_capitalization': row['FLOATING_CAPITALIZATION'],
                            'global_capitalization': row['GLOBAL_CAPITALIZATION'],
                            'global_capitalization_per': row['GLOBAL_CAPITALIZATION_PER'],
                            'update_date': row['UPDATE_DATE']
                        })
                    break
                except OperationalError:
                    if retry == max_retries - 1:
                        raise
                    time.sleep(2 ** retry)

# Run the batch insert
batch_insert(df)
print("✅ Data inserted/updated successfully")

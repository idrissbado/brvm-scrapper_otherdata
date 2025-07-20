import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection via SQLAlchemy
target_postgres_engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Setup headless browser
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# URL to scrape index data
url = "https://www.brvm.org/en/indices"
driver.get(url)
time.sleep(5)  # wait for JavaScript to render

# Find index tables
tables = driver.find_elements(By.CSS_SELECTOR, "table.table")

index_data = []
for table in tables:
    rows = table.find_elements(By.TAG_NAME, "tr")
    for row in rows[1:]:  # Skip header
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 5:
            name = cols[0].text.strip()
            prev_close = cols[1].text.strip()
            close = cols[2].text.strip()
            change_pct = cols[3].text.strip().replace('%', '')
            ytd_change = cols[4].text.strip().replace('%', '')
            index_data.append([name, prev_close, close, change_pct, ytd_change])

# Close browser
driver.quit()

# Convert to DataFrame
df = pd.DataFrame(index_data, columns=[
    "INDEX_NAME", "PREVIOUS_CLOSE", "CLOSE", "CHANGE_PERCENT", "YTD_CHANGE_PERCENT"
])

# Clean numeric columns
for col in ["PREVIOUS_CLOSE", "CLOSE", "CHANGE_PERCENT", "YTD_CHANGE_PERCENT"]:
    df[col] = df[col].str.replace(' ', '').str.replace(',', '.').astype(float)

# Add update date
df["UPDATE_DATE"] = pd.Timestamp.today().normalize()

# Create unique ID
df["ID"] = df["INDEX_NAME"] + '-' + df["UPDATE_DATE"].dt.strftime('%Y-%m-%d')

# Rename columns to match database schema
data = df.rename(columns={
    'INDEX_NAME': 'index_name',
    'PREVIOUS_CLOSE': 'previous_close',
    'CLOSE': 'close',
    'CHANGE_PERCENT': 'change_percent',
    'YTD_CHANGE_PERCENT': 'ytd_change_percent',
    'UPDATE_DATE': 'update_date',
    'ID': 'id'
})

# Insert query with upsert logic
insert_query = """
INSERT INTO indexes (
    id, index_name, previous_close, close, 
    change_percent, ytd_change_percent, update_date
) VALUES (
    :id, :index_name, :previous_close, :close,
    :change_percent, :ytd_change_percent, :update_date
)
ON CONFLICT (id) DO UPDATE SET
    index_name = EXCLUDED.index_name,
    previous_close = EXCLUDED.previous_close,
    close = EXCLUDED.close,
    change_percent = EXCLUDED.change_percent,
    ytd_change_percent = EXCLUDED.ytd_change_percent,
    update_date = EXCLUDED.update_date
"""

# Execute insert
with target_postgres_engine.begin() as connection:
    for _, row in data.iterrows():
        connection.execute(text(insert_query), {
            'id': row['id'],
            'index_name': row['index_name'],
            'previous_close': float(row['previous_close']) if pd.notna(row['previous_close']) else None,
            'close': float(row['close']) if pd.notna(row['close']) else None,
            'change_percent': float(row['change_percent']) if pd.notna(row['change_percent']) else None,
            'ytd_change_percent': float(row['ytd_change_percent']) if pd.notna(row['ytd_change_percent']) else None,
            'update_date': row['update_date']
        })

print("✅ Index data successfully inserted into 'indexes' table.")

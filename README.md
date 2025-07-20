# BRVM Market Data Scraper

This project contains Python scripts to scrape financial market data from the BRVM (Bourse Régionale des Valeurs Mobilières) website. It extracts and processes data about bonds, capitalisation, indexes, and trading volumes.

---

## Project Structure

```bash 
├── scrapper/
│ ├── bond.py
│ ├── capitalisation.py
│ ├── index.py
│ └── volume.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Description of Scripts

- **bond.py**  
  Scrapes bond market data: bond symbols, issue dates, prices, coupon rates, maturity dates, last payment info, and inserts it into the database.

- **capitalisation.py**  
  Scrapes market capitalisation data for companies listed on BRVM.

- **index.py**  
  Scrapes BRVM indexes, including index names, previous close, current close, daily and year-to-date percentage changes.

- **volume.py**  
  Scrapes volume trading data: symbols, number of transactions, traded values, and percent contribution to the global traded value.

---

## Prerequisites

- Python 3.8 or higher  
- Docker and Docker Compose (optional but recommended)  
- PostgreSQL or compatible database

---

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/idrissbado/brvm-scrapper_otherdata
cd brvm-scrapper_otherdata
## Install Python dependencies

```bash
pip install -r requirements.txt
# BRVM Scrapers
```
## Setup environment variables

Create a `.env` file with your database connection details:

```env
DATABASE_URL=postgresql://username:password@host:port/dbname
```
## Usage

### Running scripts locally

Run any individual scraper:

```bash
python scrapper/bond.py
python scrapper/capitalisation.py
python scrapper/index.py
python scrapper/volume.py
```
## Running with Docker

Build and start the container to run all scrapers sequentially:

```bash
docker-compose up --build

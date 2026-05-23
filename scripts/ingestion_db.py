"""Load CSV files from data/ into the local SQLite database."""

import logging
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "inventory.db"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "ingestion_db.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

engine = create_engine(f"sqlite:///{DB_PATH}")


def ingest_db(df, table_name, engine):
    """Ingest a dataframe into a database table."""
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)


def load_raw_data():
    """Load all CSV files from the data folder and save them to SQLite."""
    if not DATA_DIR.is_dir():
        logging.warning("Data folder not found. Create a data/ folder and add the CSV files first.")
        return

    csv_files = [file_name for file_name in DATA_DIR.iterdir() if file_name.name.lower().endswith(".csv")]
    if not csv_files:
        logging.warning("No CSV files found in data/.")
        return

    start = time.time()
    for file_name in csv_files:
        df = pd.read_csv(file_name)
        logging.info("Ingesting %s into SQLite", file_name.name)
        ingest_db(df, file_name.stem, engine)

    end = time.time()
    total_time = (end - start) / 60
    logging.info("-------------- Ingestion Complete --------------")
    logging.info("Total Time Taken: %.2f minutes", total_time)


if __name__ == "__main__":
    load_raw_data()

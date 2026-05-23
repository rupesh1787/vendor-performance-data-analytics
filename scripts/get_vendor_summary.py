"""Build the vendor summary table from the SQLite source tables."""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "inventory.db"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "get_vendor_summary.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)


def ingest_db(df, table_name, engine):
    """Ingest the dataframe into a database table."""
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)


def create_vendor_summary(conn):
    """Merge source tables into a vendor-level performance summary."""
    vendor_sales_summary = pd.read_sql_query("""WITH FreightSummary AS (
        SELECT 
            VendorNumber, 
            SUM(Freight) AS FreightCost 
        FROM vendor_invoice 
        GROUP BY VendorNumber
    ), 
    
    PurchaseSummary AS (
        SELECT 
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Price AS ActualPrice,
            pp.Volume,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases p
        JOIN purchase_prices pp
            ON p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, pp.Price, pp.Volume
    ), 
    
    SalesSummary AS (
        SELECT 
            VendorNo,
            Brand,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    ) 
    
    SELECT 
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss 
        ON ps.VendorNumber = ss.VendorNo 
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs 
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC""",conn)

    return vendor_sales_summary


def clean_data(df):
    """Clean the summary table and add derived KPI columns."""
    df["Volume"] = df["Volume"].astype("float")
    df.fillna(0, inplace=True)
    df["VendorName"] = df["VendorName"].str.strip()
    df["Description"] = df["Description"].str.strip()

    df["GrossProfit"] = df["TotalSalesDollars"] - df["TotalPurchaseDollars"]
    df["ProfitMargin"] = (df["GrossProfit"] / df["TotalSalesDollars"]) * 100
    df["StockTurnover"] = df["TotalSalesQuantity"] / df["TotalPurchaseQuantity"]
    df["SalesToPurchaseRatio"] = df["TotalSalesDollars"] / df["TotalPurchaseDollars"]

    return df

if __name__ == "__main__":
    conn = sqlite3.connect(str(DB_PATH))

    logging.info("Creating vendor summary table...")
    summary_df = create_vendor_summary(conn)
    logging.info(summary_df.head())

    logging.info("Cleaning data...")
    clean_df = clean_data(summary_df)
    logging.info(clean_df.head())

    logging.info("Ingesting summary data...")
    ingest_db(clean_df, "vendor_sales_summary", conn)
    logging.info("Completed")
    conn.close()
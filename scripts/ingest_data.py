# scripts/ingest_data.py
import pandas as pd
from sqlalchemy import create_engine
import os

CSV_FILE_PATH = os.path.join('data', 'sample_sales.csv')
DB_FILE_PATH = os.path.join('data', 'analytics.db')
TABLE_NAME = 'sales_data'

# Create a SQLAlchemy engine for SQLite
engine = create_engine(f'sqlite:///{DB_FILE_PATH}')

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    print("Cleaning data...")
    df.columns = [col.lower() for col in df.columns]
    df['orderdate'] = pd.to_datetime(df['orderdate'])
    df['product'].fillna('Unknown', inplace=True)
    df['units'] = df['units'].abs().astype(int)
    df['total_revenue'] = df['units'] * df['saleprice']
    print("Data cleaning complete.")
    return df

def ingest_data():
    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        return

    print(f"Reading data from {CSV_FILE_PATH}...")
    df = pd.read_csv(CSV_FILE_PATH)
    cleaned_df = clean_data(df)

    print(f"Ingesting data into SQLite database at {DB_FILE_PATH}...")
    # Use pandas.to_sql with the SQLAlchemy engine
    cleaned_df.to_sql(TABLE_NAME, engine, if_exists='replace', index=False)

    print(f"✅ Data successfully ingested into the '{TABLE_NAME}' table.")

if __name__ == "__main__":
    ingest_data()
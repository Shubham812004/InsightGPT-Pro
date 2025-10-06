import duckdb
import os

DB_FILE_PATH = os.path.join('data', 'analytics.db')
TABLE_NAME = 'sales_data'

con = duckdb.connect(database=DB_FILE_PATH, read_only=True)
result = con.execute(f"SELECT * FROM {TABLE_NAME} LIMIT 5").fetchdf()
con.close()

print(f"Successfully queried the '{TABLE_NAME}' table. Here's a sample:")
print(result)
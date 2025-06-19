import os
import csv
import mysql.connector
import getpass
from tqdm import tqdm

# Prompt for password
mysql_password = getpass.getpass("Enter MySQL password: ")

# MySQL connection configuration
config = {
    'host': 'localhost',
    'user': 'root',
    'password': mysql_password,
    'auth_plugin': 'mysql_native_password',
}

# Schemas and tables to export
schemas = [
    '2025_05_01_performance_osu_random_10000',
    '2025_05_01_performance_osu_top_10000'
]
tables = ['users', 'scores_high', 'beatmaps']

# Output directory
export_dir = os.path.join(os.path.dirname(__file__), 'export')
os.makedirs(export_dir, exist_ok=True)

# Export one table to CSV (streaming, memory-efficient)
def export_table_to_csv(cursor, schema, table):
    cursor.execute(f"USE `{schema}`")
    cursor.execute(f"SELECT * FROM `{table}`")

    headers = [desc[0] for desc in cursor.description]
    filename = f"{schema}__{table}.csv"
    filepath = os.path.join(export_dir, filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        row_count = 0
        for row in tqdm(cursor, desc=f"{schema}.{table}", leave=False):
            writer.writerow(row)
            row_count += 1

    tqdm.write(f"✅ Exported {schema}.{table} ({row_count} rows) to {filename}")

# Main export routine
def main():
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor(buffered=False)  # non-buffered for streaming

    for schema in tqdm(schemas, desc="Schemas", position=0):
        for table in tqdm(tables, desc=f"Tables in {schema}", position=1, leave=False):
            export_table_to_csv(cursor, schema, table)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

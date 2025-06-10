import os
import csv
import mysql.connector
import getpass
from tqdm import tqdm

# prompt for password
mysql_password = getpass.getpass("Enter MySQL password: ")

config = {
    'host': 'localhost',
    'user': 'root',
    'password': mysql_password,
    'auth_plugin': 'mysql_native_password',
}

schemas = [
    '2025_05_01_performance_osu_random_10000',
    '2025_05_01_performance_osu_top_10000'
]
tables = ['users', 'scores_high', 'beatmaps']
export_dir = os.path.join(os.path.dirname(__file__), 'export')
os.makedirs(export_dir, exist_ok=True)

def export_table_to_csv(cursor, schema, table):
    cursor.execute(f"USE `{schema}`")
    cursor.execute(f"SELECT * FROM `{table}`")
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]

    filename = f"{schema}__{table}.csv"
    filepath = os.path.join(export_dir, filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    tqdm.write(f"✅ Exported {schema}.{table} ({len(rows)} rows) to {filename}")

def main():
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    for schema in tqdm(schemas, desc="Schemas", position=0):
        for table in tqdm(tables, desc=f"Tables in {schema}", position=1, leave=False):
            export_table_to_csv(cursor, schema, table)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()


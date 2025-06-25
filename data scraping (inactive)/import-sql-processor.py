import os
import duckdb
import re
import chardet
from tqdm import tqdm

# Paths
sql_folder = os.path.join("Data", "import")
db_folder = os.path.join("Data", "import-processed")
os.makedirs(db_folder, exist_ok=True)

# Clean MySQL-specific syntax
def clean_mysql_sql(sql: str) -> str:
    sql = re.sub(r"`([^`]*)`", r"\1", sql)  # remove backticks
    sql = re.sub(r"AUTO_INCREMENT", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"UNSIGNED", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"ENGINE\s*=\s*\w+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"DEFAULT CHARSET=\w+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"COLLATE\s+\w+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"CHARACTER SET\s+\w+", "", sql, flags=re.IGNORECASE)
    return sql


# Collect SQL files
sql_file_paths = []
for root, _, files in os.walk(sql_folder):
    for file in files:
        if file.endswith(".sql"):
            sql_file_paths.append(os.path.join(root, file))

# Process files
for sql_path in tqdm(sql_file_paths, desc="Processing .sql files"):
    rel_path = os.path.relpath(sql_path, sql_folder)
    db_name = os.path.splitext(os.path.basename(sql_path))[0]
    db_output_dir = os.path.join(db_folder, os.path.dirname(rel_path))
    os.makedirs(db_output_dir, exist_ok=True)
    db_path = os.path.join(db_output_dir, f"{db_name}.duckdb")

    # Try reading the file with encoding detection
    try:
        with open(sql_path, "rb") as f:
            raw = f.read()
        encoding = chardet.detect(raw)['encoding'] or 'utf-8'
        try:
            sql_text = raw.decode(encoding)
        except UnicodeDecodeError:
            sql_text = raw.decode("latin1")  # fallback for weird encodings
    except Exception as e:
        print(f"[ERROR] Reading {sql_path}: {e}")
        continue

    # Clean SQL syntax
    sql_text = clean_mysql_sql(sql_text)

    # Run in DuckDB
    try:
        con = duckdb.connect(db_path)
        con.execute(sql_text)
        con.close()
    except Exception as e:
        print(f"[ERROR] DuckDB failed for {sql_path}: {e}")

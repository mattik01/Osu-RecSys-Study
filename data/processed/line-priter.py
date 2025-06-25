import os
import csv

# Absolute path of the current directory
folder_path = os.path.abspath(os.path.dirname(__file__))

# Iterate over all CSV files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith('.csv'):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            line_count = sum(1 for _ in reader) - 1  # Subtract 1 for header
        print(f"{file_path}: {line_count} lines")

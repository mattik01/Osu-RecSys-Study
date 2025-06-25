
import os
import pandas as pd

# ============================================
# CONFIGURATION SECTION
# ============================================

# Folder paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_DIR = os.path.join(SCRIPT_DIR, "splits")

# Dataset variants
VARIANTS = [
    ("top", "enjoyment"),
    ("top", "playcount"),
    ("random", "enjoyment"),
    ("random", "playcount")
]

N_FOLDS = 3

# ============================================

def prepare_folds(df, n_folds):
    from sklearn.model_selection import KFold
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    return [(df.iloc[train_idx], df.iloc[val_idx]) for train_idx, val_idx in kf.split(df)]

def print_dataset_stats():
    stats = []

    for user_type, rating_type in VARIANTS:
        prefix = f"{user_type}_{rating_type}"
        csv_path = os.path.join(SPLIT_DIR, f"{prefix}_train.csv")

        df = pd.read_csv(csv_path)
        df = df[df['rating'] > 0.0]
        df = df.groupby("user_id").filter(lambda x: len(x) >= 20)

        unique_users = df['user_id'].nunique()
        unique_items = df['mod_beatmap_id'].nunique()
        total_interactions = len(df)

        stats.append((prefix, unique_users, unique_items, total_interactions))

    print("\n=== Dataset Statistics ===")
    for prefix, n_users, n_items, n_interactions in stats:
        print(f"{prefix:<25} | Users: {n_users:<5} | Items: {n_items:<6} | Interactions: {n_interactions}")
    print("===========================")

if __name__ == '__main__':
    print_dataset_stats()

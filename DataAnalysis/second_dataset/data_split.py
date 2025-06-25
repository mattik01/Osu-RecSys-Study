import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from tqdm import tqdm
from joblib import Parallel, delayed
import multiprocessing

# 1) Load Instacart data directly from local CSVs in data/archive/
orders   = pd.read_csv("../../data/archive/orders.csv", usecols=['order_id','user_id'])
op_train = pd.read_csv("../../data/archive/order_products__train.csv", usecols=['order_id','product_id'])

# 2) Build implicit-feedback DataFrame
scores = (
    op_train
    .merge(orders, on='order_id', how='inner')
    .loc[:, ['user_id','product_id']]
    .assign(rating=1.0)
    .astype({'user_id': str, 'product_id': str, 'rating': float})
)
print(f"[INFO] Loaded {len(scores)} interactions")

# 3) Train/Val/Test split logic per user
def split_user_df(user_df):
    if len(user_df) < 3:
        return {'train': user_df, 'val': None, 'test': None}
    tv, test  = train_test_split(user_df, test_size=0.2, random_state=42)
    train, val = train_test_split(tv, test_size=0.25, random_state=42)
    return {'train': train, 'val': val, 'test': test}

def normalize(df, col):
    mn, mx = df[col].min(), df[col].max()
    df[col] = 0.0 if mn == mx else (df[col] - mn) / (mx - mn)
    return df

OUTPUT_DIR = "./generated_splits_instacart"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def split_and_save(scores_df):
    print("[INFO] Splitting by user")
    groups = list(scores_df.groupby('user_id'))
    print(f"  - Users: {len(groups)}")
    num_cores = multiprocessing.cpu_count()

    results = Parallel(n_jobs=num_cores)(
        delayed(split_user_df)(grp) for _, grp in tqdm(groups, desc="Users", unit="user")
    )
    splits = {'train': [], 'val': [], 'test': []}
    for r in results:
        for k in splits:
            if r[k] is not None:
                splits[k].append(r[k])

    for split_name, dfs in splits.items():
        if not dfs:
            continue
        df_big = pd.concat(dfs, ignore_index=True)
        print(f"[INFO] {split_name.upper()} size = {len(df_big)}")
        df_norm = normalize(df_big[['user_id','product_id','rating']].copy(), 'rating')
        out_file = os.path.join(OUTPUT_DIR, f"instacart_{split_name}.csv")
        df_norm.to_csv(out_file, index=False)
        print(f"  -> Wrote {out_file}")

if __name__ == "__main__":
    split_and_save(scores)

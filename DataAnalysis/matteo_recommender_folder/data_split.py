import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from tqdm import tqdm
from joblib import Parallel, delayed
import multiprocessing

# Paths to data
DATA_VARIANTS = {
    "top": {
        "scores": "data/processed/top_10000__scores.csv",
        "users": "data/processed/top_10000__users.csv"
    },
    "random": {
        "scores": "data/processed/random_10000__scores.csv",
        "users": "data/processed/random_10000__users.csv"
    }
}

OUTPUT_DIR = "./generated_splits_cf"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_filtered_scores(user_type: str):
    print(f"[INFO] Loading scores for user type: {user_type}")
    scores_path = DATA_VARIANTS[user_type]["scores"]
    users_path = DATA_VARIANTS[user_type]["users"]

    users = (
        pd.read_csv(users_path, usecols=['user_id', 'skill_stabilization_date'], parse_dates=['skill_stabilization_date'])
        .set_index('user_id')
    )

    usecols = ['user_id', 'mod_beatmap_id', 'date', 'enjoyment', 'playcount']
    dtype = {'user_id': np.int32, 'enjoyment': np.float32, 'playcount': np.float32}
    conv = {'mod_beatmap_id': lambda x: np.int64(float(x))}

    scores = pd.read_csv(scores_path, usecols=usecols, dtype=dtype, converters=conv, parse_dates=['date'])
    scores = scores.join(users, on='user_id', how='inner')
    del users

    before = len(scores)
    scores = scores[scores['date'] >= scores['skill_stabilization_date']]
    print(f"  - Filtered {before - len(scores)} pre-stabilization scores. Remaining: {len(scores)}")

    return scores[['user_id', 'mod_beatmap_id', 'enjoyment', 'playcount']].copy()


def split_user_df(user_df):
    if len(user_df) < 3:
        return {'train': user_df, 'val': None, 'test': None}
    train_val, test = train_test_split(user_df, test_size=0.2, random_state=42)
    train, val = train_test_split(train_val, test_size=0.25, random_state=42)
    return {'train': train, 'val': val, 'test': test}


def normalize(df, colname):
    min_r, max_r = df[colname].min(), df[colname].max()
    if min_r == max_r:
        df[colname] = 0.0
    else:
        df[colname] = (df[colname] - min_r) / (max_r - min_r)
    return df


def split_and_save_dual(scores_df, name_prefix):
    print(f"[INFO] Splitting and saving {name_prefix} data (shared splits for enjoyment & playcount)")
    grouped = list(scores_df.groupby('user_id'))
    print(f"  - Total users: {len(grouped)}")
    num_cores = multiprocessing.cpu_count()

    results = Parallel(n_jobs=num_cores)(
        delayed(split_user_df)(group) for _, group in tqdm(grouped, desc=f"Splitting {name_prefix}", unit="user")
    )

    sets = {'train': [], 'val': [], 'test': []}
    for split_result in results:
        for k in sets:
            if split_result[k] is not None:
                sets[k].append(split_result[k])

    for split_name in sets:
        split_df = pd.concat(sets[split_name])
        print(f"  - Normalizing and saving: {split_name} (n={len(split_df)})")

        # Save for enjoyment
        enjoyment_df = normalize(split_df[['user_id', 'mod_beatmap_id', 'enjoyment']].rename(columns={'enjoyment': 'rating'}), 'rating')
        enjoyment_df.to_csv(f"{OUTPUT_DIR}/{name_prefix}_enjoyment_{split_name}.csv", index=False)

        # Save for playcount
        playcount_df = normalize(split_df[['user_id', 'mod_beatmap_id', 'playcount']].rename(columns={'playcount': 'rating'}), 'rating')
        playcount_df.to_csv(f"{OUTPUT_DIR}/{name_prefix}_playcount_{split_name}.csv", index=False)


if __name__ == '__main__':
    for user_type in ["top", "random"]:
        print(f"\n=== PROCESSING: {user_type.upper()} USERS ===")
        scores = load_filtered_scores(user_type)
        split_and_save_dual(scores, user_type)
        del scores

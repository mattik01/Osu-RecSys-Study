import os
import pandas as pd
import numpy as np
from tqdm import tqdm

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


def normalize(df, colname):
    min_r, max_r = df[colname].min(), df[colname].max()
    if min_r == max_r:
        df[colname] = 0.0
    else:
        df[colname] = (df[colname] - min_r) / (max_r - min_r)
    return df


def save_single_train_split(scores_df, name_prefix):
    print(f"[INFO] Saving single train split for: {name_prefix}")

    # Save for enjoyment
    enjoyment_df = normalize(scores_df[['user_id', 'mod_beatmap_id', 'enjoyment']].rename(columns={'enjoyment': 'rating'}), 'rating')
    enjoyment_df.to_csv(f"{OUTPUT_DIR}/{name_prefix}_enjoyment_train.csv", index=False)

    # Save for playcount
    playcount_df = normalize(scores_df[['user_id', 'mod_beatmap_id', 'playcount']].rename(columns={'playcount': 'rating'}), 'rating')
    playcount_df.to_csv(f"{OUTPUT_DIR}/{name_prefix}_playcount_train.csv", index=False)


if __name__ == '__main__':
    for user_type in ["top", "random"]:
        print(f"\n=== PROCESSING: {user_type.upper()} USERS ===")
        scores = load_filtered_scores(user_type)
        save_single_train_split(scores, user_type)
        del scores

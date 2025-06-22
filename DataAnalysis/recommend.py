import numpy as np
import pandas as pd
from tqdm import tqdm
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split


def load_scores_sampled(score_paths, sample_frac=0.05, chunksize=1_000_000):
    """
    Load and sample score CSV files in chunks, with progress reporting.
    sample_frac: fraction of rows to keep from each chunk.
    """
    usecols = ['user_id', 'mod_beatmap_id', 'pp']
    dtype = {'user_id': np.int32, 'pp': np.float32}
    converters = {'mod_beatmap_id': lambda x: np.int64(float(x))}

    sampled_chunks = []
    for path in score_paths:
        total = 0
        for chunk in pd.read_csv(
                path,
                usecols=usecols,
                dtype=dtype,
                converters=converters,
                chunksize=chunksize,
                iterator=True
        ):
            # sample this chunk
            chunk_sample = chunk.sample(frac=sample_frac, random_state=42)
            sampled_chunks.append(chunk_sample)
            total += len(chunk_sample)
            tqdm.write(f"Sampled {len(chunk_sample)} rows (cum. {total}) from {path}")

    # Concatenate sampled data
    sampled_scores = pd.concat(sampled_chunks, ignore_index=True)
    return sampled_scores


def prepare_surprise_data(scores, user_col='user_id', item_col='mod_beatmap_id', rating_col='pp'):
    reader = Reader(rating_scale=(scores[rating_col].min(), scores[rating_col].max()))
    data = Dataset.load_from_df(scores[[user_col, item_col, rating_col]], reader)
    return data


def train_svd(data, n_factors=20, n_epochs=5, lr_all=0.005, reg_all=0.02):
    """
    Train SVD on sampled data with fewer epochs for speed.
    """
    trainset, testset = train_test_split(data, test_size=0.2, random_state=42)
    algo = SVD(n_factors=n_factors, n_epochs=n_epochs, lr_all=lr_all, reg_all=reg_all)
    algo.fit(trainset)
    return algo, trainset


def get_top_n(algo, trainset, user_ids, n=5):
    """
    Recommend top-n items for given users,
    but limit to fewer recommendations to speed up.
    """
    all_iids = trainset.all_items()
    recs = {}
    for uid in user_ids:
        try:
            trainset.to_inner_uid(uid)
        except ValueError:
            continue
        scores = []
        for iid in all_iids:
            raw_iid = trainset.to_raw_iid(iid)
            est = algo.predict(uid, raw_iid).est
            scores.append((raw_iid, est))
        scores.sort(key=lambda x: x[1], reverse=True)
        recs[uid] = [iid for iid, _ in scores[:n]]
    return recs


if __name__ == '__main__':
    score_files = ['../data/processed/processed/random_10000__scores.csv',
                   '../data/processed/processed/top_10000__scores.csv']

    # Load a small sampled subset (~5%) to finish end-to-end in ~5 minutes
    scores = load_scores_sampled(score_files, sample_frac=0.05)
    print(f"Total sampled ratings: {len(scores)}")

    data = prepare_surprise_data(scores)
    algo, trainset = train_svd(data)

    # Limit to first 50 users for quick inference
    unique_users = scores['user_id'].unique()[:50]
    recommendations = get_top_n(algo, trainset, unique_users, n=5)

    for uid, items in recommendations.items():
        print(f"User {uid}: {items}")

    # For me, it takes like 10 min to compute
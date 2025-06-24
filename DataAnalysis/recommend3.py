import numpy as np
import pandas as pd
from tqdm import tqdm
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split, cross_validate

# Paths for random-user data
# RANDOM_SCORES = '../data/processed/random_10000__scores.csv'
# RANDOM_USERS  = '../data/processed/random_10000__users.csv'

# Paths for random-user data
RANDOM_SCORES = '../data/processed/top_10000__scores.csv'
RANDOM_USERS = '../data/processed/top_10000__users.csv'

# load user stabilization dates
users = (
    pd.read_csv(RANDOM_USERS,
                usecols=['user_id', 'skill_stabilization_date'],
                parse_dates=['skill_stabilization_date'])
    .set_index('user_id')
)


def load_random_scores(chunksize=1_000_000):
    """
    Stream random-user scores, filter by skill_stabilization_date,
    and return all post-stabilization entries.
    """
    usecols = ['user_id', 'mod_beatmap_id', 'enjoyment', 'date']
    dtype = {'user_id': np.int32, 'enjoyment': np.float32}
    conv = {'mod_beatmap_id': lambda x: np.int64(float(x))}
    df_list = []
    for chunk in tqdm(
            pd.read_csv(RANDOM_SCORES,
                        usecols=usecols,
                        dtype=dtype,
                        converters=conv,
                        parse_dates=['date'],
                        chunksize=chunksize),
            desc='Filtering scores', unit='chunk'):
        chunk = chunk.join(users, on='user_id', how='inner')
        filt = chunk[chunk['date'] >= chunk['skill_stabilization_date']]
        if not filt.empty:
            df_list.append(filt[['user_id', 'mod_beatmap_id', 'enjoyment']])
    return pd.concat(df_list, ignore_index=True)


def prepare_dataset(df):
    """Build Surprise Dataset from filtered df."""
    reader = Reader(rating_scale=(df.enjoyment.min(), df.enjoyment.max()))
    return Dataset.load_from_df(df[['user_id', 'mod_beatmap_id', 'enjoyment']], reader)


def evaluate(dataset, n_splits=5):
    algo = SVD(n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.05)
    print(f'Running {n_splits}-fold CV...')
    res = cross_validate(algo, dataset, measures=['RMSE', 'MAE'], cv=n_splits, verbose=True)
    print(f"RMSE={np.mean(res['test_rmse']):.4f}, MAE={np.mean(res['test_mae']):.4f}")


def train_and_recommend(dataset, n_users=5, n_rec=5):
    trainset, _ = train_test_split(dataset, test_size=0.2, random_state=42)
    algo = SVD(n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.05)
    algo.fit(trainset)
    users = np.unique(trainset.all_users())[:n_users]
    for uid in users:
        raw_id = trainset.to_raw_uid(uid) if hasattr(trainset, 'to_raw_uid') else uid
        preds = [(iid, algo.predict(raw_id, trainset.to_raw_iid(iid)).est)
                 for iid in trainset.all_items()]
        top = sorted(preds, key=lambda x: -x[1])[:n_rec]
        print(f"User {raw_id}: {[iid for iid, _ in top]}")


if __name__ == '__main__':
    # 1) filter
    scores = load_random_scores()
    print(f"Loaded {len(scores)} post-stabilization scores")
    # 2) prepare & evaluate
    data = prepare_dataset(scores)
    evaluate(data)
    # 3) final train + recommendations
    train_and_recommend(data)

"""
results after 20min execution:
Loaded 6296570 post-stabilization scores
Running 5-fold CV...
Evaluating RMSE, MAE of algorithm SVD on 5 split(s).

                  Fold 1  Fold 2  Fold 3  Fold 4  Fold 5  Mean    Std     
RMSE (testset)    0.7905  0.7908  0.7906  0.7912  0.7911  0.7908  0.0003  
MAE (testset)     0.6356  0.6361  0.6357  0.6364  0.6361  0.6360  0.0003  
Fit time          79.23   81.19   81.28   81.16   80.98   80.77   0.77    
Test time         17.98   16.80   18.25   16.78   16.70   17.30   0.67    
RMSE=0.7908, MAE=0.6360
"""

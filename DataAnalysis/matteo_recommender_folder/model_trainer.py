import os
import pandas as pd
import joblib
from surprise import Dataset, Reader, SVD, KNNWithMeans, BaselineOnly
from joblib import Parallel, delayed
from tqdm import tqdm

# ============================================
# CONFIGURATION SECTION
# ============================================

# Folder paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_DIR = os.path.join(SCRIPT_DIR, "splits")
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)


# Dataset variants to train models on
VARIANTS = [
    ("top", "enjoyment"),
    ("top", "playcount"),
    ("random", "enjoyment"),
    ("random", "playcount")
]

# Model configurations
MODEL_CONFIGS = {
    "svd": {
        "class": SVD,
        "kwargs": {
            "n_factors": 50,
            "n_epochs": 20,
            "lr_all": 0.005,
            "reg_all": 0.02
        }
    },
    "knn": {
        "class": KNNWithMeans,
        "kwargs": {
            "k": 40,
            "sim_options": {
                    "name": "pearson_baseline",    #better for our ratings, also no zero division errors
                    "user_based": True  # item is bad idea with so many more items than users
            }
        }
    },
    "baseline": {
        "class": BaselineOnly,
        "kwargs": {
            "bsl_options": {
                "method": "sgd",
                "learning_rate": 0.005,
                "n_epochs": 20
            }
        }
    }
}

# Parallelism settings
N_JOBS = -1  # Use all CPU cores

# ============================================


def load_surprise_dataset(csv_path, min_interactions=20):
    df = pd.read_csv(csv_path)
    # ❌ Remove 0.0 ratings (they cause zero-norm vectors)
    df = df[df['rating'] > 0.0]
    # ✅ Filter users with too few remaining ratings
    df = df.groupby("user_id").filter(lambda x: len(x) >= min_interactions)

    reader = Reader(rating_scale=(0.0, 1.0))
    return Dataset.load_from_df(df[['user_id', 'mod_beatmap_id', 'rating']], reader)


def train_model_for_variant(user_type, rating_type, model_key, model_class, model_kwargs):
    prefix = f"{user_type}_{rating_type}"
    train_csv = os.path.join(SPLIT_DIR, f"{prefix}_train.csv")
    model_path = os.path.join(MODEL_DIR, f"{prefix}_{model_key}.pkl")


    print(f"[{prefix}/{model_key}] Loading training data...")
    df = pd.read_csv(train_csv)
    reader = Reader(rating_scale=(0.0, 1.0))
    data = Dataset.load_from_df(df[['user_id', 'mod_beatmap_id', 'rating']], reader)
    trainset = data.build_full_trainset()
    del df

    print(f"[{prefix}/{model_key}] Training model...")
    model = model_class(**model_kwargs)
    model.fit(trainset)

    joblib.dump(model, model_path)
    print(f"[{prefix}/{model_key}] ✔ Model saved to {model_path}")
    del model


# Prepare training jobs
jobs = []
for user_type, rating_type in VARIANTS:
    for model_key, model_info in MODEL_CONFIGS.items():
        model_class = model_info["class"]
        model_kwargs = model_info["kwargs"]
        jobs.append(delayed(train_model_for_variant)(
            user_type, rating_type, model_key, model_class, model_kwargs
        ))

# Run in parallel
print("\n=== Starting parallel training of all models ===")
Parallel(n_jobs=N_JOBS, verbose=10)(jobs)
print("\n✅ All models trained and stored in ./models/")

import os
import pandas as pd
import joblib
from surprise import Dataset, Reader, SVD, KNNWithMeans, BaselineOnly
from sklearn.model_selection import KFold
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
                "name": "pearson_baseline",
                "user_based": True
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
N_JOBS = 6 #-1 for all cores, but causes memory issues. with k fold 
N_FOLDS = 3

# ============================================

def prepare_folds(df, n_folds):
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    return [(df.iloc[train_idx], df.iloc[val_idx]) for train_idx, val_idx in kf.split(df)]

def train_fold_model(train_df, val_df, model_path, val_path, model_class, model_kwargs):
    reader = Reader(rating_scale=(0.0, 1.0))
    data = Dataset.load_from_df(train_df[['user_id', 'mod_beatmap_id', 'rating']], reader)
    trainset = data.build_full_trainset()

    model = model_class(**model_kwargs)
    model.fit(trainset)

    joblib.dump(model, model_path)
    val_df.to_csv(val_path, index=False)
    print(f"✔ Saved model: {model_path}\n✔ Saved val: {val_path}")

def train_all_models():
    jobs = []
    for user_type, rating_type in VARIANTS:
        prefix = f"{user_type}_{rating_type}"
        csv_path = os.path.join(SPLIT_DIR, f"{prefix}_train.csv")
        df = pd.read_csv(csv_path)
        df = df[df['rating'] > 0.0]
        df = df.groupby("user_id").filter(lambda x: len(x) >= 20)

        folds = prepare_folds(df, N_FOLDS)
        for fold_idx, (train_df, val_df) in enumerate(folds):
            for model_key, model_info in MODEL_CONFIGS.items():
                model_class = model_info["class"]
                model_kwargs = model_info["kwargs"]

                model_path = os.path.join(MODEL_DIR, f"{prefix}_{model_key}_fold{fold_idx}.pkl")
                val_path = os.path.join(MODEL_DIR, f"{prefix}_{model_key}_fold{fold_idx}_val.csv")

                jobs.append(delayed(train_fold_model)(
                    train_df.copy(), val_df.copy(), model_path, val_path, model_class, model_kwargs
                ))

    print("\n=== Starting cross-validated model training ===")
    Parallel(n_jobs=N_JOBS, verbose=10)(jobs)
    print("\n✅ All models and validation sets saved in ./models/")

if __name__ == '__main__':
    train_all_models()

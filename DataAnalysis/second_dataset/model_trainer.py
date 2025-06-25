import os
import pandas as pd
import joblib
from surprise import Dataset, Reader, SVD, KNNWithMeans, BaselineOnly
from joblib import Parallel, delayed

# ============================================
# CONFIGURATION SECTION
# ============================================

# Locate this script and set up paths to your splits & models
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_DIR  = os.path.join(SCRIPT_DIR, "generated_splits_instacart")
MODEL_DIR  = os.path.join(SCRIPT_DIR, "models_instacart")
os.makedirs(MODEL_DIR, exist_ok=True)

# We have just one dataset variant (no separate rating_type in filenames)
VARIANTS = [
    ("instacart",)
]

# Model configurations
MODEL_CONFIGS = {
    "svd": {
        "class": SVD,
        "kwargs": {
            "n_factors": 50,
            "n_epochs": 20,
            "lr_all": 0.005,
            "reg_all": 0.02,
            "random_state": 42
        }
    },
    "knn": {
        "class": KNNWithMeans,
        "kwargs": {
            "k": 40,
            "sim_options": {
                "name": "cosine",
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

# Use all cores
N_JOBS = -1

# ============================================

def train_model_for_variant(dataset_name, model_key, model_class, model_kwargs):
    """
    Load the train split for `dataset_name`, optionally subsample
    for KNN, then train and save the model.
    """
    prefix     = dataset_name
    train_path = os.path.join(SPLIT_DIR, f"{prefix}_train.csv")
    model_path = os.path.join(MODEL_DIR,  f"{prefix}_{model_key}.pkl")

    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Missing train split: {train_path}")

    print(f"[{prefix}/{model_key}] Loading {train_path}")
    df_raw = pd.read_csv(train_path)

    # Subsample to top 10k items for KNN to avoid huge similarity matrix
    if model_key == "knn":
        df = df_raw[df_raw['rating'] > 0.0]
        # Keep only users with ≥20 interactions
        df = df.groupby("user_id").filter(lambda x: len(x) >= 20)
        # Top-10k most frequent items
        top_items = df['product_id'].value_counts().nlargest(100000).index
        df = df[df['product_id'].isin(top_items)]
        print(f"[{prefix}/{model_key}] Filtered to {len(top_items)} items, {len(df)} rows")
    else:
        df = df_raw

    # Build Surprise dataset
    reader = Reader(rating_scale=(0.0, 1.0))
    data   = Dataset.load_from_df(df[['user_id','product_id','rating']], reader)
    trainset = data.build_full_trainset()
    del df, df_raw

    # Train
    print(f"[{prefix}/{model_key}] Training {model_key.upper()}...")
    model = model_class(**model_kwargs)
    model.fit(trainset)

    # Save
    joblib.dump(model, model_path)
    print(f"[{prefix}/{model_key}] Saved to {model_path}")
    del model

if __name__ == "__main__":
    # Sanity check: list your split files
    print("[INFO] Using splits from:", SPLIT_DIR)
    print(os.listdir(SPLIT_DIR))

    # Prepare parallel jobs
    jobs = []
    for (dataset_name,) in VARIANTS:
        for model_key, cfg in MODEL_CONFIGS.items():
            jobs.append(
                delayed(train_model_for_variant)(
                    dataset_name,
                    model_key,
                    cfg["class"],
                    cfg["kwargs"]
                )
            )

    # Launch training
    print("\n=== Starting parallel training ===")
    Parallel(n_jobs=N_JOBS, verbose=10)(jobs)
    print("\nAll models trained and saved in", MODEL_DIR)

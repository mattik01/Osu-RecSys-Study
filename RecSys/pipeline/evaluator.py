import os
import pandas as pd
import joblib
from surprise import Reader
from joblib import Parallel, delayed
from tqdm import tqdm
import numpy as np

# ========== CONFIG ==========

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
RESULT_CSV = os.path.join(os.path.dirname(__file__), "evaluation_results.csv")
BEATMAPS_PATH = r"C:\Users\glaes\Desktop\GitHub\Osu-RecSys-Study\data\processed\beatmaps.csv"
TOP_K = 100
N_JOBS = 10 
PERCENTILE = 99
MAX_FOLDS = 3  # ⬅️ Adjust this to use fewer folds (e.g., 1 for testing)

SENSITIVE_ATTRS = ["diff_approach", "diff_star_rating", "aim", "speed"]

VARIANTS = [
    ("top", "enjoyment"),
    ("top", "playcount"),
    ("random", "enjoyment"),
    ("random", "playcount")
]

MODEL_KEYS = ["svd", "knn", "baseline"]
FOLDS = list(range(MAX_FOLDS))


# ========== HELPERS ==========

def evaluate_single(user_df, model, beatmap_df, k=TOP_K):
    uid = user_df["user_id"].iloc[0]

    user_merged = user_df.merge(beatmap_df, left_on="mod_beatmap_id", right_on="mod_beatmap_id", how="left")
    ceilings = user_merged[SENSITIVE_ATTRS].quantile(PERCENTILE / 100.0)

    predictions = []
    for iid in user_df["mod_beatmap_id"].unique():
        try:
            est = model.predict(uid, iid).est
            bm_row = beatmap_df[beatmap_df["mod_beatmap_id"] == iid]
            if bm_row.empty:
                continue
            flags = any(bm_row[attr].values[0] > ceilings[attr] for attr in SENSITIVE_ATTRS)
            predictions.append((iid, est, flags))
        except Exception:
            continue

    if not predictions:
        return None

    predictions.sort(key=lambda x: x[1], reverse=True)
    top_unfiltered = predictions[:k]
    top_filtered = [p for p in predictions if not p[2]][:k]

    def get_true_rating(iid):
        match = user_df[user_df["mod_beatmap_id"] == iid]
        return match["rating"].values[0] if not match.empty else None

    def metric_stats(iid_preds):
        gt_ratings = [get_true_rating(iid) for iid, _, _ in iid_preds]
        pred_ratings = [est for _, est, _ in iid_preds]
        valid = [(gt, pr) for gt, pr in zip(gt_ratings, pred_ratings) if gt is not None]
        if not valid:
            return (0, 0, 0, 0)
        gt_only = [gt for gt, _ in valid]
        pred_only = [pr for _, pr in valid]
        avg_gt = np.mean(gt_only)
        min_gt = np.min(gt_only)
        top_gt = np.max(gt_only)
        mse = np.mean((np.array(gt_only) - np.array(pred_only)) ** 2)
        return avg_gt, top_gt, min_gt, mse

    avg_u, top_u, min_u, mse_u = metric_stats(top_unfiltered)
    avg_f, top_f, min_f, mse_f = metric_stats(top_filtered)

    return {
        "true_avg_unfiltered": avg_u,
        "true_top_unfiltered": top_u,
        "true_min_unfiltered": min_u,
        "mse_unfiltered": mse_u,
        "true_avg_filtered": avg_f,
        "true_top_filtered": top_f,
        "true_min_filtered": min_f,
        "mse_filtered": mse_f
    }


def evaluate_fold(user_type, rating_type, model_key, fold):
    prefix = f"{user_type}_{rating_type}_{model_key}_fold{fold}"
    model_path = os.path.join(MODELS_DIR, f"{prefix}.pkl")
    val_path = os.path.join(MODELS_DIR, f"{prefix}_val.csv")

    if not (os.path.exists(model_path) and os.path.exists(val_path)):
        print(f"[WARN] Missing files for {prefix}. Skipping.")
        return None

    print(f"▶️  Evaluating: {prefix}")
    try:
        model = joblib.load(model_path)
        val_df = pd.read_csv(val_path)
        beatmap_df = pd.read_csv(BEATMAPS_PATH)

        user_results = []
        for _, user_df in tqdm(val_df.groupby("user_id"), desc=f"Users in {prefix}", leave=False):
            res = evaluate_single(user_df, model, beatmap_df)
            if res:
                user_results.append(res)

        if not user_results:
            print(f"[INFO] No valid users in {prefix}")
            return None

        df = pd.DataFrame(user_results)
        return {
            "user_type": user_type,
            "rating_type": rating_type,
            "model": model_key,
            "fold": fold,
            "n_users": len(user_results),
            **df.mean(numeric_only=True).to_dict()
        }

    except Exception as e:
        print(f"[ERROR] Failed on {prefix}: {e}")
        return None


# ========== MAIN ==========

if __name__ == "__main__":
    print("=== 🚀 Starting parallel evaluation ===")

    all_jobs = [
        (user_type, rating_type, model_key, fold)
        for user_type, rating_type in VARIANTS
        for model_key in MODEL_KEYS
        for fold in FOLDS
    ]

    print(f"📊 Total tasks: {len(all_jobs)} (models x folds)")
    results = Parallel(n_jobs=N_JOBS, verbose=10)(
        delayed(evaluate_fold)(user_type, rating_type, model_key, fold)
        for user_type, rating_type, model_key, fold in tqdm(all_jobs, desc="All folds", leave=True)
    )

    results = [r for r in results if r is not None]

    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(RESULT_CSV, index=False)
        print(f"\n✅ Evaluation complete. Results saved to {RESULT_CSV}")
    else:
        print("\n⚠️ No results to save — all folds skipped or failed.")

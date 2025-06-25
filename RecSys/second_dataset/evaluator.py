import os
import pandas as pd
import joblib
from surprise import Reader, Dataset
from joblib import Parallel, delayed
from tqdm import tqdm
import numpy as np
import warnings
warnings.filterwarnings("error", category=RuntimeWarning)

# ========== CONFIG ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = SCRIPT_DIR

MODELS_DIR = os.path.join(SCRIPT_DIR, "models_instacart")
SPLIT_DIR  = os.path.join(SCRIPT_DIR, "generated_splits_instacart")
RESULT_CSV = os.path.join(SCRIPT_DIR, "evaluation_results_instacart.csv")

TOP_K = 10
N_JOBS = -1
LAST_N_ORDERS = 5
MAX_DEPT = 2
MAX_AISLE = 2

# === Constraint Toggles ===
USE_CONSTRAINT_RECENT = True
USE_CONSTRAINT_DEPT   = True
USE_CONSTRAINT_AISLE  = True

# === Model Selection ===
ENABLED_MODELS = ["svd", "knn", "baseline"]

PRODUCT_META_PATH = os.path.join(SCRIPT_DIR, "products_enriched.csv")

VARIANTS = [("instacart",)]
MODEL_KEYS = ENABLED_MODELS

# ========== DATA PREP ==========
def sanity_check_df(name, df):
    print(f"\n[🔍 Sanity check for {name}]")
    print(f"Rows: {len(df)} | Columns: {list(df.columns)}")
    if df.select_dtypes(include=[np.number]).shape[1] > 0:
        print(df.describe(include=[np.number]))
    else:
        print(df.head())

def load_product_metadata():
    if os.path.exists(PRODUCT_META_PATH):
        df = pd.read_csv(PRODUCT_META_PATH)
        sanity_check_df("products_enriched.csv", df)
        return df
    print("[INFO] Merging product metadata...")
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    aisles   = pd.read_csv(os.path.join(DATA_DIR, "aisles.csv"))
    depts    = pd.read_csv(os.path.join(DATA_DIR, "departments.csv"))
    merged = (
        products
        .merge(aisles, on="aisle_id", how="left")
        .merge(depts, on="department_id", how="left")
    )
    merged.to_csv(PRODUCT_META_PATH, index=False)
    sanity_check_df("merged metadata", merged)
    return merged

def build_recent_product_dict():
    print("[INFO] Building recent-product dict...")
    orders = pd.read_csv(os.path.join(DATA_DIR, "orders.csv"))
    prior  = pd.read_csv(os.path.join(DATA_DIR, "order_products__prior.csv"))
    sanity_check_df("orders", orders)
    sanity_check_df("order_products__prior", prior)

    reordered = prior[prior["reordered"] == 1]
    reordered = reordered.merge(
        orders[["order_id", "user_id", "order_number"]],
        on="order_id", how="left"
    )
    reordered["rank"] = reordered.groupby("user_id")["order_number"].rank(method="dense", ascending=False)
    recent = reordered[reordered["rank"] <= LAST_N_ORDERS]
    print(f"[INFO] Number of recent interactions: {len(recent)}")
    return recent.groupby("user_id")["product_id"].apply(set).to_dict()

# ========== EVALUATION ==========
def evaluate_single(user_df, model, product_df, recent_dict, k=TOP_K):
    uid = user_df["user_id"].iloc[0]
    candidate_pids = user_df["product_id"].unique()

    predictions = []
    for pid in candidate_pids:
        try:
            est = model.predict(uid, pid).est
            p_row = product_df[product_df["product_id"] == int(pid)]
            if p_row.empty:
                continue
            is_recent = int(pid) in recent_dict.get(uid, set()) if USE_CONSTRAINT_RECENT else False
            dept_id = p_row["department_id"].values[0]
            aisle_id = p_row["aisle_id"].values[0]
            predictions.append({
                "pid": pid,
                "est": est,
                "dept": dept_id,
                "aisle": aisle_id,
                "is_recent": is_recent
            })
        except Exception:
            continue

    if not predictions:
        return None

    predictions.sort(key=lambda x: x["est"], reverse=True)
    top_unfiltered = predictions[:k]

    filtered = []
    seen_depts = {}
    seen_aisles = {}
    for p in predictions:
        if USE_CONSTRAINT_RECENT and p["is_recent"]:
            continue
        if USE_CONSTRAINT_DEPT and seen_depts.get(p["dept"], 0) >= MAX_DEPT:
            continue
        if USE_CONSTRAINT_AISLE and seen_aisles.get(p["aisle"], 0) >= MAX_AISLE:
            continue

        filtered.append(p)
        if USE_CONSTRAINT_DEPT:
            seen_depts[p["dept"]] = seen_depts.get(p["dept"], 0) + 1
        if USE_CONSTRAINT_AISLE:
            seen_aisles[p["aisle"]] = seen_aisles.get(p["aisle"], 0) + 1
        if len(filtered) >= k:
            break

    def get_true_rating(iid):
        match = user_df[user_df["product_id"] == iid]
        return match["rating"].values[0] if not match.empty else None

    def metric_stats(preds):
        if not preds:
            return (np.nan, np.nan, np.nan, np.nan)
        gt = [get_true_rating(p["pid"]) for p in preds]
        est = [p["est"] for p in preds]
        valid = [(g, e) for g, e in zip(gt, est) if g is not None]
        if not valid:
            return (np.nan, np.nan, np.nan, np.nan)
        gt_vals = [g for g, _ in valid]
        est_vals = [e for _, e in valid]
        return (
            np.mean(gt_vals),
            np.max(gt_vals),
            np.min(gt_vals),
            np.mean((np.array(gt_vals) - np.array(est_vals))**2)
        )

    avg_u, top_u, min_u, mse_u = metric_stats(top_unfiltered)
    avg_f, top_f, min_f, mse_f = metric_stats(filtered)

    return {
        "user_id": uid,
        "true_avg_unfiltered": avg_u,
        "true_top_unfiltered": top_u,
        "true_min_unfiltered": min_u,
        "mse_unfiltered": mse_u,
        "true_avg_filtered": avg_f,
        "true_top_filtered": top_f,
        "true_min_filtered": min_f,
        "mse_filtered": mse_f,
        "top_k_total": len(top_unfiltered),
        "top_k_filtered": len(filtered),
        "filtered_out": len(top_unfiltered) - len(filtered)
    }

def evaluate_variant(dataset_name, model_key):
    prefix = f"{dataset_name}_{model_key}"
    model_path = os.path.join(MODELS_DIR, f"{prefix}.pkl")
    val_path = os.path.join(SPLIT_DIR, f"{dataset_name}_val.csv")

    if not (os.path.exists(model_path) and os.path.exists(val_path)):
        print(f"[WARN] Missing files for {prefix}. Skipping.")
        return None

    print(f"\n▶️  Evaluating: {prefix}")
    try:
        model = joblib.load(model_path)
        val_df = pd.read_csv(val_path)
        val_df["user_id"] = val_df["user_id"].astype(str)
        val_df["product_id"] = val_df["product_id"].astype(str)
        sanity_check_df("val split", val_df)

        product_df = load_product_metadata()
        product_df["product_id"] = product_df["product_id"].astype(str)
        recent_dict = build_recent_product_dict() if USE_CONSTRAINT_RECENT else {}

        user_results = []
        for _, user_df in tqdm(val_df.groupby("user_id"), desc=f"Users in {prefix}", leave=False):
            res = evaluate_single(user_df, model, product_df, recent_dict)
            if res is None or (res["top_k_filtered"] == 0 and res["top_k_total"] == 0):
                continue
            user_results.append(res)

        if not user_results:
            print(f"[INFO] No valid users in {prefix}")
            return None

        df = pd.DataFrame(user_results)
        summary = df.drop(columns="user_id").mean(numeric_only=True, skipna=True).to_dict()
        summary["total_filtered_out"] = df["filtered_out"].sum()
        return {
            "dataset": dataset_name,
            "model": model_key,
            "n_users": len(user_results),
            **summary
        }

    except Exception as e:
        print(f"[ERROR] Failed on {prefix}: {e}")
        return None

# ========== MAIN ==========
if __name__ == "__main__":
    print("=== \U0001F680 Starting Instacart Constraint Evaluation ===")
    jobs = [
        (variant[0], model_key)
        for variant in VARIANTS
        for model_key in MODEL_KEYS
    ]

    results = Parallel(n_jobs=N_JOBS, verbose=10)(
        delayed(evaluate_variant)(dataset_name, model_key)
        for dataset_name, model_key in jobs
    )

    results = [r for r in results if r is not None]
    if results:
        df = pd.DataFrame(results)
        df.to_csv(RESULT_CSV, index=False)
        print(f"\n✅ Evaluation complete. Results saved to {RESULT_CSV}")
    else:
        print("\n⚠️ No results to save.")

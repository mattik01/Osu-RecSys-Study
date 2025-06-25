import pandas as pd
import numpy as np

# === CONFIG ===
RESULT_PATH = r"C:\Users\glaes\Desktop\GitHub\Osu-RecSys-Study\DataAnalysis\matteo_recommender_folder\evaluation_results.csv"
OUTPUT_CSV_PREFIX = r"C:\Users\glaes\Desktop\GitHub\Osu-RecSys-Study\DataAnalysis\matteo_recommender_folder\summary_table"
OUTPUT_TXT = r"C:\Users\glaes\Desktop\GitHub\Osu-RecSys-Study\DataAnalysis\matteo_recommender_folder\summary_pretty_table.txt"

# === LOAD AND PROCESS ===
df = pd.read_csv(RESULT_PATH)

# Average over folds
grouped = df.groupby(["user_type", "rating_type", "model"]).mean(numeric_only=True).reset_index()

# Metrics to include
base_metrics = ["true_avg", "true_top", "true_min", "mse"]

# Reorganize columns
rows = []
for (user_type, rating_type), subdf in grouped.groupby(["user_type", "rating_type"]):
    for model in ["svd", "knn", "baseline"]:
        row = {"user_type": user_type, "rating_type": rating_type, "model": model}
        model_df = subdf[subdf["model"] == model]
        if not model_df.empty:
            for metric in base_metrics:
                unf = model_df[f"{metric}_unfiltered"].values[0]
                fil = model_df[f"{metric}_filtered"].values[0]
                row[f"{metric}_unfiltered"] = unf
                row[f"{metric}_filtered"] = fil
                row[f"{metric}_delta"] = fil - unf
        rows.append(row)
    # Add average row
    avg_row = {"user_type": user_type, "rating_type": rating_type, "model": "avg"}
    for metric in base_metrics:
        unf_mean = subdf[f"{metric}_unfiltered"].mean()
        fil_mean = subdf[f"{metric}_filtered"].mean()
        avg_row[f"{metric}_unfiltered"] = unf_mean
        avg_row[f"{metric}_filtered"] = fil_mean
        avg_row[f"{metric}_delta"] = fil_mean - unf_mean
    rows.append(avg_row)

final_df = pd.DataFrame(rows)

# === SPLIT TABLES AND SAVE ===
for rating_type in ["enjoyment", "playcount"]:
    part = final_df[final_df["rating_type"] == rating_type]
    part = part.drop(columns=["rating_type"])
    out_csv = f"{OUTPUT_CSV_PREFIX}_{rating_type}.csv"
    part.to_csv(out_csv, index=False)

# === TXT PRETTY PRINT ===
with open(OUTPUT_TXT, "w") as f:
    for rating_type in ["enjoyment", "playcount"]:
        f.write(f"\n=== Rating Type: {rating_type.upper()} ===\n")
        f.write(final_df[final_df["rating_type"] == rating_type]
                .drop(columns=["rating_type"])
                .to_string(index=False, float_format="%.4f"))
        f.write("\n\n")

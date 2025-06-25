import pandas as pd

# === CONFIG ===
CSV_PATH = r"C:\Users\glaes\Desktop\GitHub\Osu-RecSys-Study\data\processed\beatmaps.csv"
TITLE_QUERIES = ["Blue Zenith","(can you) understand me?","KARMANATIONS","AaAaAaAAaAaAAa", "Freedom Dive", "Bass Slut (Original Mix)","The Big Black", "No Title", "Santa-san","PADORU / PADORU", "Renai Circulation", "Epitaph", "Overkill", "Crab Rave"]

# === LOAD DATA ===
df = pd.read_csv(CSV_PATH)

# Check required columns
required_cols = {"title", "mods_string", "random_farm_factor", "top_farm_factor", "diff_star_rating"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing columns in CSV: {missing}")

# === PROCESS ===
for query in TITLE_QUERIES:
    matches = df[df["title"].str.contains(query, case=False, na=False)].copy()

    print(f"\n🔍 Title match: '{query}'")

    if matches.empty:
        print("  No matches found.")
        continue

    print("\n  🔹 Top 5 by random_farm_factor:")
    top_random = matches.sort_values(by="random_farm_factor", ascending=False).head(5)
    print(top_random[["title", "mods_string", "random_farm_factor", "diff_star_rating"]].to_string(index=False))

    print("\n  🔹 Top 5 by top_farm_factor:")
    top_top = matches.sort_values(by="top_farm_factor", ascending=False).head(5)
    print(top_top[["title", "mods_string", "top_farm_factor", "diff_star_rating"]].to_string(index=False))

import pandas as pd
import os
import hashlib
from tqdm import tqdm


################ HELPERS:
# Define mod constants and conversion function
MODS = {
    1: "NF", 2: "EZ", 4: "TD", 8: "HD", 16: "HR", 32: "SD", 64: "DT",
    128: "RX", 256: "HT", 512: "NC", 1024: "FL", 2048: "AU", 4096: "SO",
    8192: "AP", 16384: "PF", 32768: "K4", 65536: "K5", 131072: "K6",
    262144: "K7", 524288: "K8", 1048576: "FI", 2097152: "RN"
}

def decode_mods(mods_int: int):
    """Convert mod bitmask to list of mod acronyms"""
    return [acronym for bit, acronym in MODS.items() if mods_int & bit]

genre_map = {
    0: "Any", 1: "Unspecified", 2: "Video Game", 3: "Anime", 4: "Rock",
    5: "Pop", 6: "Other", 7: "Novelty", 9: "Hip Hop", 10: "Electronic",
    11: "Metal", 12: "Classical", 13: "Folk", 14: "Jazz"
}
def resolve_genre(genre_id):
    return genre_map.get(genre_id, "Unknown")

language_map = {
    0: "Any", 1: "Other", 2: "English", 3: "Japanese", 4: "Chinese",
    5: "Instrumental", 6: "Korean", 7: "French", 8: "German", 9: "Swedish",
    10: "Spanish", 11: "Italian", 12: "Russian", 13: "Polish", 14: "Other"
}
def resolve_language(language_id):
    return language_map.get(language_id, "Unknown")

preference_mods = ["PF", "SD", "HD", "NC"]

def generate_mod_beatmap_id(beatmap_id, mods_string):
    combined = f"{mods_string}_{beatmap_id}"
    return int(hashlib.sha256(combined.encode()).hexdigest(), 16) % (10 ** 12)


######### PREPROCESS BEATMAPS ONLY ONE set 
input_file = os.path.join("data", "export", "2025_05_01_performance_osu_random_10000__beatmaps.csv")
output_file = os.path.join("data", "processed", "beatmaps.csv")

print(f"Processing beatmaps: {input_file}...")
beatmaps_df = pd.read_csv(input_file, delimiter=',')

# BEATMAP-SPECIFIC PREPROCESSING
beatmaps_df["genre"] = beatmaps_df["genre_id"].map(genre_map).fillna("Unknown")
beatmaps_df["language"] = beatmaps_df["language_id"].map(language_map).fillna("Unknown")
beatmaps_df.drop(columns=["genre_id", "language_id"], inplace=True)

beatmaps_df['mods_list'] = beatmaps_df['mods'].apply(decode_mods)
beatmaps_df['mods_string'] = beatmaps_df['mods_list'].apply(
    lambda x: ''.join(sorted(mod for mod in x if mod not in preference_mods)) or 'NM'
)
beatmaps_df.drop(columns=["mods", "mods_list"], inplace=True)

# CREATE A HASH-BASED UNIQUE ID FOR BEATMAP+MODS COMBINATION
tqdm.pandas(desc="Hashing beatmap+mods")
beatmaps_df['mod_beatmap_id'] = beatmaps_df.progress_apply(
    lambda row: generate_mod_beatmap_id(row['beatmap_id'], row['mods_string']),
    axis=1
)

# Reorder columns to have mod_beatmap_id first
cols = ['mod_beatmap_id', 'beatmap_id', 'mods_string'] + [
    col for col in beatmaps_df.columns if col not in {'mod_beatmap_id', 'beatmap_id', 'mods_string'}
]
beatmaps_df = beatmaps_df[cols]

os.makedirs(os.path.dirname(output_file), exist_ok=True)
beatmaps_df.to_csv(output_file, index=False)
print(f"Saved beatmaps to {output_file}")


# Define the schemas to process
schemas = ["2025_05_01_performance_osu_random_", "2025_05_01_performance_osu_top_"]

for schema in schemas:
    ######### PREPROCESS USERS
    input_file = os.path.join("data", "export", f"{schema}10000__users.csv")
    processed_schema = '_'.join(schema.split('_')[5:])
    output_file = os.path.join("data", "processed", f"{processed_schema}10000__users.csv")

    print(f"Processing users: {input_file}...")
    users_df = pd.read_csv(input_file, delimiter=',')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    users_df.to_csv(output_file, index=False)
    del users_df
    print(f"Saved users to {output_file}")


    ######### PREPROCESS SCORES
    input_file = os.path.join("data", "export", f"{schema}10000__scores_high.csv")
    output_file = os.path.join("data", "processed", f"{processed_schema}10000__scores.csv")

    print(f"Processing scores: {input_file}...")
    scores_df = pd.read_csv(input_file, delimiter=',')

    # 1. Decode mod list
    tqdm.pandas(desc="Decoding mod bitmasks")
    scores_df['mods_list'] = scores_df['enabled_mods'].progress_apply(decode_mods)

    # 2. Filter out banned mods
    banned_mods = ["NF", "EZ", "TD", "RX", "HT", "FL", "AU", "SO", "AP", "FI", "RN", 
                   "K4", "K5", "K6", "K7", "K8"]
    scores_df = scores_df[~scores_df['mods_list'].apply(
        lambda x: any(mod in x for mod in banned_mods)
    )]

    # 3. Remove preference mods
    scores_df['mods_string'] = scores_df['mods_list'].apply(
        lambda x: ''.join(sorted(mod for mod in x if mod not in preference_mods)) or 'NM'
    )

    # 4. Keep highest-pp entry per user-beatmap-mod combo
    scores_df = scores_df.sort_values('pp', ascending=False)
    group_cols = ['beatmap_id', 'user_id', 'mods_string']
    keep_cols = ['score', 'pp','accuracy', 'maxcombo', 'rank', 'date', 'playcount']
    scores_df = scores_df.drop_duplicates(group_cols, keep='first')[group_cols + keep_cols]

    print("Merging with beatmap metadata...")
    scores_df = scores_df.merge(
        beatmaps_df[['beatmap_id', 'mods_string', 'mod_beatmap_id']],
        on=['beatmap_id', 'mods_string'],
        how='left'
    ).dropna(subset=['mod_beatmap_id'])

    # 5. Assign final score ID
    scores_df = scores_df.reset_index(drop=True)
    scores_df['score_id'] = scores_df.index + 1

    # Reorder columns to have score_id, mod_beatmap_id first
    col_order = ['score_id', 'mod_beatmap_id', 'beatmap_id', 'mods_string'] + [col for col in scores_df.columns if col not in ['score_id', 'mod_beatmap_id','beatmap_id', 'mods_string']]
    scores_df = scores_df[col_order]

    scores_df.to_csv(output_file, index=False)
    print(f"Saved scores to {output_file}")

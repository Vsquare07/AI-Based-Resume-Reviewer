import pandas as pd

INPUT_FILE = "raw_rag_dataset.csv"
OUTPUT_FILE = "cleaned_dataset.csv"
MAX_ROWS = 30

roles_to_keep = {
    "AI Engineer",
    "Cloud Engineer",
    "Cybersecurity Analyst",
    "Data Analyst",
    "Game Developer",
    "Mobile App Developer",
    "Robotics Engineer",
    "Software Engineer",
    "Blockchain Developer",
    "Software Developer",
}

df = pd.read_csv(INPUT_FILE)

# Keep only the first two columns
df = df.iloc[:, :2].copy()

# Normalize role names for case-insensitive matching
df["_role"] = (
    df["Role"]
    .astype("string")
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
    .str.casefold()
)

target_roles = {r.casefold() for r in roles_to_keep}

# Remove every role not in the specified list
df = df[df["_role"].isin(target_roles)].copy()

# Keep at most 30 entries per role
df["_count"] = df.groupby("_role", sort=False).cumcount()
df = df[df["_count"] < MAX_ROWS]

# Remove helper columns and save
df = df.drop(columns=["_role", "_count"])
df.to_csv(OUTPUT_FILE, index=False)

print("Final role counts:")
print(
    df["Role"].str.strip().str.casefold().value_counts()
)
print(f"\nTotal rows: {len(df)}")
print(f"Saved to: {OUTPUT_FILE}")

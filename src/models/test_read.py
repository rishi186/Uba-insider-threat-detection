import pandas as pd
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))
DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/daily_features.parquet")

print(f"Reading {DATA_PATH}...")
try:
    df = pd.read_parquet(DATA_PATH)
    print("Success!")
    print(df.head())
    print(df.info())
except Exception as e:
    print(f"Failed to read parquet: {e}")
    import traceback
    traceback.print_exc()

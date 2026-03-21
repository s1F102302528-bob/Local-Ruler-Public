import os
import sys
import django
from pathlib import Path
import pandas as pd

# Django環境のセットアップ
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from navi import utils

def test_load_all_files():
    print("=== Testing Loading All Files (a-j) ===")
    
    suffixes = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    results = {}

    for suffix in suffixes:
        print(f"\n--- Loading file '{suffix}' ---")
        try:
            df = utils._load_dataset(suffix)
            if df is not None:
                print(f"Success. Shape: {df.shape}")
                print(f"Columns (first 5): {df.columns.tolist()[:5]}")
                results[suffix] = True
            else:
                print(f"Failed to load file '{suffix}'.")
                results[suffix] = False
        except Exception as e:
            print(f"Exception loading file '{suffix}': {e}")
            results[suffix] = False

    print("\n=== Testing Merge (get_combined_data) ===")
    try:
        merged_df = utils.get_combined_data()
        if merged_df is not None:
            print(f"Merge Success. Final Shape: {merged_df.shape}")
            print(f"Total Columns: {len(merged_df.columns)}")
            # Show some columns to verify merge
            print(f"Sample Columns: {merged_df.columns.tolist()[:10]} ...")
        else:
            print("Merge returned None.")
    except Exception as e:
        print(f"Exception during merge: {e}")

if __name__ == "__main__":
    test_load_all_files()

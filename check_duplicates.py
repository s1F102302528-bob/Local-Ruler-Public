import pandas as pd
import os
from pathlib import Path
import sys

# Setup paths
BASE_DIR = Path("c:/Users/INIAD/Documents/チーム実習/repo/INIAD-team2025-G1T4")
DATA_DIR = BASE_DIR / "navi" / "data"

suffixes = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

def check_file(suffix):
    file_name = f"2025-{suffix}.xls"
    file_path = DATA_DIR / file_name
    
    print(f"--- Checking {file_name} ---")
    if not file_path.exists():
        print("File not found.")
        return

    try:
        # Mimic logic from navi/utils.py
        df = pd.read_excel(file_path, engine="xlrd", skiprows=5)
        
        # Cleaning
        df = df.replace(r"\n", "", regex=True)
        df.columns = df.columns.str.replace(r"\n", "", regex=True)
        df = df.replace(r"\u3000", "", regex=True)
        df = df.dropna(axis=1, how="all")
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        target_col_code = "市区町村ｺｰﾄﾞ"
        
        if target_col_code in df.columns:
            # Convert to string
            df[target_col_code] = df[target_col_code].astype(str).str.replace(r"\.0$", "", regex=True)
            
            # Check duplicates
            duplicates = df[df.duplicated(subset=[target_col_code], keep=False)]
            n_duplicates = len(duplicates)
            n_rows = len(df)
            
            print(f"Rows: {n_rows}")
            print(f"Unique Codes: {df[target_col_code].nunique()}")
            
            if n_duplicates > 0:
                print(f"WARNING: Found {n_duplicates} duplicate rows for '{target_col_code}'.")
                print("Sample duplicates:")
                print(duplicates[target_col_code].value_counts().head())
            else:
                print("No duplicates found for key.")
        else:
            print(f"Column '{target_col_code}' not found. Columns: {df.columns.tolist()[:5]}...")

    except Exception as e:
        print(f"Error: {e}")

for suffix in suffixes:
    check_file(suffix)

import os
import sys
import django
import pandas as pd
from pathlib import Path

# Django設定の読み込み
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from navi import utils


def inspect_data():
    print("=== Combined Data Inspection ===")

    # データ取得
    try:
        df = utils.get_combined_data()
    except Exception as e:
        print(f"Error calling get_combined_data: {e}")
        return

    if df is None:
        print("Error: get_combined_data returned None.")
        return

    # 1. 基本形状
    rows, cols = df.shape
    print(f"\n[Shape]")
    print(f"Rows (Municipalities): {rows}")
    print(f"Columns: {cols}")

    # 2. キーの一意性チェック
    key_col = "市区町村ｺｰﾄﾞ"
    if key_col in df.columns:
        unique_keys = df[key_col].nunique()
        print(f"\n[Key Integrity]")
        print(f"Unique '{key_col}': {unique_keys}")
        if rows == unique_keys:
            print("OK: '市区町村ｺｰﾄﾞ' is unique.")
        else:
            print(
                f"WARNING: Row count ({rows}) does not match unique keys ({unique_keys}). Duplicates exist!"
            )
            # 重複しているコードを表示
            print(
                "Duplicate codes sample:",
                df[df.duplicated(subset=[key_col])][key_col].unique()[:5],
            )
    else:
        print(f"WARNING: Key column '{key_col}' not found!")

    # 3. 自治体数の妥当性（概算）
    # 日本の基礎自治体は約1700程度。政令指定都市の区を含めるともう少し増える。
    if 1700 <= rows <= 2000:
        print(
            "OK: Row count seems reasonable for Japan municipalities (approx 1741 + wards)."
        )
    else:
        print(
            f"INFO: Row count {rows} is outside the typical range (approx 1741). Check if this is expected."
        )

    # 4. 結合状況のチェック
    print(f"\n[Column Check]")
    print(f"Total Columns: {len(df.columns)}")

    # 5. 欠損値チェック
    print(f"\n[Missing Values Check]")
    # 完全に空のカラムがあるか（結合ミスでカラムだけ作られてデータが入っていない場合など）
    all_null_cols = df.columns[df.isnull().all()].tolist()
    if all_null_cols:
        print(f"WARNING: The following columns are completely empty (all NaN):")
        print(all_null_cols)
    else:
        print("OK: No completely empty columns found.")

    # 6. サンプル表示
    print(f"\n[Sample Data (Head 3)]")
    # 表示が見やすいように調整
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.max_rows", 5)
    pd.set_option("display.width", 1000)
    print(df.head(3))


if __name__ == "__main__":
    inspect_data()

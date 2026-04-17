import pandas as pd
import numpy as np
from django.conf import settings

# --- 定数・設定 ---
DATA_DIR = settings.BASE_DIR / "navi" / "data"

# 類似度計算に使用する指標設定
SIMILARITY_FEATURES = {
    # ターゲット傾向: 課題が表面的に現れる指標（人口動態など）
    # コサイン類似度を使用（絶対値より「変化の傾向」や「バランス」を重視）
    "target": ["総人口", "出生数", "死亡数", "転入者数", "転出者数"],
    # 関連特性: ターゲット傾向に影響を与える指標（社会・経済要因）
    # コサイン類似度を使用
    "related": [
        "婚姻件数",
    ],
    # 地域特性: その地域の基本的な環境・土台（規模・財政など）
    # ユークリッド距離を使用（「規模感」そのものの近さを重視）
    "regional": [
        "可住地面積",
        "事業所数（民営）",
        "財政力指数(市町村財政)",
    ],
}

PREF_MAP = {
    "01": "北海道",
    "02": "青森県",
    "03": "岩手県",
    "04": "宮城県",
    "05": "秋田県",
    "06": "山形県",
    "07": "福島県",
    "08": "茨城県",
    "09": "栃木県",
    "10": "群馬県",
    "11": "埼玉県",
    "12": "千葉県",
    "13": "東京都",
    "14": "神奈川県",
    "15": "新潟県",
    "16": "富山県",
    "17": "石川県",
    "18": "福井県",
    "19": "山梨県",
    "20": "長野県",
    "21": "岐阜県",
    "22": "静岡県",
    "23": "愛知県",
    "24": "三重県",
    "25": "滋賀県",
    "26": "京都府",
    "27": "大阪府",
    "28": "兵庫県",
    "29": "奈良県",
    "30": "和歌山県",
    "31": "鳥取県",
    "32": "島根県",
    "33": "岡山県",
    "34": "広島県",
    "35": "山口県",
    "36": "徳島県",
    "37": "香川県",
    "38": "愛媛県",
    "39": "高知県",
    "40": "福岡県",
    "41": "佐賀県",
    "42": "長崎県",
    "43": "熊本県",
    "44": "大分県",
    "45": "宮崎県",
    "46": "鹿児島県",
    "47": "沖縄県",
}

# --- グローバルキャッシュ ---
_DF_CACHE = {}
_MERGED_DF_CACHE = None
_NORMALIZED_DF_CACHE = None  # 類似度計算用の正規化済みデータキャッシュ


# --- 内部ヘルパー ---


def _load_dataset(suffix: str = "a") -> pd.DataFrame | None:
    """
    指定されたサフィックスのExcelファイルを読み込み、クリーニングして返します。
    結果はキャッシュされます。
    """
    global _DF_CACHE

    if suffix in _DF_CACHE:
        return _DF_CACHE[suffix]

    file_name = f"2025-{suffix}.xls"
    file_path = DATA_DIR / file_name

    if not file_path.exists():
        # print(f"File not found: {file_path}")
        return None

    try:
        # ヘッダー行を動的に探索
        # 先頭20行を読み込み、"市区町村"が含まれる行を探す
        header_row = 5  # デフォルト
        temp_df = pd.read_excel(file_path, engine="xlrd", header=None, nrows=20)

        found = False
        for idx, row in temp_df.iterrows():
            # 行内の全セルを文字列化して確認
            row_str = row.astype(str).str.cat()
            if "市区町村" in row_str:
                header_row = idx
                found = True
                break

        # 本番読み込み
        df = pd.read_excel(file_path, engine="xlrd", header=header_row)

    except Exception as e:
        print(f"Error reading {file_name}: {e}")
        return None

    # 1. カラム名のクリーニング（改行、全角スペース、半角スペースの削除）
    # Column名が object 型でない場合もあるため str アクセサ使用前に変換
    df.columns = df.columns.astype(str).str.replace(r"[\n\u3000 ]", "", regex=True)

    # "市区町村コード" (全角) などを "市区町村ｺｰﾄﾞ" (半角) に統一
    # ※ファイルによって表記が揺れている場合に対応
    df.columns = df.columns.str.replace("コード", "ｺｰﾄﾞ")
    df.columns = df.columns.str.replace("市区町村名", "市区町村")

    # 2. 空の列と行を削除
    df = df.dropna(axis=1, how="all")
    # "Unnamed" カラムで、かつデータも入っていないようなものを削除したいが、
    # 重要なデータ列が Unnamed になっている可能性（ヘッダー結合セル）もあるため
    # ここでは "市区町村" や "ｺｰﾄﾞ" があるかを確認する

    target_col_code = "市区町村ｺｰﾄﾞ"
    target_col_name = "市区町村"

    # もし target_col_code が見つからない場合、1列目(index 0)か2列目を疑う
    if target_col_code not in df.columns:
        # データの中身で判断（5桁の数字っぽい列を探す）
        for col in df.columns:
            # 最初の数行をチェック
            sample = df[col].dropna().head(5).astype(str)
            # 全て数字かつ5桁以上ならコード列とみなす (北海道=01000など)
            if sample.str.match(r"^\d{5,}$").all():
                df.rename(columns={col: target_col_code}, inplace=True)
                break

    # 3. 市区町村コードに基づく行のフィルタリング
    if target_col_code in df.columns and target_col_name in df.columns:
        # テキストデータのクリーニング (セル内の改行、全角・半角スペースを削除)
        # オブジェクト型の列に対して適用
        obj_cols = df.select_dtypes(include=["object"]).columns
        df[obj_cols] = df[obj_cols].apply(
            lambda x: x.astype(str).str.replace(r"[\n\u3000 ]", "", regex=True)
        )

        # コードフォーマットの統一（末尾の.0削除など）
        df[target_col_code] = (
            df[target_col_code].astype(str).str.replace(r"\.0$", "", regex=True)
        )
        # コードを5桁にゼロ埋め (先に行うことでフィルタリングを正確に)
        df[target_col_code] = df[target_col_code].str.zfill(5)

        df[target_col_name] = df[target_col_name].astype(str)

        # 数値以外のコードを除外 (ヘッダーの残りや注釈行など)
        df = df[df[target_col_code].str.isnumeric()]

        # 重複削除
        df = df.drop_duplicates(subset=[target_col_code])

        # フィルタロジック:
        # - 東京都（13で始まる）以外の「区」を削除（政令指定都市の区など）
        is_ku = df[target_col_name].str.endswith("区", na=False)

        # is_ku だが 東京でない
        is_seirei_ku = is_ku & ~df[target_col_code].str.startswith("13")

        # 都道府県行（末尾が都/道/府/県）を削除 (コード末尾が000のものなど)
        # e-Statコードで末尾000は都道府県計
        is_pref_row = df[target_col_code].str.endswith("000")

        # さらに、コードが 00001〜00047 の場合も都道府県データとみなして削除
        # (XLSで 1〜47 の数値として入っている場合への対応)
        is_pref_code = df[target_col_code].between("00001", "00047")

        # フィルタ適用 (OR条件でまとめて除外)
        df = df[~(is_seirei_ku | is_pref_row | is_pref_code)]

        # コードを5桁にゼロ埋め (1000 -> 01000)
        df[target_col_code] = df[target_col_code].str.zfill(5)

        # 数値変換 (カンマ削除 -> 数値化)
        # 市区町村コードと市区町村名以外の全ての列を対象
        for col in df.columns:
            if col not in [target_col_code, target_col_name]:
                # 文字列にしてカンマを削除
                df[col] = df[col].astype(str).str.replace(",", "")
                # 数値変換 (エラーはNaN)
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 都道府県カラムを追加 (コードの先頭2桁から判定)
        df["都道府県"] = df[target_col_code].str[:2].map(PREF_MAP)

    # 最終的なクリーニング: Unnamed カラムを削除
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    df = df.reset_index(drop=True)
    _DF_CACHE[suffix] = df
    return df


def _get_normalized_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    類似度計算用にデータを正規化（Min-Max Scaling）します。
    """
    global _NORMALIZED_DF_CACHE
    if _NORMALIZED_DF_CACHE is not None:
        return _NORMALIZED_DF_CACHE

    # 分析対象カラムを収集
    all_features = (
        SIMILARITY_FEATURES["target"]
        + SIMILARITY_FEATURES["related"]
        + SIMILARITY_FEATURES["regional"]
    )

    # 存在するカラムのみ抽出
    valid_features = [col for col in all_features if col in df.columns]

    if not valid_features:
        return pd.DataFrame()

    # 数値変換（エラー値はNaNに）
    numeric_df = df.set_index("市区町村ｺｰﾄﾞ")[valid_features].apply(
        pd.to_numeric, errors="coerce"
    )

    # 欠損値処理（平均値で埋める、あるいは0埋め）
    numeric_df = numeric_df.fillna(numeric_df.mean())

    # 正規化 (Min-Max Scaling)
    # 値が全て同じ場合などのゼロ除算回避
    min_val = numeric_df.min()
    max_val = numeric_df.max()
    diff = max_val - min_val
    diff[diff == 0] = 1  # 回避策

    normalized_df = (numeric_df - min_val) / diff

    _NORMALIZED_DF_CACHE = normalized_df
    return normalized_df


def _load_coordinates() -> pd.DataFrame | None:
    """
    latest.csv から市区町村ごとの座標（緯度・経度）を読み込み、
    中心座標（平均値）を算出します。
    """
    file_path = DATA_DIR / "latest.csv"
    if not file_path.exists():
        return None

    try:
        # 必要な列のみ読み込む (Index 4:Code, 12:Lat, 13:Lon)
        # ヘッダー名は文字化けの可能性があるため、usecolsで番号指定推奨だが、
        # pandas read_csvは列名指定が安全。
        # ここでは全列読んでilocで抽出する方が確実
        df = pd.read_csv(file_path, encoding="utf-8")

        # 列位置で抽出 (コード, 緯度, 経度)
        coord_df = df.iloc[:, [4, 12, 13]].copy()
        coord_df.columns = ["市区町村ｺｰﾄﾞ", "lat", "lon"]

        # コードのゼロ埋め (5桁)
        coord_df["市区町村ｺｰﾄﾞ"] = coord_df["市区町村ｺｰﾄﾞ"].astype(str).str.zfill(5)

        # 数値化
        coord_df["lat"] = pd.to_numeric(coord_df["lat"], errors="coerce")
        coord_df["lon"] = pd.to_numeric(coord_df["lon"], errors="coerce")

        # 市区町村ごとに平均をとって中心とする
        grouped = coord_df.groupby("市区町村ｺｰﾄﾞ")[["lat", "lon"]].mean().reset_index()

        return grouped
    except Exception as e:
        print(f"Error loading coordinates: {e}")
        return None


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """コサイン類似度を計算 (0-1範囲に正規化はせず、-1~1を返す)"""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(vec1, vec2) / (norm1 * norm2)


def _euclidean_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    ユークリッド距離を類似度スコア(0-1)に変換
    距離が近いほど 1 に近づく
    """
    dist = np.linalg.norm(vec1 - vec2)
    # 距離の逆数や指数関数でスコア化
    # 以前の 1/(1+dist) だと、正規化された空間(最大距離√N)ではスコアが高止まりしやすいため、
    # 係数を掛けて減衰を急激にする (距離0.1でスコア0.5程度になるように)
    return 1.0 / (1.0 + 10 * dist)


# --- 公開API ---


def get_combined_data(suffixes: list[str] | None = None) -> pd.DataFrame | None:
    """
    複数のデータセットを結合して返します。
    デフォルトでは a〜j 全てを結合します。
    """
    global _MERGED_DF_CACHE

    if suffixes is None and _MERGED_DF_CACHE is not None:
        return _MERGED_DF_CACHE

    if suffixes is None:
        suffixes = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

    if not suffixes:
        return None

    base_suffix = suffixes[0]
    merged_df = _load_dataset(base_suffix)

    if merged_df is None:
        print(f"Base dataset '{base_suffix}' could not be loaded.")
        return None

    # 後続のデータセットを結合
    for suffix in suffixes[1:]:
        df = _load_dataset(suffix)
        if df is not None:
            # キー以外の重複カラムを削除
            cols_to_drop = [
                c for c in df.columns if c in merged_df.columns and c != "市区町村ｺｰﾄﾞ"
            ]
            df_to_merge = df.drop(columns=cols_to_drop)
            merged_df = pd.merge(merged_df, df_to_merge, on="市区町村ｺｰﾄﾞ", how="left")

    # 座標データを結合
    coords_df = _load_coordinates()
    if coords_df is not None:
        merged_df = pd.merge(merged_df, coords_df, on="市区町村ｺｰﾄﾞ", how="left")

    if len(suffixes) == 10:
        _MERGED_DF_CACHE = merged_df

    return merged_df


def get_municipalities(prefecture: str | None = None) -> list[dict]:
    """
    自治体のリストを返します。
    """
    df = get_combined_data()
    if df is None:
        return []

    if prefecture and "都道府県" in df.columns:
        df = df[df["都道府県"] == prefecture]
    elif prefecture:
        return []

    result = []
    # イテレーション
    for _, row in df.iterrows():
        code = row.get("市区町村ｺｰﾄﾞ")
        name = row.get("市区町村")
        pref = row.get("都道府県", "")
        lat = row.get("lat")
        lon = row.get("lon")

        if code and name:
            result.append(
                {
                    "code": str(code),
                    "name": str(name),
                    "pref": str(pref),
                    "lat": lat if pd.notnull(lat) else None,
                    "lon": lon if pd.notnull(lon) else None,
                }
            )

    return result


def get_municipality_details(city_code: str) -> dict:
    """
    指定された自治体の全データを辞書形式で返します。
    """
    df = get_combined_data()
    if df is None:
        return {}

    city_code = str(city_code).replace(".0", "")
    row = df[df["市区町村ｺｰﾄﾞ"] == city_code]

    if row.empty:
        return {}

    return row.iloc[0].where(pd.notnull(row.iloc[0]), None).to_dict()


def get_all_data_json() -> list[dict]:
    """
    全自治体のデータを辞書リストとして返します。
    Map表示用などに使用。
    """
    df = get_combined_data()
    if df is None:
        return []

    return df.where(pd.notnull(df), None).to_dict(orient="records")


def get_value(city_code: str, column_name: str):
    """
    特定の自治体の特定のデータ値を取得します。
    """
    df = get_combined_data()
    if df is None:
        return None

    city_code = str(city_code).replace(".0", "")
    row = df[df["市区町村ｺｰﾄﾞ"] == city_code]

    if row.empty or column_name not in row.columns:
        return None

    return row.iloc[0][column_name]


def get_similar_municipalities(target_city_code: str, limit: int = 5) -> list[dict]:
    """
    指定された自治体と類似度の高い自治体をリストアップします。
    仕様に基づき、ターゲット傾向、関連特性、地域特性の3つの観点からスコアを算出します。
    """
    df = get_combined_data()
    if df is None:
        return []

    target_city_code = str(target_city_code).replace(".0", "")

    # 正規化データの取得
    norm_df = _get_normalized_data(df)
    if norm_df.empty or target_city_code not in norm_df.index:
        return []

    target_vec_full = norm_df.loc[target_city_code]
    results = []

    # 各指標グループのカラムが存在するか確認
    cols = norm_df.columns
    target_cols = [c for c in SIMILARITY_FEATURES["target"] if c in cols]
    related_cols = [c for c in SIMILARITY_FEATURES["related"] if c in cols]
    regional_cols = [c for c in SIMILARITY_FEATURES["regional"] if c in cols]

    for city_code, row in norm_df.iterrows():
        if str(city_code) == target_city_code:
            continue

        # 1. ターゲット傾向 (人口動態など)
        # トレンド(Cosine)を重視しつつ、絶対的な規模感(Euclidean)も加味する
        s1 = 0.0
        if target_cols:
            s1_cos = _cosine_similarity(
                target_vec_full[target_cols].values, row[target_cols].values
            )
            s1_euc = _euclidean_similarity(
                target_vec_full[target_cols].values, row[target_cols].values
            )
            # コサイン(傾向) 8 : ユークリッド(規模) 2 の割合でブレンド
            s1 = (s1_cos * 0.8) + (s1_euc * 0.2)

        # 2. 関連特性 (社会要因)
        # こちらもトレンドと規模をブレンド
        s2 = 0.0
        if related_cols:
            s2_cos = _cosine_similarity(
                target_vec_full[related_cols].values, row[related_cols].values
            )
            s2_euc = _euclidean_similarity(
                target_vec_full[related_cols].values, row[related_cols].values
            )
            s2 = (s2_cos * 0.6) + (s2_euc * 0.4)

        # 3. 地域特性 (規模・財政)
        # 地域の「土台」としての類似性なので、規模を評価するユークリッドを重視
        s3 = 0.0
        if regional_cols:
            s3_cos = _cosine_similarity(
                target_vec_full[regional_cols].values, row[regional_cols].values
            )
            s3_euc = _euclidean_similarity(
                target_vec_full[regional_cols].values, row[regional_cols].values
            )
            s3 = (s3_cos * 0.15) + (s3_euc * 0.85)

        # 総合スコア計算
        # ターゲット指標を最重視(60%)、3指標の乗算項はバランスよく似ているとボーナス
        score = (s1 * 0.6) + (s2 * 0.15) + (s3 * 0.10) + (s1 * s2 * s3 * 0.15)

        # データ格納
        # 表示用に元のデータフレームから名前等を取得
        original_row = df[df["市区町村ｺｰﾄﾞ"] == city_code].iloc[0]

        # 都道府県名をコードから取得
        pref_code = str(city_code)[:2]
        pref_name = PREF_MAP.get(pref_code, "")

        results.append(
            {
                "code": city_code,
                "name": original_row.get("市区町村", "Unknown"),
                "pref": pref_name,
                "score": round(score * 100, 1),  # パーセント表示
                "factors": {
                    "target_similarity": round(s1 * 100, 1),
                    "related_similarity": round(s2 * 100, 1),
                    "regional_similarity": round(s3 * 100, 1),
                },
            }
        )

    # スコア順にソート
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:limit]

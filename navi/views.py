from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Region, StatisticalData
from .utils import get_similar_municipalities, get_all_data_json, get_municipality_details, get_municipalities
import json
import numpy as np
import random

# 都道府県の座標 (経度, 緯度)
PREF_COORDINATES = {
    "北海道": [141.35, 43.06], "青森県": [140.74, 40.82], "岩手県": [141.15, 39.70], "宮城県": [140.87, 38.26],
    "秋田県": [140.10, 39.72], "山形県": [140.36, 38.24], "福島県": [140.47, 37.75], "茨城県": [140.44, 36.34],
    "栃木県": [139.88, 36.56], "群馬県": [139.06, 36.39], "埼玉県": [139.63, 35.85], "千葉県": [140.12, 35.60],
    "東京都": [139.69, 35.68], "神奈川県": [139.64, 35.44], "新潟県": [139.02, 37.90], "富山県": [137.21, 36.69],
    "石川県": [136.62, 36.59], "福井県": [136.22, 36.06], "山梨県": [138.56, 35.66], "長野県": [138.18, 36.65],
    "岐阜県": [136.72, 35.39], "静岡県": [138.38, 34.97], "愛知県": [136.90, 35.18], "三重県": [136.51, 34.73],
    "滋賀県": [135.86, 35.00], "京都府": [135.75, 35.02], "大阪府": [135.52, 34.68], "兵庫県": [135.18, 34.69],
    "奈良県": [135.83, 34.68], "和歌山県": [135.16, 34.22], "鳥取県": [134.23, 35.50], "島根県": [133.05, 35.47],
    "岡山県": [133.93, 34.66], "広島県": [132.45, 34.39], "山口県": [131.47, 34.18], "徳島県": [134.55, 34.06],
    "香川県": [134.04, 34.34], "愛媛県": [132.76, 33.84], "高知県": [133.53, 33.55], "福岡県": [130.41, 33.60],
    "佐賀県": [130.29, 33.24], "長崎県": [129.87, 32.74], "熊本県": [130.74, 32.78], "大分県": [131.61, 33.23],
    "宮崎県": [131.42, 31.91], "鹿児島県": [130.55, 31.56], "沖縄県": [127.68, 26.21]
}


# --- 内部ヘルパー ---
def _find_city_code(region_obj):
    """Regionモデル(DB)からExcelデータの市区町村コードを検索する"""
    # 都道府県で絞り込み
    candidates = get_municipalities(region_obj.prefecture)
    
    # 名前で完全一致検索
    for city in candidates:
        if city["name"] == region_obj.name:
            return city["code"]
            
    return None

def _numpy_converter(o):
    if isinstance(o, (np.integer, np.int64)):
        return int(o)
    if isinstance(o, (np.floating, np.float64)):
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


# ① トップページ
def index(request):
    regions = Region.objects.all()
    return render(request, "navi/index.html", {"regions": regions})


def dashboard(request):
    return render(request, "navi/dashboard.html")


def data(request):
    return render(request, "navi/data.html")


def cases(request):
    return render(request, "navi/cases.html")


def learning(request):
    return render(request, "navi/learning.html")


def settings(request):
    return render(request, "navi/settings.html")


# ② 分析結果ページ
def analysis(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    
    # Excelデータから詳細を取得
    city_code = _find_city_code(region)
    excel_data = {}
    if city_code:
        excel_data = get_municipality_details(city_code)

    # DBの統計データ（もしあれば）
    latest_stat = region.stats.order_by("-year").first()
    
    # JSONシリアライズ（グラフ用）
    excel_data_json = "{}"
    if excel_data:
        try:
            excel_data_json = json.dumps(excel_data, default=_numpy_converter, ensure_ascii=False)
        except Exception as e:
            print(f"JSON serialize error: {e}")

    context = {
        "region_name": f"{region.prefecture} {region.name}",
        "latest_data": latest_stat,
        "excel_data": excel_data, # テーブル表示用
        "excel_data_json": excel_data_json, # JSグラフ用
        "population_graph_url": "https://placehold.co/600x400?text=Graph", # フォールバック
    }
    return render(request, "navi/analysis.html", context)


# ③ 類似地域ページ
def similar(request, region_id):
    base_region = get_object_or_404(Region, id=region_id)
    city_code = _find_city_code(base_region)
    
    similar_list = []
    if city_code:
        # 上位10件を取得
        similar_list = get_similar_municipalities(city_code, limit=10)

    context = {
        "base_region_name": base_region.name,
        "similar_regions": similar_list,
    }
    return render(request, "navi/similar.html", context)


# ④ ヒートマップページ
def heatmap(request, region_id):
    base_region = get_object_or_404(Region, id=region_id)
    
    # 地図の初期表示位置を決定
    center = PREF_COORDINATES.get(base_region.prefecture, [138.252924, 36.204824])
    zoom = 8 if base_region.prefecture in PREF_COORDINATES else 5
    
    context = {
        "base_region": base_region,
        "initial_view": {
            "center": center,
            "zoom": zoom
        }
    }
    return render(request, "navi/heatmap.html", context)


# ④ ヒートマップAPI (ArcGIS用)
def heatmap_api(request, region_id):
    base_region = get_object_or_404(Region, id=region_id)
    city_code = _find_city_code(base_region)
    
    # ターゲットとの類似度を全件取得 (limitを大きく設定)
    # city_codeが見つからない場合は空リスト
    similar_scores = []
    if city_code:
        similar_scores = get_similar_municipalities(city_code, limit=2000)
    
    # スコア検索用辞書 {code: score}
    score_map = {item["code"]: item["score"] for item in similar_scores}
    
    # 全データ検索用辞書 (名前マッチング用)
    # get_municipalities() は {code, name, pref, lat, lon} のリストを返す
    # Regionモデルにはコードがないため、(県, 名前) -> code のマップを作る
    all_munis = get_municipalities()
    name_to_code = {(m["pref"], m["name"]): m["code"] for m in all_munis}
    
    # 正確な座標マップ {code: (lat, lon)}
    code_to_coords = {
        m["code"]: (m["lat"], m["lon"]) 
        for m in all_munis 
        if m.get("lat") is not None and m.get("lon") is not None
    }

    features = []
    for region in Region.objects.all():
        # Regionに対応するコードを探す
        key = (region.prefecture, region.name)
        code = name_to_code.get(key)
        
        score = 0
        if code:
            score = score_map.get(code, 0)

        # 座標の決定
        geometry = None
        
        # 1. 正確な座標があればそれを使う
        if code and code in code_to_coords:
            lat, lon = code_to_coords[code]
            geometry = {
                "type": "Point",
                "coordinates": [lon, lat]
            }
        else:
            # 2. なければ都道府県中心から少しずらした点を生成 (Fallback)
            pref_center = PREF_COORDINATES.get(region.prefecture)
            if pref_center:
                # 重なりを防ぐためにランダムにずらす (Jitter)
                # 約 +/- 10km 程度の範囲
                lon = pref_center[0] + random.uniform(-0.15, 0.15)
                lat = pref_center[1] + random.uniform(-0.15, 0.15)
                geometry = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }

        if geometry:
            # GeoJSONのFeatureを作成
            feature = {
                "type": "Feature",
                "properties": {
                    "name": region.name, 
                    "score": score,
                    "prefecture": region.prefecture
                },
                "geometry": geometry,
            }
            features.append(feature)

    return JsonResponse({"type": "FeatureCollection", "features": features})


def maps_view(request):
    # 年度ごとのタイルレイヤー URL を管理
    tilelayers = {
        "2010": "https://tiles.arcgis.com/tiles/eVAQjIkMgiRvTUEY/arcgis/rest/services/2010改2/MapServer",
        "2015": "https://tiles.arcgis.com/tiles/eVAQjIkMgiRvTUEY/arcgis/rest/services/2015改2/MapServer",
        "2020": "https://tiles.arcgis.com/tiles/eVAQjIkMgiRvTUEY/arcgis/rest/services/2020改２/MapServer",
    }
    return render(request, "legacy/maps.html", {"tilelayers": tilelayers})


def api_map_data(request):
    """ArcGIS等で地図表示するためのGeoJSONデータを返す"""
    # 1. Pandasデータフレームから全データを取得
    all_data = get_all_data_json() # List[Dict]
    
    # 検索しやすいように (都道府県, 市区町村) をキーにした辞書に変換
    data_map = {}
    for item in all_data:
        p = item.get("都道府県")
        n = item.get("市区町村")
        if p and n:
            data_map[(p, n)] = item

    # 2. Region (Geometry) と結合
    features = []
    for region in Region.objects.all():
        key = (region.prefecture, region.name)
        props = data_map.get(key, {})
        
        # Region由来のIDや名前も確保
        props["region_id"] = region.id
        props["region_name"] = region.name
        props["prefecture"] = region.prefecture
        
        # Noneの値を空文字や0に変換（JSONシリアライズ対策）
        sanitized_props = {}
        for k, v in props.items():
            if v is None:
                sanitized_props[k] = ""
            else:
                sanitized_props[k] = v

        feature = {
            "type": "Feature",
            "properties": sanitized_props,
            "geometry": region.geometry, 
        }
        features.append(feature)

    return JsonResponse({"type": "FeatureCollection", "features": features})


def api_municipality_data(request, city_code):
    """特定自治体の詳細データを返す"""
    data = get_municipality_details(city_code)
    return JsonResponse(data, safe=False)
#def maps_view(request):
    # 年度ごとの WebMap ID を Python 側で管理
    #webmaps = {
        #"2010": "2e32d111b7bb45b8b8cc3b73251045f3",  # ← 実際の WebMap ID に置き換え
        #"2015": "b6ff72960ec349d1880fffa7e14f0416",
        #"2020": "611d6da8c6cf4c79ad5520d56fdf367b",
    #}
    #return render(request, "legacy/maps.html", {"webmaps": webmaps})
from django.shortcuts import render

def maps_view(request):
    # 年度ごとのタイルレイヤー URL を管理
    tilelayers = {
        "2010": "https://tiles.arcgis.com/tiles/eVAQjIkMgiRvTUEY/arcgis/rest/services/2010改2/MapServer",
        "2015": "https://tiles.arcgis.com/tiles/eVAQjIkMgiRvTUEY/arcgis/rest/services/2015改2/MapServer",
        "2020": "https://tiles.arcgis.com/tiles/eVAQjIkMgiRvTUEY/arcgis/rest/services/2020改２/MapServer",
    }
    return render(request, "legacy/maps.html", {"tilelayers": tilelayers})

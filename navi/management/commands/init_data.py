# app/management/commands/init_data.py
from django.core.management.base import BaseCommand
from navi.models import Region, StatisticalData
from navi import utils
import pandas as pd

class Command(BaseCommand):
    help = 'Excelファイルから実データを投入する'

    PREF_MAP = {
        "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県", "05": "秋田県",
        "06": "山形県", "07": "福島県", "08": "茨城県", "09": "栃木県", "10": "群馬県",
        "11": "埼玉県", "12": "千葉県", "13": "東京都", "14": "神奈川県", "15": "新潟県",
        "16": "富山県", "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
        "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県", "25": "滋賀県",
        "26": "京都府", "27": "大阪府", "28": "兵庫県", "29": "奈良県", "30": "和歌山県",
        "31": "鳥取県", "32": "島根県", "33": "岡山県", "34": "広島県", "35": "山口県",
        "36": "徳島県", "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
        "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県", "45": "宮崎県",
        "46": "鹿児島県", "47": "沖縄県"
    }

    def handle(self, *args, **options):
        self.stdout.write("Excelデータを読み込み中...")
        
        # 実データを取得
        df = utils.get_combined_data()
        if df is None:
            self.stdout.write(self.style.ERROR('データの読み込みに失敗しました。navi/data/内のファイルを確認してください。'))
            return

        # 既存データをクリア
        Region.objects.all().delete()
        self.stdout.write("既存のRegionデータを削除しました。")

        count = 0
        stats_count = 0
        
        # データフレームをイテレート
        for _, row in df.iterrows():
            code = str(row.get("市区町村ｺｰﾄﾞ", "")).zfill(5)
            name = row.get("市区町村")
            
            if not name:
                continue

            # コードから都道府県を判定
            pref_code = code[:2]
            pref = self.PREF_MAP.get(pref_code)
            
            if not pref:
                # 都道府県が判定できない場合はスキップ
                continue

            # Region作成
            # geometryは現状データがないためNoneとする
            region = Region.objects.create(
                prefecture=str(pref),
                name=str(name),
                geometry=None 
            )
            count += 1
            
            # 統計データ作成 (2020年として登録)
            # 総人口
            pop_val = row.get("総人口")
            population = None
            if pd.notnull(pop_val):
                try:
                    # カンマが入っている場合などを考慮して数値化（utilsでクリーニング済みだが念のため）
                    population = int(float(str(pop_val).replace(",", "")))
                except ValueError:
                    population = None

            # 空き家率
            # データ項目に直接「空き家率」はないため、現状はNoneまたは0とする
            # 将来的に計算ロジックを入れる場合はここに追加
            empty_house_rate = None

            StatisticalData.objects.create(
                region=region,
                year=2020,
                population=population,
                empty_house_rate=empty_house_rate
            )
            stats_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'データ投入完了: {count} 地域, {stats_count} 統計レコードを作成しました。'))
from django.db import models

class Region(models.Model):
    """地域マスタ（地図の形などの普遍的な情報）"""
    name = models.CharField("市区町村名", max_length=100)
    prefecture = models.CharField("都道府県名", max_length=50)
    
    # GeoJSONのgeometry部分（座標データ）をそのまま入れる箱
    # SQLiteでも使えるJSONFieldを利用
    geometry = models.JSONField("境界線データ", null=True, blank=True)

    def __str__(self):
        return f"{self.prefecture} {self.name}"

class StatisticalData(models.Model):
    """統計データ（年ごとの変化する情報）"""
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="stats")
    year = models.IntegerField("年")
    
    # 分析に使う指標（とりあえず人口と空き家率）
    population = models.IntegerField("人口", null=True, blank=True)
    empty_house_rate = models.FloatField("空き家率", null=True, blank=True)

    class Meta:
        unique_together = ('region', 'year') # 同じ地域の同じ年は重複させない

    def __str__(self):
        return f"{self.region.name} ({self.year})"
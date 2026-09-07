# -*- coding: utf-8 -*-
"""
07 品类与商品分析
数据源：SQL 结果集 07_category_*
输出：
  category_performance.png 品类 GMV 结构 + 价格带结构
  category_gender.png      性别 x 品类 GMV 热力图
  category_copurchase.png  跨品类关联购买 TOP
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_sql_result, savefig, PALETTE

perf = load_sql_result("07_category", 1).sort_values("gmv", ascending=False)
band = load_sql_result("07_category", 2)
gx = load_sql_result("07_category", 3)
co = load_sql_result("07_category", 4)

# ---------- 品类 GMV 结构 + 价格带 ----------
fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
ax = axes[0]
x = np.arange(len(perf))
bars = ax.bar(x, perf["gmv"] / 10000, color=[PALETTE[0] if i < 3 else PALETTE[4] for i in range(len(perf))])
for xi, (_, row) in zip(x, perf.iterrows()):
    ax.text(xi, row["gmv"] / 10000 + 0.5, f"{row['gmv_share_pct']:.0f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(perf["category"], rotation=35, ha="right")
ax.set_ylabel("GMV（万元）")
ax.set_title("品类 GMV TOP3：服饰 / 数码 / 美妆 贡献 {:.0f}%".format(
    perf.head(3)["gmv_share_pct"].sum()))

ax = axes[1]
band_order = ["0~50元", "50~100元", "100~200元", "200~500元", "500元以上"]
band["band"] = pd.Categorical(band["price_band"], categories=band_order, ordered=True)
band = band.sort_values("band")
x = np.arange(len(band))
bars = ax.bar(x - 0.19, band["order_share_pct"], 0.38, label="订单占比 %", color=PALETTE[1])
bars2 = ax.bar(x + 0.19, band["gmv"] / band["gmv"].sum() * 100, 0.38, label="GMV 占比 %", color=PALETTE[0])
for xi, (_, row) in zip(x, band.iterrows()):
    ax.text(xi - 0.19, row["order_share_pct"] + 1, f"{row['order_share_pct']:.0f}%", ha="center", fontsize=8.5)
    ax.text(xi + 0.19, row["gmv"] / band["gmv"].sum() * 100 + 1, f"{row['gmv']/band['gmv'].sum()*100:.0f}%",
            ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(band["band"])
ax.set_ylabel("占比 %")
ax.set_title("价格带结构：低价订单多、高价贡献大（200 元以上占 GMV {:.0f}%）".format(
    band[band["band"].isin(["200~500元", "500元以上"])]["gmv"].sum() / band["gmv"].sum() * 100))
ax.legend()
fig.tight_layout()
savefig(fig, "category_performance")

# ---------- 性别 x 品类 ----------
piv = gx.pivot(index="category", columns="sex", values="gmv").fillna(0)
piv["total"] = piv.sum(axis=1)
piv = piv.sort_values("total", ascending=False).drop(columns="total")
fig, ax = plt.subplots(figsize=(9.5, 7))
data = np.log1p(piv.values)
im = ax.imshow(data, cmap="YlGnBu", aspect="auto")
ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns)
ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index)
for i in range(len(piv.index)):
    for j in range(len(piv.columns)):
        v = piv.values[i, j]
        ax.text(j, i, f"¥{v/10000:.1f}万", ha="center", va="center", fontsize=9,
                color="#333" if v < piv.values.max() * 0.5 else "white")
ax.set_title("性别 × 品类 GMV（万元，log 色阶）\n服饰/美妆显著女性向，数码/汽车/家电男性向 → 差异化推荐与选品", fontsize=12)
fig.colorbar(im, ax=ax, shrink=0.85)
savefig(fig, "category_gender")

# ---------- 跨品类关联 ----------
fig, ax = plt.subplots(figsize=(11, 6))
co = co.head(10).sort_values("related_users")
y = np.arange(len(co))
bars = ax.barh(y, co["related_users"], color=PALETTE[0])
for yi, (_, row) in zip(y, co.iterrows()):
    ax.text(row["related_users"] + 0.3, yi, f"{int(row['related_users'])} 用户", va="center", fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels([f"{a} × {b}" for a, b in zip(co["cat_a"], co["cat_b"])], fontsize=9.5)
ax.set_xlabel("关联购买用户数（7 天窗口）")
ax.set_title("跨品类关联购买 TOP10 → 捆绑销售 / 购物后推荐策略依据", fontsize=12)
savefig(fig, "category_copurchase")

print(f"  品类 TOP3 GMV 占比 {perf.head(3)['gmv_share_pct'].sum():.1f}% | "
      f"TOP1 关联对 {co['cat_a'].iloc[-1]} x {co['cat_b'].iloc[-1]}")

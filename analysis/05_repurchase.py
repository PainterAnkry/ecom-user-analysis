# -*- coding: utf-8 -*-
"""
05 复购与购买频次
数据源：SQL 结果集 05_repurchase_*
输出：
  repurchase_freq.png   订单数分布（人数/GMV 贡献）
  repurchase_gap.png    二次购买间隔分布
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_sql_result, savefig, PALETTE

freq = load_sql_result("05_repurchase", 1)
gap = load_sql_result("05_repurchase", 2)
summ = load_sql_result("05_repurchase", 3)

# ---------- 购买频次分布 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
order = ["1单", "2单", "3单", "4单", "5单", "6单及以上"]
freq["band"] = pd.Categorical(freq["order_cnt_band"], categories=order, ordered=True)
freq = freq.sort_values("band")
bars = ax.bar(range(len(freq)), freq["user_share_pct"], color=PALETTE[0])
for i, (_, row) in enumerate(freq.iterrows()):
    ax.text(i, row["user_share_pct"] + 0.7, f"{row['user_share_pct']:.1f}%", ha="center", fontsize=9)
ax.set_xticks(range(len(freq))); ax.set_xticklabels(freq["band"])
ax.set_ylabel("人数占比 %")
ax.set_title("买家购买频次分布（13 周）\n仅 1 单的买家占 {:.0f}%（首单易得，复购难）".format(
    freq[freq["band"] == "1单"]["user_share_pct"].iloc[0]))

ax = axes[1]
bars = ax.bar(range(len(freq)), freq["gmv_share_pct"], color=PALETTE[1])
for i, (_, row) in enumerate(freq.iterrows()):
    ax.text(i, row["gmv_share_pct"] + 0.7, f"{row['gmv_share_pct']:.1f}%", ha="center", fontsize=9)
ax.set_xticks(range(len(freq))); ax.set_xticklabels(freq["band"])
ax.set_ylabel("GMV 占比 %")
ax.set_title("购买频次的 GMV 贡献\n≥3 单买家贡献 {:.0f}% GMV → 高频用户是基本盘".format(
    freq[freq["band"] >= "3单"]["gmv_share_pct"].sum()))
fig.tight_layout()
savefig(fig, "repurchase_freq")

# ---------- 复购间隔 ----------
freq_1 = float(freq[freq["band"] == "1单"]["user_share_pct"].iloc[0])
rep2_share = round(100 - freq_1, 1)   # 复购渗透率 = 订单>=2 的买家占比（分桶用户会跨桶重复计数，不能直接加总）
peak_band = gap.loc[gap["pct_of_buyers"].idxmax()]
fig, ax = plt.subplots(figsize=(10, 5.5))
gap_order = ["7天内", "8~30天", "31~60天", "60天以上"]
gap["band"] = pd.Categorical(gap["gap_band"], categories=gap_order, ordered=True)
gap = gap.sort_values("band")
colors = [PALETTE[2], PALETTE[0], PALETTE[1], PALETTE[5]]
bars = ax.bar(range(len(gap)), gap["pct_of_buyers"], color=colors)
for i, (_, row) in enumerate(gap.iterrows()):
    ax.text(i, row["pct_of_buyers"] + 0.4, f"{row['pct_of_buyers']:.1f}%\n({int(row['n_pairs']):,} 对)",
            ha="center", fontsize=9)
ax.set_xticks(range(len(gap))); ax.set_xticklabels(gap["band"])
ax.set_ylabel("占全部买家比例 %")
ax.set_title(f"首购→复购间隔分布（复购渗透率 {rep2_share:.1f}%）\n"
             f"{peak_band['pct_of_buyers']:.1f}% 买家集中在 {peak_band['gap_band']} 二次购买 → "
             f"首购后第 2~4 周是复购运营关键期", fontsize=12)
savefig(fig, "repurchase_gap")

print(f"  复购: 复购渗透率(≥2单) {rep2_share:.1f}% | 复购用户人均复购次数 {summ['avg_repurchase_times'].iloc[0]:.1f} "
      f"| 平均首复购间隔 {summ['avg_user_avg_gap_days'].iloc[0]:.1f} 天")

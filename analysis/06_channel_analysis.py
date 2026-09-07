# -*- coding: utf-8 -*-
"""
06 渠道质量与投放效率
数据源：SQL 结果集 06_channel_* + 成本表
输出：
  channel_quality.png  渠道漏斗质量（ARPU / 付费渗透 / 新客30天首购）
  channel_roas.png     付费渠道 ROAS（GMV / 获客花费）
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_sql_result, savefig, PALETTE

q = load_sql_result("06_channel", 1).sort_values("gmv", ascending=False)
roas = load_sql_result("06_channel", 2).sort_values("gmv", ascending=False)
new30 = load_sql_result("06_channel", 3).sort_values("first_buy_30d_pct", ascending=False)

# ---------- 渠道质量：GMV / ARPU / 新客首购率 ----------
fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
ax = axes[0]
x = np.arange(len(q))
bars = ax.bar(x, q["gmv"] / 10000, color=PALETTE[0])
for xi, (_, row) in zip(x, q.iterrows()):
    ax.text(xi, row["gmv"] / 10000 + 0.8, f"{row['gmv_share_pct']:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(q["channel"], rotation=20)
ax.set_ylabel("GMV（万元）")
ax.set_title("渠道 GMV 贡献\n自然搜索占 {:.0f}%，付费渠道合计 {:.0f}%".format(
    q[q["channel"] == "自然搜索"]["gmv_share_pct"].iloc[0],
    q[~q["channel"].isin(["自然搜索", "直接访问"])]["gmv_share_pct"].sum()))

ax = axes[1]
bars = ax.bar(x, q["arpu"], color=PALETTE[1])
for xi, (_, row) in zip(x, q.iterrows()):
    ax.text(xi, row["arpu"] + 3, f"{row['arpu']:.0f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(q["channel"], rotation=20)
ax.set_ylabel("ARPU（元/注册用户）")
ax.set_title("单位注册用户价值（ARPU）\n自然搜索 > 直接访问 > 社媒/短信 > 信息流")

ax = axes[2]
bars = ax.bar(range(len(new30)), new30["first_buy_30d_pct"], color=PALETTE[2])
for xi, (_, row) in zip(range(len(new30)), new30.iterrows()):
    ax.text(xi, row["first_buy_30d_pct"] + 0.4, f"{row['first_buy_30d_pct']:.1f}%\n{int(row['new_users'])}新客",
            ha="center", fontsize=8.5)
ax.set_xticks(range(len(new30))); ax.set_xticklabels(new30["channel"], rotation=20)
ax.set_ylabel("30 天首购率 %")
ax.set_title("新客 30 天首购率（获客质量）\n投放渠道首购弱 → 新手期承接不足")
fig.suptitle("渠道质量对比：免费渠道“少而精”，广告渠道“多而杂”", fontsize=13, y=1.02)
fig.tight_layout()
savefig(fig, "channel_quality")

# ---------- ROAS ----------
fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(roas))
bars = ax.bar(x, roas["roas"], color=[PALETTE[0], PALETTE[2], PALETTE[5]], width=0.5)
for xi, (_, row) in zip(x, roas.iterrows()):
    ax.text(xi, row["roas"] + 0.06, f"ROAS {row['roas']:.2f}\n花费 ¥{row['total_spend']:,.0f}\nGMV ¥{row['gmv']:,.0f}",
            ha="center", fontsize=9)
ax.axhline(1, color="gray", ls="--", lw=1)
ax.text(2.2, 1.06, "ROAS=1 盈亏线", color="gray", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{r}（{int(roas.loc[i,'registered_users'])} 注册）"
                                      for i, r in enumerate(roas["channel"])])
ax.set_ylabel("ROAS（GMV/花费）")
ax.set_title("付费渠道 ROAS：短信/邮件 最优但体量小；信息流广告花费最高、ROAS 最低 → 预算再配置方向", fontsize=12)
savefig(fig, "channel_roas")

print("  渠道 ROAS:", {r["channel"]: round(r["roas"], 2) for _, r in roas.iterrows()})
print(f"  信息流广告花费 {roas[roas['channel']=='信息流广告']['total_spend'].iloc[0]:,.0f} 元，"
      f"ROAS {roas[roas['channel']=='信息流广告']['roas'].iloc[0]:.2f}")

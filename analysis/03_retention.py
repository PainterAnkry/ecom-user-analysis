# -*- coding: utf-8 -*-
"""
03 留存分析
数据源：SQL 结果集 03_retention_*（注册队列周留存）
输出：
  retention_heatmap.png  注册队列留存热力矩阵
  retention_curves.png   各注册周队列留存衰减曲线
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_sql_result, savefig, PALETTE

r = load_sql_result("03_retention", 2)
r["reg_week_start"] = pd.to_datetime(r["reg_week_start"]).dt.strftime("%m-%d")

piv = r.pivot_table(index="reg_week_start", columns="week_offset", values="ret_rate")
piv = piv.reindex(index=piv.index[::-1])          # 最早的队列在最上面
offsets = piv.columns.astype(int).tolist()

fig, ax = plt.subplots(figsize=(14, 8))
cmap = plt.cm.YlGnBu
data = piv.values
im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=100)
ax.set_xticks(range(len(offsets)))
ax.set_xticklabels([f"注册周" if o == 0 else f"第{o}周" for o in offsets], fontsize=9)
ax.set_yticks(range(len(piv.index)))
ax.set_yticklabels([f"{d} 注册" for d in piv.index], fontsize=9)
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        v = data[i, j]
        if np.isnan(v):
            continue
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                color="white" if v > 65 else "#333333")
ax.set_title("注册队列周留存热力图（留存率 %）\n新客留存随周龄衰减，第 1 周 ~80% → 第 8 周后 ~55% 企稳",
             fontsize=13)
cbar = fig.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label("周留存率 %")
savefig(fig, "retention_heatmap")

# ---------- 衰减曲线（抽样队列 + 平均）----------
fig, ax = plt.subplots(figsize=(11, 6))
cohorts = sorted(r["reg_week_no"].unique())
for wk in cohorts[0::3][:4]:                       # 抽样展示
    s = r[r["reg_week_no"] == wk].sort_values("week_offset")
    ax.plot(s["week_offset"], s["ret_rate"], marker="o", ms=4,
            label=f"注册周 {wk}（{s['reg_week_start'].iloc[0]} 起）", color=PALETTE[cohorts.index(wk) % 4])
avg = r.groupby("week_offset")["ret_rate"].mean()
ax.plot(avg.index, avg.values, "k--", lw=2, label="全部队列平均")
ax.set_xlabel("注册后第几周"); ax.set_ylabel("周留存率 %")
ax.set_title("注册队列留存衰减：前 4 周流失最快（新手期承接入口），8 周后进入稳定老客态")
ax.legend()
savefig(fig, "retention_curves")

w1 = r[r["week_offset"] == 1]["ret_rate"].mean()
w8 = r[r["week_offset"] == 8]["ret_rate"].mean() if (r["week_offset"] == 8).any() else np.nan
print(f"  留存: 注册次周平均留存 {w1:.1f}% | 第8周 {w8:.1f}%（可用 4 周关键期运营定义）")

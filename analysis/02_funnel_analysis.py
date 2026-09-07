# -*- coding: utf-8 -*-
"""
02 转化漏斗分析
数据源：SQL 结果集 02_funnel_*
输出：
  funnel_overall.png   全站累计漏斗
  funnel_channel.png   渠道漏斗转化率对比
  funnel_device.png    设备漏斗对比
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_sql_result, savefig, PALETTE

STEP_ORDER = ["浏览商品(pv)", "加入购物车(cart)", "收藏商品(fav)", "支付下单(pay)"]

# ---------- 全站漏斗 ----------
f = load_sql_result("02_funnel", 1).set_index("step").loc[STEP_ORDER].reset_index()
pv_u = int(f.loc[0, "users"])
fig, ax = plt.subplots(figsize=(9, 5))
colors = [PALETTE[4], PALETTE[5], PALETTE[1], PALETTE[0]]
bars = ax.barh(f["step"][::-1], f["users"][::-1], color=colors[::-1])
for b, (_, row) in zip(bars, f.iloc[::-1].iterrows()):
    pct = 100 * row["users"] / pv_u
    ax.text(row["users"] + pv_u * 0.01, b.get_y() + b.get_height() / 2,
            f"{int(row['users']):,}  ({pct:.1f}%)", va="center", fontsize=10)
ax.set_xlim(0, pv_u * 1.35)
ax.set_xlabel("去重用户数（13 周累计口径）")
ax.set_title("全站转化漏斗：浏览 → 加购 → 收藏 → 支付\n"
             "长周期下“加购层”贴近浏览层，真正的转化收缩发生在 加购→支付（购物车遗弃）", fontsize=12)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
savefig(fig, "funnel_overall")

# ---------- 渠道漏斗 ----------
c = load_sql_result("02_funnel", 2).sort_values("view_to_pay_pct", ascending=False)
x = np.arange(len(c))
fig, ax = plt.subplots(figsize=(10, 5.5))
w = 0.26
for i, col in enumerate(["view_to_cart_pct", "cart_to_pay_pct", "view_to_pay_pct"]):
    ax.bar(x + (i - 1) * w, c[col], w, label={"view_to_cart_pct": "浏览→加购",
                                              "cart_to_pay_pct": "加购→支付",
                                              "view_to_pay_pct": "浏览→支付"}[col],
           color=PALETTE[[2, 1, 0][i]])
for xi, (_, row) in zip(x, c.iterrows()):
    ax.text(xi + w, row["view_to_pay_pct"] + 0.6, f"{row['view_to_pay_pct']:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(c["channel"])
ax.set_ylabel("转化率 %")
ax.set_title("分渠道漏斗：自然搜索/直接访问质量显著占优，付费广告量大人群杂")
ax.legend(ncol=3, loc="upper right")
savefig(fig, "funnel_channel")

# ---------- 设备漏斗 ----------
d = load_sql_result("02_funnel", 3).sort_values("pv_users", ascending=False)
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(d))
bars = ax.bar(x - 0.15, d["pv_users"], 0.3, label="浏览人数", color=PALETTE[4])
ax2 = ax.twinx()
bars2 = ax2.bar(x + 0.15, d["view_to_pay_pct"], 0.3, label="浏览→支付转化率 %", color=PALETTE[0])
ax.set_xticks(x); ax.set_xticklabels(d["device"])
ax.set_ylabel("浏览人数"); ax2.set_ylabel("浏览→支付转化率 %")
ax.set_title("分设备漏斗：PC 用户浏览少但转化最高（购物意图更明确）")
lines1, lab1 = ax.get_legend_handles_labels()
lines2, lab2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, lab1 + lab2, loc="upper right")
savefig(fig, "funnel_device")

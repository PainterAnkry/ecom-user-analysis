# -*- coding: utf-8 -*-
"""
01 EDA：用户结构画像 + 行为时段规律
结论写入 stdout 并在 output/charts 输出：
  eda_user_profile.png  用户结构（渠道/设备/城市/年龄性别/注册节奏）
  eda_hour_profile.png  各行为 24 小时分布（含业务结论：支付峰值滞后浏览）
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from common import query, savefig, PALETTE

# ---------- 用户结构 ----------
ch = query("SELECT channel, COUNT(*) AS n FROM users GROUP BY channel ORDER BY n DESC")
dev = query("SELECT device, COUNT(*) AS n FROM users GROUP BY device ORDER BY n DESC")
city = query("SELECT city_tier, COUNT(*) AS n FROM users GROUP BY city_tier")
age_sex = query("SELECT sex, FLOOR(age/10)*10 AS age_band, COUNT(*) AS n FROM users GROUP BY sex, age_band")
reg = query("SELECT DATE_FORMAT(reg_date, '%Y-%m') AS ym, COUNT(*) AS n FROM users GROUP BY ym ORDER BY ym")

fig, axes = plt.subplots(2, 2, figsize=(13, 8))
ax = axes[0][0]
bars = ax.barh(ch["channel"], ch["n"], color=PALETTE[:len(ch)])
for b, v in zip(bars, ch["n"]):
    ax.text(v + 20, b.get_y() + b.get_height() / 2, f"{v:,} ({v/ch['n'].sum()*100:.0f}%)", va="center", fontsize=9)
ax.set_title("注册渠道构成（获客来源结构）"); ax.set_xlabel("用户数")

ax = axes[0][1]
bars = ax.barh(dev["device"], dev["n"], color=[PALETTE[2], PALETTE[0], PALETTE[4]])
for b, v in zip(bars, dev["n"]):
    ax.text(v + 20, b.get_y() + b.get_height() / 2, f"{v:,}", va="center", fontsize=9)
ax.set_title("设备构成"); ax.set_xlabel("用户数")

ax = axes[1][0]
city_map = {1: "一线城市", 2: "二线城市", 3: "三线城市", 4: "四线及以下"}
city["label"] = city["city_tier"].map(city_map)
bars = ax.bar(city["label"], city["n"], color=PALETTE[:len(city)])
for b, v in zip(bars, city["n"]):
    ax.text(b.get_x() + b.get_width() / 2, v + 15, f"{v/ city['n'].sum() * 100:.0f}%", ha="center", fontsize=9)
ax.set_title("城市层级分布"); ax.set_ylabel("用户数")

ax = axes[1][1]
for i, sex in enumerate(["女", "男"]):
    s = age_sex[age_sex["sex"] == sex].sort_values("age_band")
    ax.bar(s["age_band"].astype(str) + "岁", s["n"], alpha=0.75, color=PALETTE[i], label=f"{sex}({s['n'].sum():,})")
ax.set_title("年龄结构（按性别）"); ax.set_xlabel("年龄"); ax.set_ylabel("用户数"); ax.legend()
fig.suptitle("用户画像 EDA", fontsize=14, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
savefig(fig, "eda_user_profile")
print(f"  EDA: 用户 {ch['n'].sum():,} | 女性占比 {age_sex[age_sex['sex']=='女']['n'].sum()/age_sex['n'].sum():.1%}")

# ---------- 注册节奏 ----------
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(reg["ym"], reg["n"], color=PALETTE[0])
for b, v in zip(bars, reg["n"]):
    ax.text(b.get_x() + b.get_width() / 2, v + 5, f"{v}", ha="center", fontsize=9)
ax.set_title("各月新增注册（获客节奏：6~7 月投放旺季拉新）")
ax.set_ylabel("注册用户数")
savefig(fig, "eda_reg_trend")

# ---------- 24 小时行为分布 ----------
h = query("SELECT hour, action, COUNT(*) AS n FROM behaviors GROUP BY hour, action")
h["zh"] = h["action"].map({"pv": "浏览", "cart": "加购", "fav": "收藏", "pay": "支付"})
h["share"] = h.groupby("action")["n"].transform(lambda s: s / s.sum() * 100)
peak_h = h.groupby("action").apply(lambda s: int(s.loc[s["share"].idxmax(), "hour"]), include_groups=False)
fig, ax = plt.subplots(figsize=(11, 5))
for i, action in enumerate(["pv", "cart", "pay"]):
    s = h[h["action"] == action].sort_values("hour")
    ax.plot(s["hour"], s["share"], marker="o", ms=4, label=f"{s['zh'].iloc[0]}(峰值 {peak_h[action]} 时)", color=PALETTE[i])
ax.axvline(peak_h["pay"], color="gray", ls=":", lw=1)
ax.set_title("各行为 24 小时分布（浏览→支付存在 1~2h 转化时滞 → 晚间推送/客服为黄金窗口）")
ax.set_xlabel("小时"); ax.set_ylabel("占该行为全天比例 %"); ax.legend()
savefig(fig, "eda_hour_profile")
print(f"  EDA: 浏览/加购/支付峰值小时 = {peak_h['pv']}/{peak_h['cart']}/{peak_h['pay']}")

# -*- coding: utf-8 -*-
"""
04 RFM 用户分层
数据源：SQL 结果集 04_rfm_*（NTILE 五分位打分 + 八宫格标签）
输出：
  rfm_segments.png  各分层 人数/GMV 双维度贡献
  rfm_matrix.png    R x F 矩阵（颜色=平均客单贡献）
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_sql_result, savefig, PALETTE

seg = load_sql_result("04_rfm", 2).sort_values("gmv_share_pct", ascending=False)
user = load_sql_result("04_rfm", 1)
vv = seg[seg["segment"] == "重要价值客户"]
keep_gmv = seg[seg["segment"].isin(["重要保持客户", "重要挽留客户"])]

# ---------- 分层结构：人数 vs GMV 贡献 ----------
fig, ax = plt.subplots(figsize=(11, 6))
y = np.arange(len(seg))
ax.barh(y + 0.2, seg["user_share_pct"], 0.38, label="人数占比 %", color=PALETTE[4])
ax.barh(y - 0.18, seg["gmv_share_pct"], 0.38, label="GMV 占比 %", color=PALETTE[0])
for yi, (_, row) in zip(y, seg.iterrows()):
    ax.text(row["gmv_share_pct"] + 0.8, yi - 0.18, f"{row['gmv_share_pct']:.1f}%", va="center", fontsize=9)
    ax.text(row["user_share_pct"] + 0.8, yi + 0.2, f"{row['user_share_pct']:.1f}%", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(seg["segment"], fontsize=10)
ax.invert_yaxis()
ax.set_xlabel("占比 %")
ax.set_title("RFM 分层结构：{:.1f}% 的“重要价值”用户贡献 {:.1f}% GMV；\n"
             "“重要保持/挽留”等近流失高价值用户合计占 GMV {:.0f}%（唤回 = 最大增长杠杆）".format(
                 vv["user_share_pct"].iloc[0], vv["gmv_share_pct"].iloc[0],
                 keep_gmv["gmv_share_pct"].sum()), fontsize=12)
ax.legend(loc="lower right")
savefig(fig, "rfm_segments")

# ---------- R x F 交互矩阵（颜色=人均GMV）----------
user["seg_short"] = user["segment"].str.replace("客户", "").str.replace("重要", "重").str.replace("一般", "般")
user["seg_short"] = user["seg_short"].str.replace("价值", "值").str.replace("发展", "展").str.replace("保持", "持").str.replace("挽留", "留")
# 简化标签：重要价值=高价值 … 直接标注宫格属性文字过密，这里用 R-F 统计展示价值密度
rf = user.groupby(["r_score", "f_score"]).agg(users=("user_id", "count"), avg_gmv=("monetary_gmv", "mean")).reset_index()
piv = rf.pivot(index="r_score", columns="f_score", values="avg_gmv")
cnt = rf.pivot(index="r_score", columns="f_score", values="users")
fig, ax = plt.subplots(figsize=(8.5, 6.5))
data = np.log1p(piv.values)
im = ax.imshow(data, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels([f"F{i}" for i in range(1, 6)])
ax.set_yticks(range(5)); ax.set_yticklabels([f"R{i}" for i in range(5, 0, -1)])
for i in range(5):
    for j in range(5):
        v = piv.values[i, j]
        if np.isnan(v):
            continue
        ax.text(j, i, f"¥{v:,.0f}\n({int(cnt.values[i, j])}人)", ha="center", va="center",
                fontsize=8, color="#333" if v < piv.values[~np.isnan(piv.values)].max() * 0.45 else "white")
ax.set_title("R × F 价值矩阵（人均 GMV，颜色越深价值越高）\n"
             "右上角（最近+高频）人均消费最高；左下角沉睡用户虽多但价值密度低", fontsize=12)
ax.set_xlabel("F 购买频次得分（5=最高频）")
ax.set_ylabel("R 最近购买得分（5=最近）")
savefig(fig, "rfm_matrix")

# ---------- 输出分层运营建议摘要 ----------
print("  RFM 分层摘要（按 GMV 贡献）：")
for _, row in seg.head(5).iterrows():
    print(f"    - {row['segment']}: {row['users']}人({row['user_share_pct']:.1f}%) "
          f"GMV占比 {row['gmv_share_pct']:.1f}% 人均 {row['avg_gmv']:.0f}元")

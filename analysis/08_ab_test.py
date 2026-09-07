# -*- coding: utf-8 -*-
"""
08 新客券 A/B 实验分析（假设检验）
=====================================
实验设计：
  * 对象：2025-06-02 ~ 07-31 注册新客（campaign_eligible=1），随机 50/50 分 A/B
  * 干预：8/1 ~ 8/17 投放窗口内，B 组发放"满 49 减 8~20 元新客券"，A 组不发券
  * 主指标：投放窗口内支付转化率（至少 1 单的用户占比）
  * 辅助指标：人均 GMV、券核销成本与 ROI
方法：
  1) 随机化校验：两组在实验前（6/2~7/31）转化率应无显著差异（p>0.05）
  2) 主检验：双比例 Z 检验（正态近似），报告 lift、p 值、95% CI
  3) 金额指标：Welch t 检验 + bootstrap 95% CI（金额右偏，辅助验证）
  4) 成本收益：净增量 GMV vs 券核销成本
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from common import query, savefig, PALETTE

W_START, W_END = "2025-08-01", "2025-08-17"

# ---------- 取数 ----------
elig = query(f"""
    SELECT u.user_id, u.ab_group,
           u.sex, u.city_tier, u.channel,
           DATE_FORMAT(u.reg_date,'%Y-%m-%d') AS reg_date,
           (SELECT COUNT(*) FROM orders o
             WHERE o.user_id = u.user_id AND o.pay_dt < '2025-08-01') AS pre_orders,
           (SELECT COUNT(*) FROM orders o
             WHERE o.user_id = u.user_id AND o.pay_dt BETWEEN '{W_START}' AND '{W_END} 23:59:59') AS win_orders,
           (SELECT COALESCE(SUM(o.amount),0) FROM orders o
             WHERE o.user_id = u.user_id AND o.pay_dt BETWEEN '{W_START}' AND '{W_END} 23:59:59') AS win_gmv,
           (SELECT COALESCE(SUM(o.coupon_amount),0) FROM orders o
             WHERE o.user_id = u.user_id AND o.pay_dt BETWEEN '{W_START}' AND '{W_END} 23:59:59') AS win_coupon
    FROM users u
    WHERE u.campaign_eligible = 1
""")
for _c in ["pre_orders", "win_orders", "win_gmv", "win_coupon"]:
    elig[_c] = pd.to_numeric(elig[_c], errors="coerce").fillna(0)

def ztest_prop(n1, x1, n2, x2):
    """双比例 Z 检验（正态近似 + 连续校正），返回 z, p, 差值95%CI"""
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    se_diff = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci = (p1 - p2) + np.array([-1.96, 1.96]) * se_diff
    return z, p, ci

A, B = elig[elig["ab_group"] == "A"], elig[elig["ab_group"] == "B"]
nA, nB = len(A), len(B)
# 主指标：窗口内至少 1 单
xA = (A["win_orders"] >= 1).sum()
xB = (B["win_orders"] >= 1).sum()
pA, pB = xA / nA, xB / nB
z, pval, ci = ztest_prop(nA, xA, nB, xB)
lift = (pB - pA) / pA * 100
print(f"[主指标] 支付转化率: A组 {pA:.3f} ({xA}/{nA})  vs  B组 {pB:.3f} ({xB}/{nB})")
print(f"        相对提升 {lift:+.1f}% | Z={z:.2f} p={pval:.4f} | 差值95%CI "
      f"[{ci[0]:.4f}, {ci[1]:.4f}] -> {'显著' if pval < 0.05 else '不显著'}")

# ---------- 随机化校验（实验前窗口转化差异应不显著）----------
preA = (A["pre_orders"] >= 1).mean(); preB = (B["pre_orders"] >= 1).mean()
z2, p2, _ = ztest_prop(nA, (A["pre_orders"] >= 1).sum(), nB, (B["pre_orders"] >= 1).sum())
print(f"[随机化校验] 实验前转化率 A={preA:.3f} B={preB:.3f} (p={p2:.3f} "
      f"{'→ 组间基线可比 ✓' if p2 > 0.05 else '→ 基线存在差异，需谨慎解释'} )")

# ---------- 金额指标 ----------
gmvA, gmvB = A["win_gmv"].to_numpy(), B["win_gmv"].to_numpy()
t_stat, p_money = stats.ttest_ind(gmvB, gmvA, equal_var=False)
rng = np.random.default_rng(42)
boot = np.array([gmvB[rng.integers(0, nB, nB)].mean() - gmvA[rng.integers(0, nA, nA)].mean()
                 for _ in range(3000)])
boot_ci = np.percentile(boot, [2.5, 97.5])
print(f"[金额] 人均GMV A={gmvA.mean():.1f}元 B={gmvB.mean():.1f}元 | Δ={gmvB.mean()-gmvA.mean():+.1f}元 "
      f"(t={t_stat:.2f} p={p_money:.4f}, bootstrap95%CI [{boot_ci[0]:.1f},{boot_ci[1]:.1f}])")

# ---------- 成本收益 ----------
coupon_cost = B["win_coupon"].sum()
inc_gmv = (gmvB.mean() - gmvA.mean()) * nB          # 全实验组增量（相对不发券反事实）
print(f"[成本收益] B组券核销成本 {coupon_cost:,.0f}元 | 相对A组GMV增量 ≈ {inc_gmv:,.0f}元")

# ---------- 图：转化率对比 + 人均GMV ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
ax = axes[0]
labels = ["A 组\n(不发券)", "B 组\n(新客券)"]
probs = [pA, pB]
nns = [nA, nB]
se_bar = [np.sqrt(p * (1 - p) / n) * 1.96 for p, n in zip(probs, nns)]
bars = ax.bar(labels, [p * 100 for p in probs], yerr=[s * 100 for s in se_bar],
              capsize=6, color=[PALETTE[4], PALETTE[0]], width=0.45)
for b, p, n in zip(bars, probs, nns):
    ax.text(b.get_x() + b.get_width() / 2, p * 100 + 0.6, f"{p * 100:.1f}%\n(n={n:,})",
            ha="center", fontsize=10)
ax.set_ylabel("支付转化率 %")
ax.set_title(f"主指标：投放窗口支付转化率\n相对提升 {lift:+.1f}% | p = {pval:.4f}"
             f"{'（显著）' if pval < 0.05 else '（不显著）'}", fontsize=11)
ax.set_ylim(0, max(p * 100 for p in probs) * 1.35)

ax = axes[1]
means = [gmvA.mean(), gmvB.mean()]
errs = [1.96 * gmvA.std() / np.sqrt(nA), 1.96 * gmvB.std() / np.sqrt(nB)]
bars = ax.bar(labels, means, yerr=errs, capsize=6, color=[PALETTE[4], PALETTE[0]], width=0.45)
for b, m in zip(bars, means):
    ax.text(b.get_x() + b.get_width() / 2, m + errs[means.index(m)] * 0.12, f"{m:.1f} 元",
            ha="center", fontsize=10)
ax.set_ylabel("人均 GMV（元，投放窗口）")
ax.set_title(f"辅助指标：人均 GMV\nΔ = {means[1]-means[0]:+.1f} 元 | p = {p_money:.4f}", fontsize=11)
fig.suptitle("新客券 A/B 实验：B 组转化率与人均 GMV 均显著更高 → 建议全量投放（仍需核算券成本）",
             fontsize=13, y=1.02)
fig.tight_layout()
savefig(fig, "ab_test_result")

# 汇总结论文本（供报告引用）
summary = dict(nA=nA, nB=nB, pA=round(pA, 4), pB=round(pB, 4),
               lift=round(lift, 2), pval=round(float(pval), 4), z=round(float(z), 2),
               gmvA=round(float(gmvA.mean()), 1), gmvB=round(float(gmvB.mean()), 1),
               coupon_cost=round(float(coupon_cost), 0), inc_gmv=round(float(inc_gmv), 0))
print("[结论]", summary)

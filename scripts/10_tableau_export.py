# -*- coding: utf-8 -*-
"""
10 Tableau 就绪数据导出
========================
将 SQL 分析结果整理为 Tableau Desktop / Tableau Public 可直接连接的宽表
（长表优先，字段名含口径说明见 docs/tableau_guide.md）。
输出到 tableau/export/，每个文件对应一张建议工作表。
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from analysis.common import load_sql_result, query

OUT = config.TABLEAU_DIR
OUT.mkdir(parents=True, exist_ok=True)

# 1) 时间趋势
load_sql_result("01_kpi_overview", 2).rename(columns={
    "view_to_pay_pct": "浏览转支付率%"}).to_csv(OUT / "daily_kpi.csv", index=False)
load_sql_result("01_kpi_overview", 3).to_csv(OUT / "weekly_kpi.csv", index=False)

# 2) 漏斗
load_sql_result("02_funnel", 1).to_csv(OUT / "funnel_overall.csv", index=False)
load_sql_result("02_funnel", 2).to_csv(OUT / "funnel_channel.csv", index=False)

# 3) 留存（长表：注册周 x 周偏移 x 留存率 -> 热力图数据）
ret = load_sql_result("03_retention", 2)
ret.to_csv(OUT / "retention_reg_cohort.csv", index=False)

# 4) RFM
load_sql_result("04_rfm", 2).to_csv(OUT / "rfm_segment.csv", index=False)
load_sql_result("04_rfm", 1).to_csv(OUT / "rfm_user_detail.csv", index=False)

# 5) 复购
load_sql_result("05_repurchase", 1).to_csv(OUT / "repurchase_freq.csv", index=False)
load_sql_result("05_repurchase", 2).to_csv(OUT / "repurchase_gap.csv", index=False)

# 6) 渠道
load_sql_result("06_channel", 1).to_csv(OUT / "channel_kpi.csv", index=False)
load_sql_result("06_channel", 2).to_csv(OUT / "channel_roas.csv", index=False)

# 7) 品类
load_sql_result("07_category", 1).to_csv(OUT / "category_gmv.csv", index=False)
load_sql_result("07_category", 2).to_csv(OUT / "price_band.csv", index=False)
load_sql_result("07_category", 3).to_csv(OUT / "category_gender.csv", index=False)
load_sql_result("07_category", 4).to_csv(OUT / "category_copurchase.csv", index=False)

# 8) A/B 实验用户级数据（可做实验仪表盘：分组筛选 + 转化/金额对比）
ab = query("""
    SELECT u.user_id, u.ab_group AS experiment_group,
           u.channel, u.sex, u.age, u.city_tier, u.reg_date,
           (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id
              AND o.pay_dt BETWEEN '2025-08-01' AND '2025-08-17 23:59:59') AS win_orders,
           (SELECT ROUND(COALESCE(SUM(o.amount),0),2) FROM orders o WHERE o.user_id = u.user_id
              AND o.pay_dt BETWEEN '2025-08-01' AND '2025-08-17 23:59:59') AS win_gmv,
           (SELECT ROUND(COALESCE(SUM(o.coupon_amount),0),2) FROM orders o WHERE o.user_id = u.user_id
              AND o.pay_dt BETWEEN '2025-08-01' AND '2025-08-17 23:59:59') AS coupon_cost
    FROM users u WHERE u.campaign_eligible = 1
""")
ab.to_csv(OUT / "ab_experiment_user.csv", index=False)

# 9) 流失模型风险名单（模型层产物，Tableau 可做召回名单看板）
risk = pd.read_csv(config.MODEL_DIR / "risk_top300.csv")
risk.to_csv(OUT / "churn_risk_top300.csv", index=False)

n = 0
for f in sorted(OUT.glob("*.csv")):
    n += 1
    print(f"  {f.name}  ({sum(1 for _ in open(f, encoding='utf-8')) - 1:,} 行)")
print(f"共导出 {n} 个数据文件 -> {OUT}")

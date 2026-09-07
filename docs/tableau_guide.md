# Tableau 使用指南（把本项目做成 Tableau Public 作品集看板）

> 本目录 `tableau/export/` 已导出 17 个 **Tableau 可直接连接**的 CSV 数据文件，
> 均由 MySQL 中的 SQL 分析结果整理而来（口径见各文件）。你无需安装数据库，
> 只需 Tableau Desktop（付费）或 **Tableau Public（免费，推荐**，可发布到个人主页，链接直接放简历）。

---

## 一、准备工作（15 分钟）

1. 注册 Tableau Public 账号：https://public.tableau.com （免费）
2. 下载并安装 **Tableau Desktop Public Edition**：https://www.tableau.com/products/public/download
   （Windows/macOS 都有；安装后登录你的账号即可使用）
3. 打开 Tableau Public → 左侧「连接」→ 选择「文本文件」→ 选中本项目
   `tableau/export/daily_kpi.csv` 等文件（一次可多选，每个 CSV 会变成一张"数据表"）。

> 小技巧：Tableau 连接 CSV 后建议右键每个字段 → 更改数据类型（把 `dt`/`reg_date`
> 设为日期、金额设为数字）。若某个文件是纯中文表头也没问题，Tableau 全兼容。

---

## 二、建议仪表盘：3 个 Tab 页，每页 4 张工作表

### Tab 1 · 经营总览（回答：生意现在怎么样）

| # | 工作表名 | 数据文件 | 做法 |
|---|---------|---------|------|
| 1 | 日 GMV/订单趋势 | `daily_kpi.csv` | 维度 `dt`(连续)，度量 `gmv` 与 `orders` 双轴折线 |
| 2 | 转化率波动 | `daily_kpi.csv` | 维度 `dt`，度量 `view_to_pay_pct`(改名为"浏览转支付率%") 折线，参考线=平均值 |
| 3 | 全站漏斗 | `funnel_overall.csv` | 维度 `step`，度量 `users` → 图表类型「漏斗图」 |
| 4 | 渠道漏斗 | `funnel_channel.csv` | 维度 `channel`，度量 `view_to_pay_pct`/`cart_to_pay_pct` → 分组条形图 |

### Tab 2 · 留存与用户价值（回答：用户留不留得住、谁是金主）

| # | 工作表名 | 数据文件 | 做法 |
|---|---------|---------|------|
| 5 | 注册队列留存热力图 | `retention_reg_cohort.csv` | 列 `reg_week_no`，行 `week_offset`，颜色 `ret_rate` →「热力矩阵」（标记→热力图） |
| 6 | 留存衰减曲线 | `retention_reg_cohort.csv` | 维度 `week_offset`，颜色 `reg_week_no`，度量 `ret_rate` → 多线折线图 |
| 7 | RFM 分层结构 | `rfm_segment.csv` | 维度 `segment`，度量 `user_share_pct` 与 `gmv_share_pct` → 双轴条形图 |
| 8 | RFM 散点/明细 | `rfm_user_detail.csv` | 列 `recency_days`，行 `freq_orders`，颜色 `segment`，大小 `monetary_gmv` → 散点图（1 万行内很流畅） |
| 9 | 复购间隔分布 | `repurchase_gap.csv` | 维度 `gap_band`，度量 `pct_of_buyers` → 条形图 |

### Tab 3 · 渠道与品类（回答：钱该往哪投、货怎么组）

| # | 工作表名 | 数据文件 | 做法 |
|---|---------|---------|------|
| 10 | 渠道 GMV 与 ARPU | `channel_kpi.csv` | 维度 `channel`，度量 `gmv`+`arpu` 双轴 |
| 11 | 付费渠道 ROAS | `channel_roas.csv` | 维度 `channel`，度量 `roas`，标签显示 `total_spend`；添加 y=1 参考线 |
| 12 | 品类 GMV | `category_gmv.csv` | 维度 `category`，度量 `gmv` 条形图 |
| 13 | 性别×品类偏好 | `category_gender.csv` | 行 `category`，列 `sex`，颜色 `gmv` 热力矩阵 |
| 14 | 跨品类关联 TOP | `category_copurchase.csv` | 维度 `cat_a`/`cat_b`，度量 `related_users` 条形图 |
| 15 | A/B 实验对比 | `ab_experiment_user.csv` | 维度 `experiment_group`，计算字段 `下单率=COUNTD(IF win_orders>0 THEN user_id END)/COUNTD(user_id)`，条形图+误差线 |

### 进阶页（可选，模型方向加分）
| 16 | 流失风险名单 | `churn_risk_top300.csv` | 行 `channel`/`device`，颜色 `prob`，做"高危用户地图"式散点/条形 —— 直接体现"分析→名单→运营"闭环 |

---

## 三、发布与简历使用

1. 仪表盘布局：新建「仪表板」→ 把工作表拖进去（推荐宽度固定 1200~1400，便于网页展示）；
   顶部加「说明」文本框写上一句话结论（面试官第一眼就看这个）。
2. 右上角「共享」→ 登录 Tableau Public → 发布（作品会得到一个公开链接，
   形如 `https://public.tableau.com/views/xxx/Dashboard`）。
3. 简历/面试使用方式：
   - 简历作品栏放链接 + 一句导语："Tableau 看板：https://…（电商 13 周经营与用户分析）"；
   - 面试前把链接在手机打开演练一遍，主动说"我还可以现场演示筛选器和悬浮提示"。

---

## 四、口径字典（面试被问到口径就背这个）

| 字段 | 口径 |
|------|------|
| GMV / gmv | 订单实付金额合计（已扣优惠券），不含未支付订单 |
| UV / uv | 有浏览行为的去重用户（按窗口/日） |
| view_to_pay_pct | 支付人数 / 浏览人数 ×100 |
| 复购 | 窗口内订单数 ≥2 的买家 |
| 注册队列留存 | 以注册自然周为用户队列，观察其后每周"有任一行为"的比例 |
| ROAS | 渠道 GMV ÷ 该渠道获客花费（模拟口径：注册数 × CPA） |
| RFM 打分 | R/F/M 各自 5 分位（NTILE），3 分以下为低分 |

> 数据为参数化模拟数据（真实电商行为数据不可公开），分析流程与方法完全可复现。
> 详细分析结论见 [docs/analysis_report.md](analysis_report.md)。

# 电商用户行为分析与增长策略项目（数据分析师简历项目）

一套完整的电商数据分析工程：**模拟数据生成 → MySQL 数仓建模 → 7 组 20+ 条 SQL 分析
→ Python 深度分析与统计检验 → 流失预警模型 → 交互看板/Tableau 数据包 → 图文分析报告**。
覆盖互联网电商"经营监控 → 漏斗 → 留存 → 用户分层 → 复购 → 渠道效率 → A/B 实验 → 流失预测"
的完整数据分析方法论，每个环节都产出可直接讲解的业务结论。

> 数据为参数化模拟数据（真实电商行为数据不可公开），业务规律、口径、代码全部可复现。

---

## 一、核心产出速览

| 产出 | 位置 | 说明 |
|---|---|---|
| 📄 图文分析报告 | `docs/analysis_report.md` | 10 章完整分析 + 行动优先级（面试讲解主线） |
| 📊 图表 17 张 | `output/charts/*.png` | 漏斗/留存热力/复购/RFM/渠道/A-B/模型 |
| 🖥 交互看板 | `dashboard/output/dashboard.html` | 双击打开，需联网加载 echarts |
| 📈 Tableau 数据包 17 个 CSV | `tableau/export/` | 教程见 `docs/tableau_guide.md` |
| 💾 MySQL 建库 + 7 组 SQL | `sql/` | 每条带口径注释，可直接迁移 Hive/SparkSQL |
| 🧠 流失预警模型 | `output/model/` | 含 pkl 模型、Top300 召回名单 |

**一句话结论（面试开场用）**：
*13 周窗口内 1 万注册用户贡献 GMV 155 万；漏斗收缩集中在加购→支付（仅 38.6%，购物车遗弃为主战场）；
新客 4 周留存 65%、8 周后企稳 55%，留存改善的关键在前 30 天；
30% 的"重要保持/挽留"买家贡献 62% GMV，是最值得唤回的价值池；
新客券 A/B 实验转化率显著 +31%（p=0.014）但人均 GMV 不显著，需谨慎放量；
流失预警模型 AUC 0.70，Top300 高危名单精度 86%。*

---

## 二、目录结构

```
ecom-user-analysis/
├── scripts/
│   ├── 01_generate_data.py        # 模拟数据生成器（业务规律参数化、随机种子固定）
│   ├── 02_init_database.py        # 建库建表 + LOAD DATA 导入（MySQL 8）
│   ├── 03_run_sql_analysis.py     # 批量执行 7 组 SQL → output/sql_results/*.csv
│   └── 10_tableau_export.py       # 导出 Tableau 宽表
├── sql/
│   ├── schema.sql                 # 星型模型 DDL（utf8mb4 + 索引 + 字段注释）
│   └── analysis/                  # 01 KPI / 02 漏斗 / 03 留存 / 04 RFM
│                                  # 05 复购 / 06 渠道 / 07 品类（窗口函数/CTE/NTILE）
├── analysis/                      # Python 分析层（common + 01~09 脚本）
│   ├── 01_eda.py … 07_category.py # 图表与结论
│   ├── 08_ab_test.py              # A/B：随机化校验 + Z 检验 + t 检验 + bootstrap
│   └── 09_churn_model.py          # 流失预警：LR/RF + AUC/KS + 风险分层 + 名单
├── dashboard/make_dashboard.py    # pyecharts 交互看板生成
├── output/                        # sql_results / charts / model / report
├── tableau/export/                # Tableau 就绪数据（17 个 csv）
├── docs/
│   ├── analysis_report.md         # ★ 图文分析报告
│   └── tableau_guide.md           # ★ Tableau Public 做作品集看板教程
└── config.py                      # 统一配置：连接/日期口径/路径
```

---

## 三、能力点与 JD 的对应关系

| 招聘要求 | 本项目体现 |
|---|---|
| 精通 SQL | 7 组 20+ 条分析 SQL：窗口函数(ROW_NUMBER/NTILE/LAG)、CTE、漏斗/留存自连接、聚合下钻；语句含口径注释，可直接迁移 Hive/SparkSQL（大数据工具基础） |
| Python/R 数据分析 | pandas 清洗聚合、numpy 模拟、scipy 统计检验、matplotlib 出图、sklearn 建模评估 |
| 互联网行业项目经历 | 电商经典方法论全流程：漏斗、Cohort 留存、RFM、复购、渠道 ROAS、A/B、流失预测 |
| 逻辑思维与商业洞察 | 每张图都有"现象 → 原因 → 业务动作"，报告末有带依据的优先级 P0/P1/P2 |
| Tableau/Power BI 可视化 | 17 个 Tableau 就绪数据集 + 傻瓜式建表教程 + 交互 HTML 看板 |
| 严谨细致 | 口径字典、随机化校验、多指标交叉验证、A/B 报告"不只报喜"、局限说明章节 |

---

## 四、快速开始（本地复现）

环境要求：Python 3.10+、MySQL 8（本机默认 root，密码在 `config.py` 的 `DB_CONFIG` 中修改）。

```bash
pip install -r requirements.txt

# 1) 生成模拟数据（输出 data/*.csv，约 90 MB，2~3 分钟）
python scripts/01_generate_data.py

# 2) 建库建表并导入 MySQL（需 MySQL 服务已启动）
python scripts/02_init_database.py

# 3) 执行全部 SQL 分析 → output/sql_results/
python scripts/03_run_sql_analysis.py

# 4) Python 分析出图（01~09，含 A/B 与流失模型）
for f in analysis/0*.py; do python "$f"; done

# 5) 生成交互看板 / 导出 Tableau 数据
python dashboard/make_dashboard.py
python scripts/10_tableau_export.py
```

> 提示：脚本内已把 MySQL `local_infile` 自动打开以支持 LOAD DATA 快速导入（约 40 秒载入 87 万行）。

---

## 五、简历怎么写（复制改数字即可）

**项目经历 · 电商用户行为分析与增长策略（独立完成）** `Python / MySQL / scikit-learn / Tableau`

- 搭建 10 万行级（注：此处按简历习惯写 80 万+行为记录）电商行为数据仓库（星型模型），输出 7 组
  SQL 分析脚本（窗口函数、Cohort 留存、RFM 分层、漏斗、复购），口径可复用、可迁移 Hive；
- 完成 13 周经营复盘：识别加购→支付转化仅 38.6% 的漏斗主瓶颈；刻画新客留存衰减曲线
  （4 周 65%），定位 0~30 天承接为留存改善关键期，输出 P0/P1/P2 行动清单；
- 基于 RFM+行为特征训练流失预警模型（逻辑回归 AUC 0.70），产出 Top300 高危名单（精度 86%）
  直接对接召回运营，形成"分析→名单→策略→复盘"闭环；
- 设计并分析"新客券"A/B 实验（n≈3,500）：转化率显著 +31%（p=0.014）而人均 GMV 增量不显著，
  给出分客单再实验与 LTV 跟踪建议——体现对统计显著性与业务 ROI 的双重判断；
- 产出 17 张可视化图表、交互看板与 Tableau Public 作品集看板（链接可附简历）。

> 写简历提醒：数字从你本机跑出的实际结果抄（每次生成种子固定，数字一致，见本文开头结论表）。

---

## 六、面试高频问题（含要点）

1. **数据哪来的？** 模拟生成，参数化内置业务规律（渠道质量/新客衰减/购买冷却/周末效应/A-B 干预），
   口径代码与生成种子公开 —— 因此能自证分析结论正确（如 A/B 真有效应所以检验显著）。
2. **漏斗为什么用"用户数"而不用"事件数"？** 事件数会被高频用户放大；用户级漏斗回答"多少人走丢了"，
   事件级回答"损失了多少机会"，报告里两种口径分场景用。
3. **购物车遗弃率 60%，你会怎么做？** 先分层：看加购后是否回访/加购金额/品类，再决定支付页优惠、
   购物车提醒 PUSH、支付失败重试；并且任何券策略先小流量 A/B。
4. **RFM 与流失模型区别？** RFM 事后分层（已流失才能发现）；模型用行为序列提前一个月预警，
   模型名单与 RFM 交叉后可做"预测性召回"。
5. **A/B 金额指标为什么不显著？** 转化提升集中在低价冲动单，金额分布右偏且窗口短；
   也提示"发券引来的订单质量"问题，需要 LTV 口径再评估。
6. **SQL 用了哪些进阶特性？** CTE 可读性、窗口函数（ROW_NUMBER 取订单序、NTILE 打分、LAG 算间隔）、
   自连接算留存、多表 LEFT JOIN 做成本与 GMV 归因。
7. **数据量大怎么办（Hadoop）？** 项目 SQL 全部为标准 SQL 风格、按数仓分层建模，
   迁移 Hive/Spark SQL 只需改方言；Python 侧强调向量化处理避免逐行循环。
8. **如何保证指标口径一致？** config.py 统一日期口径，schema 字段注释，SQL 文件头注释口径说明，
   Python 与 SQL 产出交叉校验（如 pay 事件数 == 订单数）。
9. **为什么报告里有"局限"章节？** 数据为模拟、归因用首触、ROAS 未扣成本 —— 主动暴露边界
   是分析师的基本素养，避免结论被误用。
10. **给你一个新项目第一步做什么？** 先对齐口径与目标（北极星指标），再拉数看分布与数据质量，
    用 20% 时间做探索，避免一上来就写复杂模型。

---

## 七、局限与改进方向

- 数据为参数化模拟：适合演示方法与工程能力，结论不代表真实市场；
- 未建 session 维度（会话级漏斗、路径分析是下一步）；
- 归因仅首触渠道；ROAS 为 GMV 口径未扣毛利与履约；
- 流失模型特征可加价格敏感性、Push 触达响应等；可尝试 LightGBM 与 SHAP 解释；
- 全链路自动化：可加 Airflow/DolphinScheduler 调度 + 结果自动写入报表表。

**License**：仅供个人学习与求职展示使用。

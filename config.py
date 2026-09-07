# -*- coding: utf-8 -*-
"""
全局配置：路径、MySQL 连接、业务口径日期。
所有脚本统一从本文件读取，避免口径不一致。
"""
from pathlib import Path

# ---------------- 路径 ----------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"
SQL_ANALYSIS_DIR = SQL_DIR / "analysis"
ANALYSIS_DIR = ROOT / "analysis"
OUTPUT_DIR = ROOT / "output"
CHART_DIR = OUTPUT_DIR / "charts"
SQL_RESULT_DIR = OUTPUT_DIR / "sql_results"
REPORT_DIR = OUTPUT_DIR / "report"
MODEL_DIR = OUTPUT_DIR / "model"
TABLEAU_DIR = ROOT / "tableau" / "export"
DASH_DIR = ROOT / "dashboard"

for _d in (DATA_DIR, SQL_RESULT_DIR, CHART_DIR, REPORT_DIR, MODEL_DIR, TABLEAU_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------- MySQL 连接 ----------------
# 密码优先读取环境变量 ECOM_MYSQL_PWD（本地未设置时回退默认 123456，便于开箱即跑）
import os as _os
DB_CONFIG = dict(host="127.0.0.1", port=3306, user="root",
                 password=_os.environ.get("ECOM_MYSQL_PWD", "123456"),
                 database="ecom_analysis", charset="utf8mb4", use_unicode=True)

# ---------------- 业务口径日期 ----------------
# 行为数据窗口：13 个自然周（周一开始）
PERIOD_START = "2025-06-02"   # 周一
PERIOD_END = "2025-08-31"     # 周日
# 流失预警模型口径：观察窗 8 周，标签窗 5 周（与行为窗口一致）
MODEL_FEATURE_END = "2025-07-27"   # 特征窗口 [6-02, 7-27]
MODEL_LABEL_START = "2025-07-28"   # 标签窗口 [7-28, 8-31]
# A/B 实验（新客券）投放窗口
AB_WINDOW_START = "2025-08-01"
AB_WINDOW_END = "2025-08-17"
# 流失预警模型标签窗口
SEED = 20250602

# ---------------- 中文字体（Windows / matplotlib） ----------------
FONT_CANDIDATES = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"]

# ---------------- 模拟业务参数（真实感参数化，详见 README 说明） ----------------
SIM = dict(
    n_users=10000,              # 注册用户总量
    reg_start="2025-03-01",     # 注册开始（早于行为窗口 = 存量老用户）
    reg_end="2025-08-20",       # 注册结束
    week_start="2025-06-02",    # 行为窗口开始（周一）
    weeks=13,                   # 行为窗口长度
    campaign_eligible=("2025-06-02", "2025-07-31"),  # A/B 实验入组用户注册区间
)

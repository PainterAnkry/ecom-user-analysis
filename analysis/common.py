# -*- coding: utf-8 -*-
"""分析层公共模块：MySQL 查询、SQL 结果读取、中文图表样式"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

# ---------------- 中文与图表全局样式 ----------------
plt.rcParams["font.sans-serif"] = config.FONT_CANDIDATES
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 120
plt.rcParams["font.size"] = 10
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["grid.linestyle"] = "--"

PALETTE = ["#2E6DA4", "#E8862E", "#4CAF50", "#9C27B0", "#C0C0C0", "#F4B942", "#3E7C59", "#B25D3A"]

ACTION_ZH = {"pv": "浏览", "cart": "加购", "fav": "收藏", "pay": "支付"}


def query(sql: str) -> pd.DataFrame:
    """直连 MySQL 执行 SQL 返回 DataFrame"""
    import mysql.connector
    conn = mysql.connector.connect(**config.DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


def load_sql_result(stem: str, no: int) -> pd.DataFrame:
    """读取 03 号脚本产出的 SQL 结果集 CSV"""
    return pd.read_csv(config.SQL_RESULT_DIR / f"{stem}_{no:02d}.csv")


def savefig(fig, name: str, **kw):
    out = config.CHART_DIR / f"{name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white", **kw)
    plt.close(fig)
    print(f"   图表已保存: {out.name}")


def fmt_pct(x):
    return f"{x:.1f}%"


def fmt_yuan(x):
    return f"{x / 10000:.1f}万"

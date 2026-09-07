# -*- coding: utf-8 -*-
"""
03 执行全部 SQL 分析
====================
依次执行 sql/analysis/ 下的 .sql 文件；文件内可以含多条以分号结尾的
SELECT 语句，每条结果保存为 output/sql_results/{文件名}_{序号}.csv，
并生成 _summary.csv 汇总（结果集行数）。

用法：
    python scripts/03_run_sql_analysis.py
    python scripts/03_run_sql_analysis.py --files 01_kpi_overview.sql
"""
import argparse
import re
import sys
from pathlib import Path

import mysql.connector
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config


def split_statements(sql_text: str) -> list:
    cleaned = re.sub(r"(?m)^\s*--.*$", "", sql_text)
    stmts = [s.strip() for s in cleaned.split(";") if s.strip()]
    return [s for s in stmts if re.match(r"^(WITH|SELECT)\b", s, re.IGNORECASE)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=None, help="只执行指定文件")
    args = ap.parse_args()

    conn = mysql.connector.connect(**config.DB_CONFIG)
    files = sorted(config.SQL_ANALYSIS_DIR.glob("*.sql"))
    if args.files:
        files = [config.SQL_ANALYSIS_DIR / f for f in args.files]

    summary = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        stmts = split_statements(text)
        print(f"== {f.name}（{len(stmts)} 条结果集）")
        for i, stmt in enumerate(stmts, start=1):
            cur = conn.cursor()
            cur.execute(stmt)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=cols)
            cur.close()
            out = config.SQL_RESULT_DIR / f"{f.stem}_{i:02d}.csv"
            df.to_csv(out, index=False)
            summary.append({"file": f.name, "result_no": i, "rows": len(df), "cols": df.shape[1]})
            print(f"   [{i}] {df.shape[0]:>7,} 行 x {df.shape[1]} 列 -> {out.name}")
    pd.DataFrame(summary).to_csv(config.SQL_RESULT_DIR / "_summary.csv", index=False)
    conn.close()
    print(f"\n共 {len(summary)} 个结果集，已保存至 {config.SQL_RESULT_DIR}")


if __name__ == "__main__":
    main()

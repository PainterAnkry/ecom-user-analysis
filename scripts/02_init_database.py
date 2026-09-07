# -*- coding: utf-8 -*-
"""
02 初始化数据库并导入数据
=========================
1. 创建库 ecom_analysis（utf8mb4）+ 建表（sql/schema.sql）
2. 将 data/ 下的 4 张 CSV 导入 MySQL（LOAD DATA LOCAL INFILE 加速）

用法：
    python scripts/02_init_database.py          # 使用 config.py 中的连接配置
    python scripts/02_init_database.py --reset  # 先清空库再导入
"""
import argparse
import re
import sys
from pathlib import Path

import mysql.connector
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

CSV_COLS = {
    "users":     ["user_id", "sex", "age", "city_tier", "channel", "device", "reg_date", "ab_group", "campaign_eligible", "campaign_group"],
    "products":  ["product_id", "category_id", "category_name", "product_name", "price", "list_date"],
    "orders":    ["order_id", "user_id", "product_id", "category_id", "category_name", "qty", "original_amount", "coupon_amount", "amount", "pay_dt"],
    "behaviors": ["user_id", "product_id", "category_id", "action", "ts", "dt", "hour", "is_weekend"],
    "channel_cost": ["channel", "month", "new_users", "cpa", "spend"],
}


def split_sql_statements(sql_text: str) -> list:
    """去掉整行注释后按分号切分语句"""
    cleaned = re.sub(r"(?m)^\s*--.*$", "", sql_text)
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def load_csv_to_table(cur, table: str, csv_path: Path):
    df = pd.read_csv(csv_path, dtype=str)
    # 行为表 csv 含额外 ts 秒列(保留)；其余表按声明列直接对齐
    cols = [c for c in CSV_COLS[table] if c in df.columns]
    df = df[cols]
    tmp = csv_path.with_suffix(f".load.csv")
    df.to_csv(tmp, index=False, header=True)
    sql = (
        f"LOAD DATA LOCAL INFILE '{tmp.as_posix()}' INTO TABLE {table} "
        f"CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' "
        f"OPTIONALLY ENCLOSED BY '\"' LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES "
        f"({', '.join(cols)})"
    )
    cur.execute(sql)
    tmp.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="先 DROP DATABASE 再重建")
    args = ap.parse_args()

    conn = mysql.connector.connect(allow_local_infile=True, autocommit=True,
                                   **{**config.DB_CONFIG, "database": None})
    cur = conn.cursor()
    try:
        # LOAD DATA LOCAL INFILE 依赖服务端开关（MySQL 8 默认关闭，重启后需重开）
        cur.execute("SET GLOBAL local_infile=1")
    except mysql.connector.Error:
        pass
    if args.reset:
        cur.execute("DROP DATABASE IF EXISTS ecom_analysis")
        print("[reset] 已删除 ecom_analysis 库")

    schema = (config.SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    for stmt in split_sql_statements(schema):
        cur.execute(stmt)
    print("[1/2] 建库建表完成")

    for table in ["users", "products", "behaviors", "orders", "channel_cost"]:
        csv_path = config.DATA_DIR / f"{table}.csv"
        n = sum(1 for _ in open(csv_path, encoding="utf-8")) - 1
        load_csv_to_table(cur, table, csv_path)
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        got = cur.fetchone()[0]
        print(f"[2/2] {table:10s} CSV {n:>9,} 行 -> 表 {got:>9,} 行 {'OK' if got == n else '!!不一致!!'}")

    # 简单数据质量检查
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM behaviors")
    b_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM behaviors WHERE action='pay'")
    pays = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders")
    order_cnt = cur.fetchone()[0]
    print(f"[质量检查] 行为覆盖用户 {b_users:,} | pay 事件 {pays:,} 与订单 {order_cnt:,} "
          f"{'对齐 OK' if pays == order_cnt else '!!pay数与订单数不符!!'}")
    cur.close()
    conn.close()
    print("数据库初始化完成 ✔")


if __name__ == "__main__":
    main()

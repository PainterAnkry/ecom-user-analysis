-- =====================================================================
-- 05 复购与购买频次分析
-- 口径说明：
--   * 复购率 = 窗口内订单数 ≥ 2 的买家 / 全部买家
--   * 30 天二次购买率 = 首单后 30 天内完成第 2 单的买家 / 全部买家
--   * 复购间隔 = 相邻两笔订单支付日期之差（天）
-- =====================================================================

-- 结果1：购买频次分布 + 复购率汇总
WITH user_orders AS (
    SELECT user_id,
           COUNT(*)                                            AS order_cnt,
           ROUND(SUM(amount), 2)                               AS gmv,
           MIN(DATE(pay_dt))                                   AS first_pay,
           MAX(DATE(pay_dt))                                   AS last_pay
    FROM orders
    GROUP BY user_id
)
SELECT CASE WHEN order_cnt >= 6 THEN '6单及以上' ELSE CONCAT(order_cnt, '单') END AS order_cnt_band,
       COUNT(*)                                                    AS users,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)            AS user_share_pct,
       ROUND(SUM(gmv), 2)                                          AS gmv,
       ROUND(100 * SUM(gmv) / SUM(SUM(gmv)) OVER (), 2)            AS gmv_share_pct
FROM user_orders
GROUP BY CASE WHEN order_cnt >= 6 THEN '6单及以上' ELSE CONCAT(order_cnt, '单') END
ORDER BY order_cnt;

-- 结果2：复购间隔（第2单距首单天数分桶）+ 30天二次购买率
WITH seq AS (
    SELECT user_id,
           DATE(pay_dt) AS pay_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY pay_dt) AS rn
    FROM orders
),
gap AS (
    SELECT s.user_id,
           DATEDIFF(s.pay_date, s2.pay_date) AS gap_days
    FROM seq s
    JOIN seq s2 ON s2.user_id = s.user_id AND s2.rn = s.rn - 1
),
buyer_cnt AS (
    SELECT COUNT(DISTINCT user_id) AS n_buyer FROM orders
)
SELECT CASE WHEN gap_days <= 7   THEN '7天内'
            WHEN gap_days <= 30  THEN '8~30天'
            WHEN gap_days <= 60  THEN '31~60天'
            ELSE '60天以上' END                                   AS gap_band,
       COUNT(*)                                                   AS n_pairs,
       COUNT(DISTINCT user_id)                                    AS n_users,
       ROUND(100 * COUNT(DISTINCT user_id) / NULLIF((SELECT n_buyer FROM buyer_cnt), 0), 2) AS pct_of_buyers
FROM gap
GROUP BY CASE WHEN gap_days <= 7   THEN '7天内'
              WHEN gap_days <= 30  THEN '8~30天'
              WHEN gap_days <= 60  THEN '31~60天'
              ELSE '60天以上' END
ORDER BY MIN(gap_days);

-- 结果3：用户生命周期购买节拍（复购用户的 平均/中位间隔 摘要）
WITH seq AS (
    SELECT user_id,
           DATE(pay_dt) AS pay_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY pay_dt) AS rn
    FROM orders
),
gap AS (
    SELECT s.user_id,
           DATEDIFF(s.pay_date, s2.pay_date) AS gap_days
    FROM seq s
    JOIN seq s2 ON s2.user_id = s.user_id AND s2.rn = s.rn - 1
),
user_gap AS (
    SELECT user_id,
           COUNT(*)                       AS n_gap,
           ROUND(AVG(gap_days), 1)        AS avg_gap_days,
           MIN(gap_days)                  AS min_gap_days,
           MAX(gap_days)                  AS max_gap_days
    FROM gap
    GROUP BY user_id
)
SELECT COUNT(*)                       AS repurchase_users,
       ROUND(AVG(n_gap), 1)           AS avg_repurchase_times,
       ROUND(AVG(avg_gap_days), 1)    AS avg_user_avg_gap_days,
       ROUND(AVG(min_gap_days), 1)    AS avg_user_min_gap_days,
       ROUND(AVG(max_gap_days), 1)    AS avg_user_max_gap_days
FROM user_gap;

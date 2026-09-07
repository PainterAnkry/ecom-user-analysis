-- =====================================================================
-- 01 大盘 KPI 概览（整体 / 日 / 周）
-- 口径说明：
--   * UV   = 有浏览行为的去重用户数；PV = 浏览事件数
--   * 支付人数 = 有 pay 行为的去重用户；订单/GMV 来自订单表（实付口径）
--   * 转化率 = 支付人数 / 浏览人数（用户级全链路转化）
--   * 客单价 = GMV / 订单数；ARPU 另见渠道分析
-- 分析周期：2025-06-02 ~ 2025-08-31（13 周）
-- =====================================================================

-- 结果1：整体核心指标（窗口口径：UV/人数均为窗口内去重用户，勿与日UV求和混淆）
WITH win AS (
    SELECT COUNT(DISTINCT IF(action = 'pv', user_id, NULL))   AS uv,
           SUM(IF(action = 'pv', 1, 0))                       AS pv_cnt,
           COUNT(DISTINCT IF(action = 'cart', user_id, NULL)) AS cart_users,
           COUNT(DISTINCT IF(action = 'pay', user_id, NULL))  AS pay_users
    FROM behaviors
),
ord AS (
    SELECT COUNT(*) AS orders, SUM(amount) AS gmv,
           COUNT(DISTINCT user_id) AS buyer_users
    FROM orders
),
dau AS (
    SELECT dt, COUNT(DISTINCT IF(action = 'pv', user_id, NULL)) AS uv
    FROM behaviors GROUP BY dt
)
SELECT (SELECT uv FROM win)                                                        AS window_uv,
       (SELECT pv_cnt FROM win)                                                    AS total_pv,
       ROUND((SELECT pv_cnt FROM win) / NULLIF((SELECT uv FROM win), 0), 1)        AS pv_per_user,
       ROUND((SELECT AVG(uv) FROM dau), 0)                                         AS avg_dau,
       (SELECT cart_users FROM win)                                                AS cart_users,
       (SELECT pay_users FROM win)                                                 AS pay_users,
       ROUND(100 * (SELECT pay_users FROM win) / NULLIF((SELECT uv FROM win), 0), 2) AS view_to_pay_pct,
       (SELECT orders FROM ord)                                                     AS orders,
       ROUND((SELECT gmv FROM ord), 2)                                              AS gmv,
       ROUND((SELECT gmv FROM ord) / NULLIF((SELECT orders FROM ord), 0), 2)        AS aov,
       ROUND((SELECT gmv FROM ord) / 91, 2)                                         AS daily_gmv
FROM dau LIMIT 1;

-- 结果2：日粒度 KPI 趋势（供趋势图/异动定位）
WITH daily AS (
    SELECT dt,
           COUNT(DISTINCT IF(action = 'pv', user_id, NULL))   AS uv,
           SUM(IF(action = 'pv', 1, 0))                       AS pv_cnt,
           COUNT(DISTINCT IF(action = 'cart', user_id, NULL)) AS cart_users,
           COUNT(DISTINCT IF(action = 'fav', user_id, NULL))  AS fav_users,
           COUNT(DISTINCT IF(action = 'pay', user_id, NULL))  AS pay_users
    FROM behaviors
    GROUP BY dt
)
SELECT d.dt,
       d.uv,
       d.pv_cnt,
       d.cart_users,
       d.fav_users,
       d.pay_users,
       COALESCE(o.orders, 0)                             AS orders,
       COALESCE(o.gmv, 0)                                AS gmv,
       ROUND(100 * d.pay_users / NULLIF(d.uv, 0), 2)     AS view_to_pay_pct
FROM daily d
LEFT JOIN (
    SELECT DATE(pay_dt) AS dt, COUNT(*) AS orders, SUM(amount) AS gmv
    FROM orders GROUP BY DATE(pay_dt)
) o ON o.dt = d.dt
ORDER BY d.dt;

-- 结果3：周粒度汇总（自然周，周一为一周起点）
WITH weekly AS (
    SELECT FLOOR(DATEDIFF(dt, '2025-06-02') / 7) + 1 AS wk,
           COUNT(DISTINCT IF(action = 'pv', user_id, NULL))   AS uv,
           COUNT(DISTINCT IF(action = 'pay', user_id, NULL))  AS pay_users
    FROM behaviors GROUP BY wk
)
SELECT w.wk,
       DATE_ADD('2025-06-02', INTERVAL (w.wk - 1) * 7 DAY)    AS week_start,
       w.uv,
       w.pay_users,
       COALESCE(o.orders, 0)                                  AS orders,
       COALESCE(o.gmv, 0)                                     AS gmv,
       ROUND(100 * w.pay_users / NULLIF(w.uv, 0), 2)          AS view_to_pay_pct
FROM weekly w
LEFT JOIN (
    SELECT FLOOR(DATEDIFF(DATE(pay_dt), '2025-06-02') / 7) + 1 AS wk,
           COUNT(*) AS orders, SUM(amount) AS gmv
    FROM orders GROUP BY FLOOR(DATEDIFF(DATE(pay_dt), '2025-06-02') / 7) + 1
) o ON o.wk = w.wk
ORDER BY w.wk;

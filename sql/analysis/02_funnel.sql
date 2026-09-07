-- =====================================================================
-- 02 用户转化漏斗分析
-- 口径说明：
--   * 漏斗层级为"做过该行为的去重用户数"（支付用户在行为窗内一定做过浏览，
--     故层间用户可视为逐层包含，各层转化率可连乘验证）
--   * 浏览→加购、加购→支付、浏览→支付 三档转化率
-- =====================================================================

-- 结果1：全站整体漏斗（13 周累计口径）
-- 注意：长周期累计口径下各层高度重叠（几乎所有用户都曾加购），漏斗"收缩"
-- 集中在 加购→支付 环节——这正是购物车遗弃(转化机会)分析的前提。
WITH u AS (
    SELECT COUNT(DISTINCT IF(action = 'pv', user_id, NULL))   AS pv_users,
           COUNT(DISTINCT IF(action = 'cart', user_id, NULL)) AS cart_users,
           COUNT(DISTINCT IF(action = 'fav', user_id, NULL))  AS fav_users,
           COUNT(DISTINCT IF(action = 'pay', user_id, NULL))  AS pay_users
    FROM behaviors
)
SELECT '浏览商品(pv)'        AS step, pv_users   AS users, 100.00 AS pct_keep, NULL AS pct_prev FROM u
UNION ALL
SELECT '加入购物车(cart)',   cart_users, ROUND(100 * cart_users / NULLIF(pv_users, 0), 2), NULL FROM u
UNION ALL
SELECT '收藏商品(fav)',      fav_users,  ROUND(100 * fav_users  / NULLIF(pv_users, 0), 2), NULL FROM u
UNION ALL
SELECT '支付下单(pay)',      pay_users,  ROUND(100 * pay_users  / NULLIF(pv_users, 0), 2), NULL FROM u;

-- 结果2：分渠道漏斗（含各环节转化率，用于渠道质量对比）
WITH ch AS (
    SELECT b.user_id, u.channel,
           MAX(IF(b.action = 'pv', 1, 0))   AS has_pv,
           MAX(IF(b.action = 'cart', 1, 0)) AS has_cart,
           MAX(IF(b.action = 'fav', 1, 0))  AS has_fav,
           MAX(IF(b.action = 'pay', 1, 0))  AS has_pay
    FROM behaviors b
    JOIN users u ON u.user_id = b.user_id
    GROUP BY b.user_id, u.channel
)
SELECT channel,
       SUM(has_pv)                                     AS pv_users,
       SUM(has_cart)                                   AS cart_users,
       SUM(has_fav)                                    AS fav_users,
       SUM(has_pay)                                    AS pay_users,
       ROUND(100 * SUM(has_cart) / NULLIF(SUM(has_pv), 0), 2) AS view_to_cart_pct,
       ROUND(100 * SUM(has_pay)  / NULLIF(SUM(has_cart), 0), 2) AS cart_to_pay_pct,
       ROUND(100 * SUM(has_pay)  / NULLIF(SUM(has_pv), 0), 2)   AS view_to_pay_pct
FROM ch
GROUP BY channel
ORDER BY pay_users DESC;

-- 结果3：分设备漏斗（移动端 vs PC 差异）
WITH dev AS (
    SELECT b.user_id, u.device,
           MAX(IF(b.action = 'pv', 1, 0))   AS has_pv,
           MAX(IF(b.action = 'cart', 1, 0)) AS has_cart,
           MAX(IF(b.action = 'pay', 1, 0))  AS has_pay
    FROM behaviors b
    JOIN users u ON u.user_id = b.user_id
    GROUP BY b.user_id, u.device
)
SELECT device,
       SUM(has_pv)                                     AS pv_users,
       SUM(has_cart)                                   AS cart_users,
       SUM(has_pay)                                    AS pay_users,
       ROUND(100 * SUM(has_pay) / NULLIF(SUM(has_pv), 0), 2) AS view_to_pay_pct
FROM dev
GROUP BY device
ORDER BY pv_users DESC;

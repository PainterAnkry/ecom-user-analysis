-- =====================================================================
-- 06 渠道获客与投放效率分析
-- 口径说明：
--   * 渠道 = 用户注册渠道（首触归因口径）
--   * GMV/订单按支付时间归属到用户注册渠道
--   * 付费渠道成本来自 channel_cost 表（模拟口径：按当月新增注册 x CPA），
--     免费渠道（直接访问/自然搜索）成本为 0，不参与 ROAS 计算
--   * 新客首购率 = 注册日 ≤ 行为窗口内、且 30 天内完成首购 / 窗口内新注册
-- =====================================================================

-- 结果1：渠道整体质量概览
SELECT u.channel                                  AS channel,
       COUNT(DISTINCT u.user_id)                  AS users,
       COUNT(DISTINCT IF(u.reg_date BETWEEN '2025-06-02' AND '2025-08-31', u.user_id, NULL)) AS new_users,
       COUNT(DISTINCT o.user_id)                  AS buyers,
       ROUND(100 * COUNT(DISTINCT o.user_id) / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS buy_rate_pct,
       COUNT(o.order_id)                          AS orders,
       ROUND(SUM(o.amount), 2)                    AS gmv,
       ROUND(100 * SUM(o.amount) / NULLIF(SUM(SUM(o.amount)) OVER (), 0), 2) AS gmv_share_pct,
       ROUND(SUM(o.amount) / NULLIF(COUNT(o.order_id), 0), 2)  AS aov,
       ROUND(SUM(o.amount) / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS arpu
FROM users u
LEFT JOIN orders o ON o.user_id = u.user_id
GROUP BY u.channel
ORDER BY gmv DESC;

-- 结果2：付费渠道全窗口 ROAS（GMV / 获客花费；花费含窗口前早期注册成本，
-- 与"用户沉没获客成本 vs 生命周期GMV"口径一致，避免注册月/支付月错配）
WITH ch_gmv AS (
    SELECT u.channel AS channel,
           COUNT(DISTINCT u.user_id)   AS users,
           COUNT(o.order_id)           AS orders,
           ROUND(SUM(o.amount), 2)     AS gmv
    FROM users u
    LEFT JOIN orders o ON o.user_id = u.user_id
    WHERE u.channel IN ('社交媒体', '信息流广告', '短信/邮件营销')
    GROUP BY u.channel
),
ch_cost AS (
    SELECT channel, SUM(spend) AS spend FROM channel_cost GROUP BY channel
)
SELECT g.channel                       AS channel,
       g.users                         AS registered_users,
       g.orders                        AS orders,
       g.gmv                           AS gmv,
       c.spend                         AS total_spend,
       ROUND(g.gmv / NULLIF(c.spend, 0), 2) AS roas,
       ROUND(c.spend / NULLIF(g.gmv, 0), 2) AS cost_per_100_yuan
FROM ch_gmv g
LEFT JOIN ch_cost c ON c.channel = g.channel
ORDER BY g.gmv DESC;

-- 结果3：窗口内新注册用户的 30 天首购率（获客质量）
SELECT u.channel                                AS channel,
       COUNT(DISTINCT u.user_id)                AS new_users,
       COUNT(DISTINCT IF(o.user_id IS NOT NULL AND DATEDIFF(o.pay_dt, u.reg_date) <= 30,
                         u.user_id, NULL))      AS first_buy_30d,
       ROUND(100 * COUNT(DISTINCT IF(o.user_id IS NOT NULL AND DATEDIFF(o.pay_dt, u.reg_date) <= 30,
                                     u.user_id, NULL)) / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS first_buy_30d_pct
FROM users u
LEFT JOIN (
    SELECT user_id, MIN(pay_dt) AS pay_dt
    FROM orders
    GROUP BY user_id
) o ON o.user_id = u.user_id
WHERE u.reg_date BETWEEN '2025-06-02' AND '2025-08-31'
GROUP BY u.channel
ORDER BY first_buy_30d_pct DESC;

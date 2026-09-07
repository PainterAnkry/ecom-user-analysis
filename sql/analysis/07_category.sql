-- =====================================================================
-- 07 品类与商品分析
-- 口径说明：
--   * 品类 = 一级品类；订单金额 = 实付口径
--   * 价格带基于订单商品单价（orders.product_id -> products.price）
--   * 跨品类关联购买：同一用户 7 天内购买的两个不同品类视为一次关联
-- =====================================================================

-- 结果1：品类业绩排名（GMV / 订单 / 买家 / 客单价 / 折扣率）
SELECT o.category_name                              AS category,
       COUNT(o.order_id)                            AS orders,
       ROUND(SUM(o.amount), 2)                      AS gmv,
       COUNT(DISTINCT o.user_id)                    AS buyers,
       ROUND(SUM(o.amount) / NULLIF(COUNT(o.order_id), 0), 2) AS aov,
       ROUND(100 * SUM(o.coupon_amount) / NULLIF(SUM(o.original_amount), 0), 2) AS discount_rate_pct,
       ROUND(SUM(o.qty) / NULLIF(COUNT(o.order_id), 0), 2)     AS avg_qty,
       ROUND(100 * SUM(o.amount) / NULLIF(SUM(SUM(o.amount)) OVER (), 0), 2) AS gmv_share_pct
FROM orders o
GROUP BY o.category_name
ORDER BY gmv DESC;

-- 结果2：商品价格带表现（含支付前加购率：价格带内用户级）
SELECT CASE WHEN p.price < 50      THEN '0~50元'
            WHEN p.price < 100     THEN '50~100元'
            WHEN p.price < 200     THEN '100~200元'
            WHEN p.price < 500     THEN '200~500元'
            ELSE '500元以上' END                     AS price_band,
       COUNT(o.order_id)                             AS orders,
       ROUND(SUM(o.amount), 2)                       AS gmv,
       COUNT(DISTINCT o.user_id)                     AS buyers,
       ROUND(SUM(o.amount) / NULLIF(COUNT(o.order_id), 0), 2) AS aov,
       ROUND(100 * COUNT(o.order_id) / NULLIF(SUM(COUNT(o.order_id)) OVER (), 0), 2) AS order_share_pct
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY CASE WHEN p.price < 50      THEN '0~50元'
              WHEN p.price < 100     THEN '50~100元'
              WHEN p.price < 200     THEN '100~200元'
              WHEN p.price < 500     THEN '200~500元'
              ELSE '500元以上' END
ORDER BY MIN(p.price);

-- 结果3：性别 x 品类偏好（GMV 口径，用于选品与推荐策略）
SELECT u.sex                       AS sex,
       o.category_name             AS category,
       COUNT(o.order_id)           AS orders,
       ROUND(SUM(o.amount), 2)     AS gmv,
       COUNT(DISTINCT o.user_id)   AS buyers
FROM orders o
JOIN users u ON u.user_id = o.user_id
GROUP BY u.sex, o.category_name
ORDER BY u.sex, gmv DESC;

-- 结果4：跨品类关联购买 TOP（7 天窗口，用户级计数；供连带推荐/捆绑销售）
WITH udp AS (
    SELECT DISTINCT user_id, category_id, category_name, DATE(pay_dt) AS pay_date
    FROM orders
)
SELECT a.category_name                              AS cat_a,
       b.category_name                              AS cat_b,
       COUNT(DISTINCT a.user_id)                    AS related_users,
       COUNT(*)                                     AS pair_days
FROM udp a
JOIN udp b ON a.user_id = b.user_id
          AND a.category_id < b.category_id
          AND ABS(DATEDIFF(a.pay_date, b.pay_date)) <= 7
GROUP BY a.category_name, b.category_name
ORDER BY related_users DESC, pair_days DESC
LIMIT 12;

-- =====================================================================
-- 04 RFM 用户价值分层
-- 口径说明：
--   * 计算对象：窗口内（6/2~8/31）至少支付过 1 单的买家
--   * R 最近一次支付距 2025-08-31 的天数；F 支付笔数；M 累计实付 GMV
--   * 打分：R 越小分越高（5=最近支付），F/M 越大分越高；
--     分位数方法 NTILE(5)，5 档 = 前 20%
--   * 分层规则（经典 RFM 八宫格，高分段 = 分值 ≥ 4）：
--     重要价值=三高；重要发展=R高F低M高（新近高频额）；… 见 CASE
-- =====================================================================

-- 结果1：用户级 R/F/M 明细与标签（可回流至运营做 1v1 触达）
WITH buyer AS (
    SELECT user_id,
           DATEDIFF('2025-08-31', MAX(pay_dt))                      AS recency_days,
           COUNT(*)                                                 AS freq_orders,
           ROUND(SUM(amount), 2)                                    AS monetary_gmv
    FROM orders
    GROUP BY user_id
),
scored AS (
    SELECT user_id,
           recency_days, freq_orders, monetary_gmv,
           NTILE(5) OVER (ORDER BY recency_days)                    AS r_score,  -- 天数升序 => 最近支付得分高
           NTILE(5) OVER (ORDER BY freq_orders)                     AS f_score,
           NTILE(5) OVER (ORDER BY monetary_gmv)                    AS m_score
    FROM buyer
)
SELECT user_id,
       recency_days, freq_orders, monetary_gmv,
       r_score, f_score, m_score,
       CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '重要价值客户'
            WHEN r_score >= 4 AND f_score <  4 AND m_score >= 4 THEN '重要发展客户'
            WHEN r_score <  4 AND f_score >= 4 AND m_score >= 4 THEN '重要保持客户'
            WHEN r_score <  4 AND f_score <  4 AND m_score >= 4 THEN '重要挽留客户'
            WHEN r_score >= 4 AND f_score >= 4 AND m_score <  4 THEN '一般价值客户'
            WHEN r_score >= 4 AND f_score <  4 AND m_score <  4 THEN '一般发展客户'
            WHEN r_score <  4 AND f_score >= 4 AND m_score <  4 THEN '一般保持客户'
            ELSE '一般挽留客户' END                                 AS segment
FROM scored
ORDER BY monetary_gmv DESC;

-- 结果2：分层汇总（人数结构 + GMV 贡献，识别真正的价值基本盘）
WITH buyer AS (
    SELECT user_id,
           DATEDIFF('2025-08-31', MAX(pay_dt)) AS recency_days,
           COUNT(*) AS freq_orders,
           SUM(amount) AS monetary_gmv
    FROM orders GROUP BY user_id
),
scored AS (
    SELECT user_id, recency_days, freq_orders, monetary_gmv,
           NTILE(5) OVER (ORDER BY recency_days) AS r_score,
           NTILE(5) OVER (ORDER BY freq_orders)  AS f_score,
           NTILE(5) OVER (ORDER BY monetary_gmv) AS m_score
    FROM buyer
)
SELECT CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '重要价值客户'
            WHEN r_score >= 4 AND f_score <  4 AND m_score >= 4 THEN '重要发展客户'
            WHEN r_score <  4 AND f_score >= 4 AND m_score >= 4 THEN '重要保持客户'
            WHEN r_score <  4 AND f_score <  4 AND m_score >= 4 THEN '重要挽留客户'
            WHEN r_score >= 4 AND f_score >= 4 AND m_score <  4 THEN '一般价值客户'
            WHEN r_score >= 4 AND f_score <  4 AND m_score <  4 THEN '一般发展客户'
            WHEN r_score <  4 AND f_score >= 4 AND m_score <  4 THEN '一般保持客户'
            ELSE '一般挽留客户' END                                  AS segment,
       COUNT(*)                                                      AS users,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)              AS user_share_pct,
       ROUND(SUM(monetary_gmv), 2)                                   AS gmv,
       ROUND(100 * SUM(monetary_gmv) / SUM(SUM(monetary_gmv)) OVER (), 2) AS gmv_share_pct,
       ROUND(AVG(monetary_gmv), 2)                                   AS avg_gmv,
       ROUND(AVG(freq_orders), 2)                                    AS avg_orders
FROM scored
GROUP BY segment
ORDER BY gmv DESC;

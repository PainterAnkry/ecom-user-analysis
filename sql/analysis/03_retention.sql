-- =====================================================================
-- 03 留存分析
-- 口径说明：
--   * 周 = 自然周，以 2025-06-02（周一）为第 1 周起点
--   * 活跃定义 = 当周至少产生 1 条行为记录（浏览/加购/收藏/支付任一）
--   * 周活跃留存：以"当周活跃用户"为队列，观察其后续每周仍有活跃的比例
--   * 注册队列留存：以"当周新注册用户"为队列，观察其每周活跃比例
--     （第1周注册可能横跨窗口起点，若注册周早于第1周则不计入）
-- =====================================================================

-- 结果1：活跃用户周留存矩阵（cohort_wk=活跃周序号, week_offset=第几周后, act_users=双周交集用户数, cohort_size=队列规模, ret_rate=留存率)
WITH act AS (
    SELECT DISTINCT user_id, FLOOR(DATEDIFF(dt, '2025-06-02') / 7) AS wk
    FROM behaviors
),
pair AS (
    SELECT a.wk                                    AS cohort_wk,
           b.wk                                    AS week_wk,
           COUNT(DISTINCT b.user_id)               AS act_users
    FROM act a
    JOIN act b ON a.user_id = b.user_id AND b.wk >= a.wk
    GROUP BY a.wk, b.wk
),
cohort_size AS (
    SELECT wk, COUNT(*) AS size FROM act GROUP BY wk
)
SELECT p.cohort_wk,
       p.week_wk - p.cohort_wk                     AS week_offset,
       p.act_users,
       s.size                                      AS cohort_size,
       ROUND(100 * p.act_users / NULLIF(s.size, 0), 2) AS ret_rate
FROM pair p
JOIN cohort_size s ON s.wk = p.cohort_wk
ORDER BY p.cohort_wk, p.week_wk;

-- 结果2：注册队列留存（新注册用户分周队列，观察注册后各周活跃比例）
WITH reg AS (
    SELECT user_id,
           FLOOR(DATEDIFF(reg_date, '2025-06-02') / 7) AS reg_wk
    FROM users
    WHERE reg_date BETWEEN '2025-06-02' AND '2025-08-31'
),
act AS (
    SELECT DISTINCT user_id, FLOOR(DATEDIFF(dt, '2025-06-02') / 7) AS act_wk
    FROM behaviors
),
sizes AS (
    SELECT reg_wk, COUNT(*) AS cohort_size FROM reg GROUP BY reg_wk
)
SELECT r.reg_wk + 1                                            AS reg_week_no,
       DATE_ADD('2025-06-02', INTERVAL r.reg_wk * 7 DAY)       AS reg_week_start,
       s.cohort_size,
       a.act_wk - r.reg_wk                                     AS week_offset,
       COUNT(DISTINCT a.user_id)                               AS retained_users,
       ROUND(100 * COUNT(DISTINCT a.user_id) / NULLIF(s.cohort_size, 0), 2) AS ret_rate
FROM reg r
JOIN sizes s ON s.reg_wk = r.reg_wk
JOIN act a ON a.user_id = r.user_id AND a.act_wk >= r.reg_wk
GROUP BY r.reg_wk, s.cohort_size, a.act_wk
ORDER BY r.reg_wk, week_offset;

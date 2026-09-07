-- ============================================================
-- 电商用户行为分析 库表结构（MySQL 8.0，utf8mb4）
-- 设计说明：
--   * 采用"维度表 + 事实表"星型简化模型（用户/商品 维度，行为/订单 事实）
--   * 行为事实表按 action 压缩编码 pv/cart/fav/pay，冗余 dt/hour/is_weekend
--     以规避函数索引开销，便于直接做时间切片分析（数仓分层常见做法）
--   * 事实表不建外键约束（大规模写入性能与数仓惯例），靠 ETL 层保证一致性
-- ============================================================

CREATE DATABASE IF NOT EXISTS ecom_analysis
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE ecom_analysis;

-- ---------- 用户维度表 ----------
DROP TABLE IF EXISTS users;
CREATE TABLE users (
  user_id           INT          NOT NULL COMMENT '用户ID',
  sex               VARCHAR(4)   NOT NULL COMMENT '性别：男/女',
  age               TINYINT      NOT NULL COMMENT '年龄',
  city_tier         TINYINT      NOT NULL COMMENT '城市层级 1~4（1=一线）',
  channel           VARCHAR(16)  NOT NULL COMMENT '注册渠道',
  device            VARCHAR(16)  NOT NULL COMMENT '设备',
  reg_date          DATE         NOT NULL COMMENT '注册日期',
  ab_group          CHAR(1)      NOT NULL COMMENT 'A/B 随机分组 A/B',
  campaign_eligible TINYINT      NOT NULL COMMENT '是否入组新客券实验 0/1',
  campaign_group    VARCHAR(2)   NOT NULL COMMENT '实验组（未入组为空）',
  PRIMARY KEY (user_id),
  KEY idx_users_reg (reg_date),
  KEY idx_users_channel (channel)
) ENGINE=InnoDB COMMENT='用户维度表（含A/B分组标签）';

-- ---------- 商品维度表 ----------
DROP TABLE IF EXISTS products;
CREATE TABLE products (
  product_id    INT          NOT NULL COMMENT '商品ID',
  category_id   SMALLINT     NOT NULL COMMENT '一级品类ID',
  category_name VARCHAR(16)  NOT NULL COMMENT '品类名称',
  product_name  VARCHAR(64)  NOT NULL COMMENT '商品名称',
  price         INT          NOT NULL COMMENT '单价（元）',
  list_date     DATE         NOT NULL COMMENT '上架日期',
  PRIMARY KEY (product_id),
  KEY idx_products_cat (category_id)
) ENGINE=InnoDB COMMENT='商品维度表';

-- ---------- 用户行为事实表（浏览/加购/收藏/支付）----------
DROP TABLE IF EXISTS behaviors;
CREATE TABLE behaviors (
  id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '事件ID(自增)',
  user_id     INT         NOT NULL COMMENT '用户ID',
  product_id  INT         NOT NULL COMMENT '商品ID',
  category_id SMALLINT    NOT NULL COMMENT '品类ID',
  action      VARCHAR(8)  NOT NULL COMMENT '事件类型 pv/cart/fav/pay',
  ts          BIGINT      NOT NULL COMMENT '事件时间戳(秒,UTC起算)',
  dt          DATE        NOT NULL COMMENT '事件日期(业务日)',
  hour        TINYINT     NOT NULL COMMENT '事件小时0-23',
  is_weekend  TINYINT     NOT NULL COMMENT '是否周末 0/1',
  PRIMARY KEY (id),
  KEY idx_beh_user_dt (user_id, dt),
  KEY idx_beh_dt_action (dt, action),
  KEY idx_beh_user_action (user_id, action),
  KEY idx_beh_product (product_id)
) ENGINE=InnoDB COMMENT='用户行为事实表：pv=浏览 cart=加购 fav=收藏 pay=支付';

-- ---------- 订单事实表（支付即成交订单）----------
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  order_id        INT           NOT NULL COMMENT '订单ID',
  user_id         INT           NOT NULL COMMENT '用户ID',
  product_id      INT           NOT NULL COMMENT '商品ID',
  category_id     SMALLINT      NOT NULL COMMENT '品类ID',
  category_name   VARCHAR(16)   NOT NULL COMMENT '品类名称',
  qty             TINYINT       NOT NULL COMMENT '件数',
  original_amount DECIMAL(10,2) NOT NULL COMMENT '原价金额',
  coupon_amount   DECIMAL(10,2) NOT NULL COMMENT '优惠券抵扣金额',
  amount          DECIMAL(10,2) NOT NULL COMMENT '实付金额(=GMV口径)',
  pay_dt          DATETIME      NOT NULL COMMENT '支付时间',
  PRIMARY KEY (order_id),
  KEY idx_orders_user (user_id),
  KEY idx_orders_paydt (pay_dt)
) ENGINE=InnoDB COMMENT='订单事实表：GMV=SUM(amount)';

-- ---------- 渠道月度投放成本表（模拟投放预算口径）----------
DROP TABLE IF EXISTS channel_cost;
CREATE TABLE channel_cost (
  channel   VARCHAR(16)   NOT NULL COMMENT '付费渠道',
  month     CHAR(7)       NOT NULL COMMENT '月份 YYYY-MM',
  new_users INT           NOT NULL COMMENT '该月新增注册',
  cpa       DECIMAL(8,2)  NOT NULL COMMENT '单注册成本(元)',
  spend     DECIMAL(12,2) NOT NULL COMMENT '当月投放花费(元)',
  KEY idx_cost_channel (channel, month)
) ENGINE=InnoDB COMMENT='渠道成本表（营销模拟口径）';

# -*- coding: utf-8 -*-
"""
01 模拟数据生成器
=================
电商平台真实行为数据无法公开获取，本项目按公开行业经验参数化生成一份
"足够真实"的模拟数据（3 个月、13 周、1 万用户、约 70~80 万条行为记录），
覆盖：用户属性、商品目录、浏览/加购/收藏/支付行为、订单明细。

业务规律内置（用于支撑后续分析的"因果"）：
1. 渠道质量差异：自然搜索/直接访问用户付费意愿高，广告渠道量大人群杂；
2. 新用户红利：注册后 2 周内活跃与转化加成，随后衰减（用于留存/新手期分析）；
3. 用户异质性：活跃度、付费意愿服从厚尾分布（少量高频用户贡献大部分 GMV）；
4. 周末效应：周末活跃、转化略高于工作日；
5. 价格弹性：低价商品转化率高于高价；
6. A/B 实验：6/2~7/31 注册用户按 50/50 分 A/B 组，8 月起 B 组收到"新客券"，
   实验中真实施加 18% 转化加成（可被假设检验识别）。

输出：data/users.csv / products.csv / behaviors.csv / orders.csv / channel_cost.csv
"""
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

rng = np.random.default_rng(config.SEED)

# ============================================================
# 1. 基础业务参数
# ============================================================
# 渠道: 名称, 占比, 活跃加成(logit 域), 付费加成, 单注册成本(元, 0=免费渠道)
CHANNELS = [
    ("直接访问", 0.10, +0.10, 1.00, 0.0),
    ("自然搜索", 0.30, +0.15, 1.15, 0.0),
    ("社交媒体", 0.18, -0.05, 0.92, 20.0),
    ("信息流广告", 0.27, -0.30, 0.80, 45.0),
    ("短信/邮件营销", 0.15, -0.15, 0.88, 18.0),
]
ch_names = [c[0] for c in CHANNELS]
ch_share = np.array([c[1] for c in CHANNELS])
ch_act = np.array([c[2] for c in CHANNELS])
ch_pay = np.array([c[3] for c in CHANNELS])
ch_cpa = np.array([c[4] for c in CHANNELS])
ch_share /= ch_share.sum()

# 品类: 名称, 目录占比, 价格对数正态(log 中位数, sigma)
CATEGORIES = [
    ("服饰鞋包", 0.19, np.log(165), 0.55),
    ("手机数码", 0.13, np.log(1100), 0.60),
    ("美妆个护", 0.11, np.log(175), 0.50),
    ("食品生鲜", 0.10, np.log(55), 0.50),
    ("运动户外", 0.09, np.log(285), 0.60),
    ("家居日用", 0.09, np.log(120), 0.55),
    ("家用电器", 0.07, np.log(950), 0.65),
    ("母婴玩具", 0.06, np.log(150), 0.60),
    ("图书文娱", 0.06, np.log(58), 0.45),
    ("汽车用品", 0.05, np.log(340), 0.70),
]
cat_names = [c[0] for c in CATEGORIES]
cat_share = np.array([c[1] for c in CATEGORIES]); cat_share /= cat_share.sum()
cat_pmu = np.array([c[2] for c in CATEGORIES])
cat_psigma = np.array([c[3] for c in CATEGORIES])

# 性别 x 品类偏好系数（女性偏服饰美妆母婴，男性偏数码汽车家电运动）
SEX_CAT_PREF = {
    "女": np.array([1.35, 0.70, 1.45, 1.00, 0.90, 1.10, 0.75, 1.30, 0.95, 0.60]),
    "男": np.array([0.65, 1.30, 0.60, 1.00, 1.10, 0.90, 1.25, 0.70, 1.05, 1.40]),
}
BRANDS = ["悦享", "极客", "南风", "乐购", "优选", "星选", "匠造", "云帆", "纯甄", "潮集"]

# 24 小时访问权重（晚上为高峰）
HOUR_W = np.array([
    0.006, 0.003, 0.002, 0.002, 0.002, 0.003, 0.008, 0.020, 0.038, 0.052, 0.056, 0.058,
    0.062, 0.055, 0.048, 0.045, 0.048, 0.055, 0.065, 0.088, 0.105, 0.095, 0.058, 0.026,
])
HOUR_W /= HOUR_W.sum()

REG_START = date.fromisoformat(config.SIM["reg_start"])
REG_END = date.fromisoformat(config.SIM["reg_end"])
WEEK_START = date.fromisoformat(config.SIM["week_start"])
N_WEEKS = config.SIM["weeks"]
WEEK_END = WEEK_START + timedelta(weeks=N_WEEKS) - timedelta(days=1)
N_USERS = config.SIM["n_users"]
N_PRODUCTS = 3000
N_CAT = len(cat_names)

# 实验口径
CAMP_START = date.fromisoformat(config.SIM["campaign_eligible"][0])
CAMP_END = date.fromisoformat(config.SIM["campaign_eligible"][1])
AB_START = date.fromisoformat(config.AB_WINDOW_START)
AB_END = date.fromisoformat(config.AB_WINDOW_END)
COUPON_LIFT = 0.18          # B 组投放期转化加成
COUPON_MIN_AMT = 49.0       # 用券门槛

print(f"[1] 行为窗口 {WEEK_START} ~ {WEEK_END}（{N_WEEKS} 周）")

# ============================================================
# 2. 生成商品目录
# ============================================================
n_per_cat = np.maximum(np.round(cat_share * N_PRODUCTS).astype(int), 100)
n_per_cat[-1] += N_PRODUCTS - n_per_cat.sum()
products = []      # (product_id, category_id, name, price, list_date)
list_days = (REG_START - date(2025, 1, 1)).days
pid = 0
for ci, n in enumerate(n_per_cat):
    price = np.round(np.exp(rng.normal(cat_pmu[ci], cat_psigma[ci], n)), 0).astype(int)
    price = np.maximum(price, 9)
    offsets = rng.integers(0, list_days, n)
    base_d = date(2025, 1, 1)
    for i in range(n):
        pid += 1
        products.append((pid, ci + 1, cat_names[ci],
                         f"{rng.choice(BRANDS)}{cat_names[ci]}款-{pid:04d}",
                         int(price[i]), (base_d + timedelta(days=int(offsets[i]))).isoformat()))
products = pd.DataFrame(products, columns=["product_id", "category_id", "category_name", "product_name", "price", "list_date"])
price_arr = products["price"].to_numpy()
# 价格弹性系数：价格越低转化越高（相对 150 元基准）
price_aff = np.clip(np.exp(-0.7 * (np.log(price_arr) - np.log(150.0))), 0.15, 2.0)
prod_by_cat = {ci: products.index[products["category_id"] == ci + 1].to_numpy() for ci in range(N_CAT)}
# 商品热度（品类内长尾：少数爆款被浏览的概率远高于普通款）
pop_by_cat = {}
for ci, idxs in prod_by_cat.items():
    w = 10 ** rng.normal(-1.1, 1.1, len(idxs))
    w = np.clip(w, 1e-4, None)
    pop_by_cat[ci] = w / w.sum()

# ============================================================
# 3. 生成用户（含渠道 / 画像 / 实验分组 / 潜在活跃度）
# ============================================================
reg_days_total = (REG_END - REG_START).days + 1
reg_off = rng.integers(0, reg_days_total, N_USERS)     # 相对注册起始的偏移
users = pd.DataFrame({
    "user_id": np.arange(1, N_USERS + 1),
    "reg_date": [(REG_START + timedelta(days=int(o))).isoformat() for o in reg_off],
})
channel_idx = rng.choice(len(ch_names), N_USERS, p=ch_share)
sex = rng.choice(["女", "男"], N_USERS, p=[0.53, 0.47])
age = np.concatenate([
    rng.integers(18, 25, int(N_USERS * 0.22)),
    rng.integers(25, 35, int(N_USERS * 0.38)),
    rng.integers(35, 45, int(N_USERS * 0.24)),
    rng.integers(45, 62, N_USERS - int(N_USERS * 0.84)),
]); rng.shuffle(age)
users["sex"] = sex
users["age"] = age
users["city_tier"] = rng.choice([1, 2, 3, 4], N_USERS, p=[0.27, 0.33, 0.25, 0.15])
users["channel"] = [ch_names[i] for i in channel_idx]
users["device"] = rng.choice(["iOS", "Android", "PC/其他"], N_USERS, p=[0.45, 0.48, 0.07])
users["ab_group"] = rng.choice(["A", "B"], N_USERS)
# 实验入组：注册日在 6/2~7/31 之间
eligible = users["reg_date"].between(CAMP_START.isoformat(), CAMP_END.isoformat())
users["campaign_eligible"] = np.where(eligible, 1, 0)
users["campaign_group"] = np.where(users["campaign_eligible"] == 1, users["ab_group"], "")

# ---- 用户潜在活跃度 / 付费意愿（厚尾异质性）----
# 活跃度设计：窗口前注册的"存量老客"活跃水平稳定（基本盘）；
# 窗口内新注册用户存在"新手红利 + 热情衰减"：注册初期活跃冲高，随后
# 按个体节奏指数衰减至长期水平（留存衰减的来源，也是留存分析要度量的对象）
t0 = np.array([(pd.Timestamp(rd) - pd.Timestamp(WEEK_START)).days for rd in users["reg_date"]])
reg_in_window = t0 >= 0                          # 注册日落在行为窗口内
old_mu = -1.15 + ch_act[channel_idx] + rng.normal(0, 0.9, N_USERS)          # 老客长期活跃 logit
new_long = -2.45 + ch_act[channel_idx] + rng.normal(0, 0.95, N_USERS)       # 新客衰减后的 logit
lift_u = rng.uniform(0.8, 2.1, N_USERS)          # 新手期活跃提升幅度(logit)
tau_u = rng.uniform(16.0, 45.0, N_USERS)         # 衰减半程(天)，个体差异
mu_long = np.where(reg_in_window, new_long, old_mu)
pay_k = np.exp(rng.normal(0, 1.35, N_USERS))                            # 付费意愿倍率(厚尾对数正态)
cart_k = np.clip(np.exp(rng.normal(0, 0.65, N_USERS)), 0.05, 4.0)       # 加购倾向
# 品类偏好：目录占比 x 性别偏好 x 个体噪声
pref_w = np.empty((N_USERS, N_CAT))
for i in range(N_USERS):
    w = cat_share * SEX_CAT_PREF[sex[i]] * np.exp(rng.normal(0, 0.75, N_CAT))
    pref_w[i] = w / w.sum()

# ============================================================
# 4. 逐日行为模拟
# ============================================================
print("[2] 生成商品与用户完毕，开始逐日行为模拟 ...")
behav = []   # 行为事件
orders = []  # 支付订单明细
o_cnt = 0
total_days = N_WEEKS * 7

# 逐日模拟（活跃度衰减过程 + 会话/事件生成）
cd_left = np.zeros(N_USERS, dtype=int)   # 购买冷却剩余天数（购后短时间不再购，贴合真实购物节律）
for t in range(total_days):
    day = WEEK_START + timedelta(days=t)
    wknd = 1 if day.weekday() >= 5 else 0
    cd_left = np.maximum(cd_left - 1, 0)
    # ---- 活跃过程：μ(t) = 长期水平 + 新手红利 x exp(-(注册后天数)/τ) ----
    decay = np.exp(-np.maximum(t - t0, 0) / tau_u)
    mu_day = mu_long + np.where(reg_in_window, lift_u * decay, 0.0)
    xi = np.where(wknd, 0.15, 0.0)
    p_act = 1 / (1 + np.exp(-(mu_day + xi)))
    # 自回归使个体活跃在时间上聚集（来就是一阵子）
    if t == 0:
        z = rng.normal(0, 1, N_USERS)
    z = 0.62 * z + 0.38 * rng.normal(0, 1, N_USERS)
    active = (rng.random(N_USERS) < np.clip(p_act + 0.32 * (z > 0.8) - 0.32 * (z < -0.8), 0.001, 0.97))
    # ^ 简化：以潜状态修正活跃概率，产生"来则成片、走则沉寂"的时间聚集

    act_idx = np.flatnonzero(active)
    if len(act_idx) == 0:
        continue
    day_sec = np.datetime64(day.isoformat(), "s").astype("int64")

    # 会话数：1 + Poisson(0.7)，封顶 7
    n_sess = 1 + rng.poisson(0.7, len(act_idx))
    n_sess = np.minimum(n_sess, 7)

    # 每个会话：时长与商品数
    for j, u in enumerate(act_idx):
        n_s = n_sess[j]
        # 本次"来访"的付费加成 = 渠道质量 x 个体意愿 x 新客券实验加成
        pay_mult = ch_pay[channel_idx[u]] * pay_k[u]
        if users["campaign_eligible"].iat[u] and users["ab_group"].iat[u] == "B" \
                and AB_START <= day <= AB_END:
            pay_mult *= (1 + COUPON_LIFT)
        p_pay = 0.0064 * pay_mult * price_aff      # 逐商品支付概率
        p_cart = 0.15 * cart_k[u]
        for _ in range(n_s):
            # 会话时间（秒）；深夜会话保证当天结束前结束，避免跨天
            h = int(rng.choice(24, p=HOUR_W))
            day_end = day_sec + 86399
            s0 = day_sec + (h * 3600 + int(rng.integers(0, 3600)))
            s0 = min(s0, day_end - 1200)
            # 会话内浏览商品数：1 + Poisson(0.7)
            n_pv = 1 + rng.poisson(0.7)
            for _p in range(n_pv):
                c = int(rng.choice(N_CAT, p=pref_w[u]))
                idx = int(rng.choice(prod_by_cat[c], p=pop_by_cat[c]))
                pid0, price0 = products["product_id"].iat[idx], products["price"].iat[idx]
                ts_pv = s0 + int(rng.integers(0, 90))
                behav.append((u + 1, int(pid0), c + 1, "pv", ts_pv))
                r_cart = rng.random()
                if r_cart < p_cart:
                    behav.append((u + 1, int(pid0), c + 1, "cart", ts_pv + int(rng.integers(1, 200))))
                if rng.random() < 0.07 * cart_k[u]:
                    behav.append((u + 1, int(pid0), c + 1, "fav", ts_pv + int(rng.integers(1, 200))))
                if rng.random() < p_pay[idx] and cd_left[u] <= 0:
                    # 支付（生成订单）；购买后进入冷却期（模拟购买节律）
                    o_cnt += 1
                    cd_left[u] = int(rng.integers(6, 26))
                    qty = int(rng.choice([1, 2, 3], p=[0.78, 0.17, 0.05]))
                    ts_pay = min(ts_pv + int(rng.integers(60, 900)), day_end)
                    amt = round(float(price0) * qty, 2)
                    coupon = 0.0
                    # 新客券核销
                    if (users["campaign_eligible"].iat[u] and users["ab_group"].iat[u] == "B"
                            and AB_START <= day <= AB_END and amt >= COUPON_MIN_AMT and rng.random() < 0.5):
                        coupon = round(min(rng.uniform(8, 20), amt * 0.4), 2)
                        amt = round(amt - coupon, 2)
                    behav.append((u + 1, int(pid0), c + 1, "pay", ts_pay))
                    orders.append((o_cnt, u + 1, int(pid0), c + 1, cat_names[c], qty, round(float(price0) * qty, 2), coupon, amt, ts_pay))
    if (t + 1) % 14 == 0 or t == total_days - 1:
        print(f"   ...第 {t + 1}/{total_days} 天完成，行为 {len(behav):,} 条 / 订单 {len(orders):,} 笔")

# ---- 写行为表 ----
bdf = pd.DataFrame(behav, columns=["user_id", "product_id", "category_id", "action", "ts"])
bdf["ts_dt"] = pd.to_datetime(bdf["ts"], unit="s")
bdf["dt"] = bdf["ts_dt"].dt.strftime("%Y-%m-%d")
bdf["hour"] = bdf["ts_dt"].dt.hour
bdf["is_weekend"] = (bdf["ts_dt"].dt.dayofweek >= 5).astype("int8")
bdf = bdf.drop(columns=["ts_dt"])
behav_rows = len(bdf)
bdf.to_csv(config.DATA_DIR / "behaviors.csv", index=False)

# ---- 写订单表 ----
odf = pd.DataFrame(orders, columns=["order_id", "user_id", "product_id", "category_id", "category_name",
                                    "qty", "original_amount", "coupon_amount", "amount", "ts"])
odf["pay_dt"] = pd.to_datetime(odf["ts"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
odf = odf.drop(columns=["ts"])
odf.to_csv(config.DATA_DIR / "orders.csv", index=False)

users.to_csv(config.DATA_DIR / "users.csv", index=False)
products.to_csv(config.DATA_DIR / "products.csv", index=False)

# ---- 渠道成本（按当月新增注册人数 x CPA 折算投放预算，模拟口径）----
uc = users.copy()
uc["reg_month"] = pd.to_datetime(uc["reg_date"]).dt.to_period("M").astype(str)
cost_rows = []
for ch_i, ch in enumerate(ch_names):
    sub = uc[uc["channel"] == ch]
    if ch_cpa[ch_i] <= 0:
        continue
    for m, cnt in sub["reg_month"].value_counts().items():
        cost_rows.append((ch, m, int(cnt), float(ch_cpa[ch_i]), round(cnt * ch_cpa[ch_i], 2)))
cost_df = pd.DataFrame(cost_rows, columns=["channel", "month", "new_users", "cpa", "spend"])
cost_df.to_csv(config.DATA_DIR / "channel_cost.csv", index=False)

# ============================================================
# 5. 校验摘要（用于调参，不做任何"美化"）
# ============================================================
print("\n=========== 生成校验摘要 ===========")
print(f"用户: {len(users):,}  商品: {len(products):,}")
print(f"行为: {behav_rows:,} 行 | 订单: {len(odf):,} 笔 | 支付 GMV: {odf['amount'].sum():,.0f} 元")
act_stats = bdf.groupby("dt").size().reset_index(name="events")
print(f"日均事件: {act_stats['events'].mean():,.0f}  | 有行为天数: {bdf['dt'].nunique()}")
a_counts = bdf["action"].value_counts()
print("行为构成:", {k: int(v) for k, v in a_counts.items()})
buyers = bdf[bdf["action"] == "pay"]["user_id"].nunique()
print(f"购买人数: {buyers:,} ({buyers / len(users):.1%}) | 客单价: {odf['amount'].sum() / len(odf):.1f} 元")
print("文件已输出至 data/ 目录")

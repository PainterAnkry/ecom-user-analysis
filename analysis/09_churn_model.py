# -*- coding: utf-8 -*-
"""
09 用户流失预警模型
=====================
业务问题：识别"未来 1 个月不再下单"的高流失风险买家，支撑定向召回（PUSH/券），
降低沉默成本 —— 与 RFM"重要保持/挽留"分层互补（模型可提前到发生前预警）。

口径：
  * 建模人群：特征窗 2025-06-02 ~ 07-27 内至少支付 1 单的买家
  * 标签 y=1：标签窗 07-28 ~ 08-31 内 0 笔订单（流失）；y=0 有订单
  * 特征：画像（性别/年龄/城市/渠道/设备/新老客）+ 行为（浏览/加购/收藏量、
    活跃天数、品类宽度、周末占比）+ 消费（订单数、GMV、距窗末最近购买天数）
方法：
  * 逻辑回归（可解释，输出系数方向）与 随机森林（非线性+重要性）双模型对比
  * 评估：AUC / KS / Gini；业务视角 = 风险分层（十分位 lift）+ 高危名单精度
"""
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve, roc_auc_score

from common import query, savefig, PALETTE
import config

FEAT_END = config.MODEL_FEATURE_END          # 2025-07-27
LABEL_START = config.MODEL_LABEL_START        # 2025-07-28

# ---------- 1. 取数与特征工程 ----------
beh = query(f"""
    SELECT user_id,
           SUM(action = 'pv')                         AS n_pv,
           SUM(action = 'cart')                       AS n_cart,
           SUM(action = 'fav')                        AS n_fav,
           SUM(is_weekend)                            AS weekend_evt,
           COUNT(DISTINCT dt)                         AS act_days,
           COUNT(DISTINCT category_id)                AS n_cat
    FROM behaviors
    WHERE dt <= '{FEAT_END}'
    GROUP BY user_id
""")
ord_f = query(f"""
    SELECT user_id,
           COUNT(*)                                   AS n_ord_feat,
           ROUND(SUM(amount), 2)                      AS gmv_feat,
           DATEDIFF('{FEAT_END}', MAX(DATE(pay_dt)))  AS last_pay_gap
    FROM orders
    WHERE pay_dt <= '{FEAT_END}'
    GROUP BY user_id
""")
buyers_later = query(f"""
    SELECT DISTINCT user_id AS buyer_later FROM orders
    WHERE pay_dt >= '{LABEL_START}'
""")
users = query("SELECT user_id, sex, age, city_tier, channel, device, reg_date FROM users")
for _df, _cols in [(beh, ["n_pv", "n_cart", "n_fav", "weekend_evt", "act_days", "n_cat"]),
                   (ord_f, ["n_ord_feat", "gmv_feat", "last_pay_gap"])]:
    for _c in _cols:
        _df[_c] = pd.to_numeric(_df[_c], errors="coerce").fillna(0)

df = ord_f.merge(beh, on="user_id", how="left").merge(users, on="user_id", how="left")
df["y"] = (~df["user_id"].isin(buyers_later["buyer_later"])).astype(int)
for c in ["n_pv", "n_cart", "n_fav", "weekend_evt", "act_days", "n_cat"]:
    df[c] = df[c].fillna(0)
df["tenure_days"] = (pd.to_datetime(FEAT_END) - pd.to_datetime(df["reg_date"])).dt.days
df["is_new_user"] = (pd.to_datetime(df["reg_date"]) >= pd.Timestamp("2025-06-02")).astype(int)
df["sex_code"] = (df["sex"] == "男").astype(int)

feat_cols = ["age", "city_tier", "sex_code", "tenure_days", "is_new_user",
             "n_pv", "n_cart", "n_fav", "act_days", "n_cat", "weekend_evt",
             "n_ord_feat", "last_pay_gap"]
df["log_gmv"] = np.log1p(df["gmv_feat"])
feat_cols += ["log_gmv"]
df = pd.get_dummies(df, columns=["channel"], prefix="ch", drop_first=True)
df = pd.get_dummies(df, columns=["device"], prefix="dev", drop_first=True)
feat_cols += [c for c in df.columns if c.startswith("ch_") or c.startswith("dev_")]

df = df.fillna(0)
X = df[feat_cols].astype(float)
y = df["y"]
print(f"[建模] 人群 {len(df):,} 人（特征窗买家）| 流失率 {y.mean():.1%}")

# ---------- 2. 训练 / 评估 ----------
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
sc = StandardScaler().fit(X_tr)

lr = LogisticRegression(C=1.0, max_iter=2000, random_state=42)
lr.fit(sc.transform(X_tr), y_tr)
rf = RandomForestClassifier(n_estimators=400, max_depth=7, min_samples_leaf=40,
                            n_jobs=-1, random_state=42, class_weight="balanced")
rf.fit(X_tr, y_tr)

def metrics(y_true, prob):
    auc = roc_auc_score(y_true, prob)
    fpr, tpr, _ = roc_curve(y_true, prob)
    ks = float((tpr - fpr).max())
    return auc, ks, 2 * auc - 1

for name, prob in [("逻辑回归", lr.predict_proba(sc.transform(X_te))[:, 1]),
                   ("随机森林", rf.predict_proba(X_te)[:, 1])]:
    auc, ks, gini = metrics(y_te, prob)
    print(f"  {name}: AUC={auc:.4f} | KS={ks:.3f} | Gini={gini:.3f}")

# ---------- 3. 图：ROC / 特征重要性 / 风险分层 lift ----------
prob_te = rf.predict_proba(X_te)[:, 1]
auc_te, ks_te, _ = metrics(y_te, prob_te)
fig, ax = plt.subplots(figsize=(7.5, 6))
fpr, tpr, _ = roc_curve(y_te, prob_te)
ax.plot(fpr, tpr, lw=2, color=PALETTE[0],
        label=f"随机森林 (AUC={auc_te:.3f}, KS={ks_te:.2f})")
prob_lr = lr.predict_proba(sc.transform(X_te))[:, 1]
auc_lr, _, _ = metrics(y_te, prob_lr)
fpr2, tpr2, _ = roc_curve(y_te, prob_lr)
ax.plot(fpr2, tpr2, lw=1.5, ls="--", color=PALETTE[1], label=f"逻辑回归 (AUC={auc_lr:.3f})")
ax.plot([0, 1], [0, 1], "k:", lw=1)
ax.set_xlabel("假正率 FPR"); ax.set_ylabel("真正率 TPR")
ax.set_title(f"流失预警 ROC（特征窗 6/2~7/27 买家 → 预测 7/28 后 30 天流失）\n"
             f"流失率 {y.mean():.1%}，AUC {auc_te:.3f} 区分度良好")
ax.legend()
savefig(fig, "churn_roc")

imp = pd.Series(rf.feature_importances_, index=feat_cols).sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(9, 6))
top = imp.head(12)
zh = {"age": "年龄", "city_tier": "城市层级", "sex_code": "性别(男)", "tenure_days": "注册时长(天)",
      "is_new_user": "窗口内新客", "n_pv": "浏览数", "n_cart": "加购数", "n_fav": "收藏数",
      "act_days": "活跃天数", "n_cat": "覆盖品类数", "weekend_evt": "周末活跃事件",
      "n_ord_feat": "特征窗订单数", "last_pay_gap": "距窗末最近购买天数(天)", "log_gmv": "GMV(log)"}
top.index = [zh.get(c, c) for c in top.index]
ax.barh(top.index[::-1], top.values[::-1], color=PALETTE[0])
ax.set_xlabel("随机森林特征重要性")
ax.set_title("流失预警关键特征：活跃天数/最近购买天数/订单量 居前\n"
             "（“好久没来 + 买得少”比画像更能预测流失）")
savefig(fig, "churn_importance")

# 风险分层（测试集按预测概率十分位）
df_te = X_te.copy()
df_te["prob"] = prob_te
df_te["y"] = y_te.values
df_te["decile"] = pd.qcut(df_te["prob"], 10, labels=False, duplicates="drop")
lift = df_te.groupby("decile").agg(churn=("y", "mean"), n=("y", "size"))
base_rate = y_te.mean()
fig, ax = plt.subplots(figsize=(10, 5.5))
x = np.arange(len(lift))
bars = ax.bar(x, lift["churn"] * 100, color=[PALETTE[0] if i >= 7 else PALETTE[4] for i in x])
ax.axhline(base_rate * 100, color="gray", ls="--", lw=1.2)
ax.text(len(lift) - 0.6, base_rate * 100 + 1.2, f"整体流失率 {base_rate * 100:.1f}%",
        color="gray", fontsize=9, ha="right")
for xi, (_, row) in zip(x, lift.iterrows()):
    ax.text(xi, row["churn"] * 100 + 1, f"{row['churn'] * 100:.0f}%\n(n={int(row['n'])})",
            ha="center", fontsize=8.5)
ax.set_xticks(x)
ax.set_xticklabels([f"D{i+1}" for i in range(len(lift))])
ax.set_xlabel("风险十分位（D10 = 预测流失风险最高）"); ax.set_ylabel("实际流失率 %")
ax.set_title("风险分层：模型预测前 10% 用户的真实流失率是整体均值的 "
             f"{lift['churn'].iloc[-1] / base_rate:.1f} 倍 → 可用作召回名单")
savefig(fig, "churn_lift")

# ---------- 4. 业务交付：高危名单 ----------
top_n = 300
df_all = X.copy()
prob_all = rf.predict_proba(df_all)[:, 1]
df_all["user_id"] = df["user_id"].to_numpy()
df_all["prob"] = prob_all
risk = df_all.nlargest(top_n, "prob")[["user_id", "prob"]].reset_index(drop=True)
risk = risk.merge(users[["user_id", "sex", "age", "city_tier", "channel", "device", "reg_date"]],
                  on="user_id", how="left").merge(
    ord_f[["user_id", "n_ord_feat", "gmv_feat", "last_pay_gap"]], on="user_id", how="left")
risk.to_csv(config.MODEL_DIR / "risk_top300.csv", index=False)
later_buyers = set(buyers_later["buyer_later"])
n_churned_top = int((~risk["user_id"].isin(later_buyers)).sum())
print(f"[交付] 高危召回名单 Top{top_n}：其中 {n_churned_top} 人已实际流失"
      f"（名单精度 {n_churned_top / top_n:.0%}，召回率视角见十分位图）→ output/model/risk_top300.csv")

# 逻辑回归系数（可解释性：负系数=该特征越高流失概率越低）
coef = pd.Series(lr.coef_[0], index=feat_cols).sort_values()
zh2 = dict(zh); zh2["log_gmv"] = "GMV(log)"
print("[LR 负相关(保护因素)]:", "、".join(f"{zh2.get(c, c)}({v:+.2f})" for c, v in coef.head(3).items()))
print("[LR 正相关(风险因素)]:", "、".join(f"{zh2.get(c, c)}({v:+.2f})" for c, v in coef.tail(3).items()))
d10 = lift["churn"].iloc[-1] / base_rate
print(f"[风险分层] 最高风险十分位实际流失率 {lift['churn'].iloc[-1]*100:.0f}% "
      f"vs 最低分位 {lift['churn'].iloc[0]*100:.0f}% vs 整体 {base_rate*100:.0f}% "
      f"（Top分位是整体的 {d10:.1f} 倍）")

with open(config.MODEL_DIR / "churn_model.pkl", "wb") as f:
    pickle.dump({"lr": lr, "rf": rf, "scaler": sc, "feat_cols": feat_cols}, f)
print("[模型] 已保存 output/model/churn_model.pkl")

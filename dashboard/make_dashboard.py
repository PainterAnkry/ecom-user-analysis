# -*- coding: utf-8 -*-
"""
生成单页交互式数据看板（pyecharts -> HTML，浏览器打开即可交互）
数据源：output/sql_results 下的 SQL 分析结果（保证"SQL 出数 -> 看板展示"链路一致）

运行: python dashboard/make_dashboard.py
输出: dashboard/output/dashboard.html（自包含，双击打开）
说明: pyecharts 渲染的 echarts.js 默认走 CDN，需联网打开；也可截图/录屏放入简历。
"""
import sys
from pathlib import Path

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Bar, Funnel, Grid, HeatMap, Line, Page, Pie, Tab
from pyecharts.commons.utils import JsCode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

RES = config.SQL_RESULT_DIR
OUT = config.DASH_DIR / "output"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, GREEN, GRAY = "#2E6DA4", "#E8862E", "#4CAF50", "#9AA5B1"

def load(stem: str, no: int) -> pd.DataFrame:
    return pd.read_csv(RES / f"{stem}_{no:02d}.csv")

# ---------------- 数据加载 ----------------
kpi = load("01_kpi_overview", 1).iloc[0]
daily = load("01_kpi_overview", 2)
weekly = load("01_kpi_overview", 3)
funnel_all = load("02_funnel", 1)
funnel_ch = load("02_funnel", 2)
ret_reg = load("03_retention", 2)
rfm_seg = load("04_rfm", 2).sort_values("gmv_share_pct")
freq = load("05_repurchase", 1)
gap = load("05_repurchase", 2)
ch = load("06_channel", 1)
roas = load("06_channel", 2)
cat = load("07_category", 1).sort_values("gmv")
band = load("07_category", 2)

def ax_common(chart, title, **kw):
    return chart.set_global_opts(
        title_opts=opts.TitleOpts(title=title, title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        legend_opts=opts.LegendOpts(pos_top="6%"), **kw)

# ================= Tab1 经营总览 =================
daily["dt"] = pd.to_datetime(daily["dt"]).dt.strftime("%m-%d")
line_gmv = (
    Line()
    .add_xaxis(daily["dt"].tolist())
    .add_yaxis("日 GMV(元)", daily["gmv"].round(0).tolist(), is_smooth=True,
               yaxis_index=1, color=BLUE)
    .add_yaxis("支付人数", daily["pay_users"].tolist(), is_smooth=True,
               yaxis_index=0, color=ORANGE)
    .extend_axis(yaxis=opts.AxisOpts(name="日GMV(元)", position="right", splitline_opts=opts.SplitLineOpts(is_show=False)))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="日 GMV 与支付人数趋势（6/2~8/31）", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, interval=6)),
        yaxis_opts=opts.AxisOpts(name="支付人数"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        datazoom_opts=[opts.DataZoomOpts(range_start=40, range_end=100)],
        legend_opts=opts.LegendOpts(pos_top="6%"))
)

line_conv = (
    Line()
    .add_xaxis(daily["dt"].tolist())
    .add_yaxis("浏览→支付转化率 %", daily["view_to_pay_pct"].tolist(), is_smooth=True, color=GREEN)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="日浏览→支付转化率波动", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, interval=6)),
        yaxis_opts=opts.AxisOpts(min_=0),
        legend_opts=opts.LegendOpts(pos_top="6%"))
)

# 周 KPI
weekly["wk"] = "第" + weekly["wk"].astype(str) + "周"
bar_week = (
    Bar()
    .add_xaxis(weekly["wk"].tolist())
    .add_yaxis("订单量", weekly["orders"].tolist(), color=ORANGE)
    .add_yaxis("浏览UV(百人)", (weekly["uv"] / 100).round(1).tolist(), color=GRAY)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="周 KPI：订单量 vs 浏览UV", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        legend_opts=opts.LegendOpts(pos_top="6%"))
)

funnel_row = funnel_all.set_index("step")
funnel_sorted = funnel_row.reindex(["浏览商品(pv)", "加入购物车(cart)", "收藏商品(fav)", "支付下单(pay)"])
fun = (
    Funnel()
    .add("用户数", [[i, int(v)] for i, v in zip(funnel_sorted.index, funnel_sorted["users"])],
         label_opts=opts.LabelOpts(formatter="{b}: {c} 人", position="inside"))
    .set_global_opts(title_opts=opts.TitleOpts(title="全站转化漏斗（13周累计用户）",
                                               title_textstyle_opts=opts.TextStyleOpts(font_size=15)))
)
# ================= 第二屏：漏斗与留存 =================
ch_sorted = funnel_ch.sort_values("view_to_pay_pct")
bar_funnel_ch = (
    Bar()
    .add_xaxis(ch_sorted["channel"].tolist())
    .add_yaxis("浏览→加购 %", ch_sorted["view_to_cart_pct"].tolist(), color=ORANGE)
    .add_yaxis("加购→支付 %", ch_sorted["cart_to_pay_pct"].tolist(), color=GREEN)
    .add_yaxis("浏览→支付 %", ch_sorted["view_to_pay_pct"].tolist(), color=BLUE)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="渠道漏斗转化率对比", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        yaxis_opts=opts.AxisOpts(min_=0), legend_opts=opts.LegendOpts(pos_top="6%"))
)

ret_reg["label"] = pd.to_datetime(ret_reg["reg_week_start"]).dt.strftime("%m-%d")
cohorts = sorted(ret_reg["reg_week_no"].unique())[::-1]
weeks_off = sorted(ret_reg["week_offset"].unique())
heat_data = []
for yi, cw in enumerate(cohorts):
    sub = ret_reg[ret_reg["reg_week_no"] == cw].sort_values("week_offset")
    for _, row in sub.iterrows():
        heat_data.append([int(row["week_offset"]), yi, round(float(row["ret_rate"]), 1)])
heat = (
    HeatMap()
    .add_xaxis([f"第{o}周" if o else "当周" for o in range(len(weeks_off))])
    .add_yaxis("", [f"{pd.to_datetime(r).strftime('%m-%d')}注册" for r in
                    sorted(ret_reg["reg_week_start"].unique())[::-1]],
               heat_data, label_opts=opts.LabelOpts(is_show=True, position="inside",
                                                     formatter=JsCode("function(p){return p.value[2]||''}")))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="注册队列周留存热力图 %", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        visualmap_opts=opts.VisualMapOpts(min_=0, max_=100, is_calculable=True, orient="horizontal",
                                          pos_left="center", pos_bottom=0, range_color=["#E8F4F8", "#2E6DA4"]),
        legend_opts=opts.LegendOpts(is_show=False))
)
# ================= 第三屏：用户与品类 =================
rfm = rfm_seg.sort_values("gmv_share_pct")
bar_rfm = (
    Bar()
    .add_xaxis(rfm["segment"].tolist())
    .add_yaxis("人数占比 %", rfm["user_share_pct"].round(1).tolist(), color=GRAY)
    .add_yaxis("GMV 占比 %", rfm["gmv_share_pct"].round(1).tolist(), color=BLUE)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="RFM 分层：人数 vs GMV 贡献", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20)),
        yaxis_opts=opts.AxisOpts(min_=0), legend_opts=opts.LegendOpts(pos_top="6%"))
)

gap_order = ["7天内", "8~30天", "31~60天", "60天以上"]
gap = gap.set_index("gap_band").loc[gap_order].reset_index()
bar_gap = (
    Bar()
    .add_xaxis(gap["gap_band"].tolist())
    .add_yaxis("占买家比例 %", gap["pct_of_buyers"].round(1).tolist(), color=GREEN)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="首购→二次购买间隔分布", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        yaxis_opts=opts.AxisOpts(min_=0), legend_opts=opts.LegendOpts(pos_top="6%"))
)

ch2 = ch.sort_values("gmv")
bar_ch = (
    Bar()
    .add_xaxis(ch2["channel"].tolist())
    .add_yaxis("GMV(万元)", (ch2["gmv"] / 10000).round(1).tolist(), color=BLUE)
    .add_yaxis("ARPU(元)", ch2["arpu"].round(0).tolist(), color=ORANGE)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="渠道 GMV 与单位用户价值", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        yaxis_opts=opts.AxisOpts(min_=0), legend_opts=opts.LegendOpts(pos_top="6%"))
)

bar_cat = (
    Bar()
    .add_xaxis(cat["category"].tolist())
    .add_yaxis("GMV(万元)", (cat["gmv"] / 10000).round(1).tolist(), color=ORANGE)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="品类 GMV 结构", title_textstyle_opts=opts.TextStyleOpts(font_size=15)),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
        yaxis_opts=opts.AxisOpts(min_=0), legend_opts=opts.LegendOpts(pos_top="6%"))
)
# ================= 组装（单页直排看板） =================
page = Page(layout=Page.SimplePageLayout)
for _c in [line_gmv, line_conv, bar_week, fun, bar_funnel_ch, heat, bar_rfm, bar_gap, bar_ch, bar_cat]:
    page.add(_c)
out_file = OUT / "dashboard.html"
page.render(str(out_file))
print(f"看板已生成: {out_file}（浏览器打开，需联网加载 echarts）")


"""
Facebook 投流策略推荐工具 — Streamlit Web 界面 v2.0
三段式策略卡片 / 智能行业识别 / B2B优先 / USD全量标注
"""

import json
import os
import sys
import uuid
from datetime import datetime
from io import BytesIO, StringIO
from typing import List, Tuple

import pandas as pd
import streamlit as st

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from fb_ads_recommender import (
    AdsStrategyEngine,
    SmartInferrer,
    ReportGenerator,
    Product,
    StrategyCard,
    INDUSTRY_DEFAULTS,
    MARKET_PROFILES,
    BUSINESS_TYPE_STRATEGY,
    OBJECTIVE_LABELS,
    LIFECYCLE_WEIGHTS,
    MODEL_VERSION,
    MODEL_LAST_UPDATED,
    HistoricalCalibrator,
    KPI_DATA_SOURCE_TEMPLATE,
    CALIBRATION_FACTORS,
    match_industrial_subcategory,
    INDUSTRIAL_SUBCATEGORIES,
    ProductEnricher,
    EnrichmentResult,
    ShippingEstimator,
    TariffCalculator,
)

# ═══════════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="FB投流策略推荐工具",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
# CSS styles
# ═══════════════════════════════════════════════════════════════════
def inject_css():
    st.html("""
    <style>
    /* ===== 三段式策略卡片 ===== */
    .strat-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 0;
        margin-bottom: 20px;
        overflow: hidden;
        background: #fff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    /* 顶层 — 产品名 + 评分 + ROI + 主推目标 */
    .strat-top {
        padding: 18px 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    }
    .strat-product-name {
        font-size: 20px;
        font-weight: 700;
        color: #1a1a1a;
    }
    .strat-score-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 15px;
        font-weight: 700;
        color: #fff;
    }
    .score-excellent { background: #22c55e; }
    .score-medium   { background: #f59e0b; }
    .score-poor     { background: #ef4444; }
    .strat-roi {
        font-size: 16px;
        font-weight: 600;
        color: #2563eb;
    }
    .strat-objective {
        font-size: 14px;
        color: #6b7280;
    }
    .strat-objective strong { color: #374151; }

    /* 中层 — KPI 四格卡 */
    .strat-mid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1px;
        background: #f3f4f6;
        padding: 1px;
    }
    .kpi-cell {
        background: #fff;
        padding: 14px 16px;
        text-align: center;
    }
    .kpi-label {
        font-size: 12px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 700;
        color: #111827;
    }
    .kpi-bench {
        font-size: 12px;
        margin-top: 3px;
        font-weight: 500;
    }
    .bench-up   { color: #22c55e; }
    .bench-down { color: #ef4444; }
    .bench-flat { color: #9ca3af; }

    /* 底层 — 执行区 */
    .strat-bottom {
        padding: 16px 22px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
        border-top: 1px solid #f3f4f6;
        font-size: 13px;
        color: #4b5563;
    }
    .exec-item { }
    .exec-label {
        font-size: 11px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .exec-value {
        font-size: 14px;
        font-weight: 600;
        color: #1f2937;
    }

    /* 数据源行 */
    .data-source-line {
        text-align: right;
        font-size: 11px;
        color: #9ca3af;
        padding: 4px 22px 8px 0;
    }

    /* ===== 对比表格 heat bar ===== */
    .heat-bar {
        display: inline-block;
        height: 10px;
        border-radius: 5px;
        vertical-align: middle;
    }
    .heat-excellent { background: linear-gradient(90deg, #22c55e, #4ade80); }
    .heat-medium   { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .heat-poor     { background: linear-gradient(90deg, #ef4444, #f87171); }

    /* ===== 智能识别提示 ===== */
    .smart-detect-box {
        background: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 13px;
        color: #0369a1;
    }
    .smart-detect-box strong { color: #0284c7; }

    /* ===== Streamlit overrides ===== */
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    div[data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 8px; }

    /* ===== 侧边栏导航增强 — 加大字号、清晰醒目 ===== */
    section[data-testid="stSidebar"] * {
        font-size: 16px !important;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .st-bq,
    section[data-testid="stSidebar"] .st-br,
    section[data-testid="stSidebar"] .st-c0,
    section[data-testid="stSidebar"] .st-c1,
    section[data-testid="stSidebar"] .st-c2,
    section[data-testid="stSidebar"] .st-c3,
    section[data-testid="stSidebar"] .st-c4,
    section[data-testid="stSidebar"] .st-c5,
    section[data-testid="stSidebar"] .st-c6,
    section[data-testid="stSidebar"] .st-c7,
    section[data-testid="stSidebar"] .st-c8,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 18px !important;
        font-weight: 600 !important;
        line-height: 1.6 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 22px !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        font-size: 18px !important;
        padding: 14px 16px !important;
        border-radius: 8px !important;
        margin: 4px 0 !important;
        transition: background 0.2s !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #f3f4f6 !important;
    }
    </style>
    """)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

INDUSTRY_LIST = list(INDUSTRY_DEFAULTS.keys())
MARKET_LIST = list(MARKET_PROFILES.keys())
LIFECYCLE_LIST = list(LIFECYCLE_WEIGHTS.keys())
DEFAULT_MARKET = "北美"
DEFAULT_LIFECYCLE = "成长期"
DEFAULT_BUSINESS = "B2B"


def score_color(score: int) -> str:
    if score >= 80:
        return "score-excellent"
    elif score >= 60:
        return "score-medium"
    else:
        return "score-poor"


def score_label(score: int) -> str:
    if score >= 80:
        return "优秀"
    elif score >= 60:
        return "中等"
    else:
        return "待优化"


def bench_indicator(current: float, bench: float, invert: bool = False) -> Tuple[str, str]:
    """返回 (class, 符号)。invert=True 表示越低越好（如 CPC/CPA）"""
    if bench is None or bench == 0:
        return "bench-flat", "（预估值）"
    diff = current - bench
    pct = diff / bench
    if invert:
        if pct < -0.05:
            return "bench-up", "↓ 低于行业基准"
        elif pct > 0.05:
            return "bench-down", "↑ 高于行业基准"
        else:
            return "bench-flat", "≈ 持平行业基准"
    else:
        if pct > 0.05:
            return "bench-up", "↑ 高于行业基准"
        elif pct < -0.05:
            return "bench-down", "↓ 低于行业基准"
        else:
            return "bench-flat", "≈ 持平行业基准"


def format_usd(val) -> str:
    """安全格式化 USD，None 返回 '--'"""
    if val is None:
        return "--"
    if isinstance(val, float):
        if val >= 10:
            return f"${val:,.2f} USD"
        elif val >= 1:
            return f"${val:.2f} USD"
        else:
            return f"${val:.3f} USD"
    return str(val)


def format_pct(val) -> str:
    """安全格式化百分比"""
    if val is None:
        return "--"
    return f"{val:.2f}%"


# ═══════════════════════════════════════════════════════════════════
# Session state
# ═══════════════════════════════════════════════════════════════════

def init_session():
    defaults = {
        "products": [],          # list of dicts
        "strategy_cards": [],    # list of StrategyCard
        "generated": False,
        "view_mode": "card",     # "card" or "table"
        "business_type": "B2B",
        "next_product_id": 1,
        "enrichment_result": None,  # EnrichmentResult for last queried product
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════
# Product Input Page
# ═══════════════════════════════════════════════════════════════════

def render_product_input():
    st.header("产品管理")
    st.caption("添加你要投放 Facebook 广告的产品")

    # B2B/B2C toggle
    bt = st.radio(
        "业务类型",
        ["B2B", "B2C"],
        horizontal=True,
        help="默认 B2B：受众偏向采购决策者，出价策略采用 target_cost",
        key="biz_type_toggle",
    )
    st.session_state["business_type"] = bt

    # ── 单个产品输入 ──
    st.subheader("添加产品")

    col1, col2 = st.columns([2, 1])
    with col1:
        product_name = st.text_input(
            "产品名称",
            placeholder="例如：氧化铝砂纸、蓝牙耳机、不锈钢阀门…",
            key="pname_input",
        )

    # 初始化 er，确保所有代码路径下都有定义
    er = None

    # 智能识别
    if product_name.strip():
        matched, hits = SmartInferrer.match_industry(product_name.strip(), bt)
        sub_name, sub_matched = match_industrial_subcategory(product_name.strip())
        sub_hint = ""
        if matched == "其他工业品":
            if sub_matched:
                sub_hint = f" | 子类: {sub_name}"
            else:
                sub_hint = " | 子类: 未识别（兜底）"
        st.html(f"""
        <div class="smart-detect-box">
            <strong>智能识别：</strong>{matched}（命中 {hits} 个关键词）{sub_hint}
        </div>
        """)

        # ── 市场数据查询按钮 ──
        col_enrich_btn, col_enrich_info = st.columns([1, 3])
        with col_enrich_btn:
            if st.button("查询市场数据", key="enrich_btn", help="查询产品市场参考数据（本地参考表），自动填充客单价和利润率"):
                with st.spinner("正在查询产品市场数据..."):
                    er = ProductEnricher.enrich(
                        product_name.strip(),
                        subcategory=sub_name,
                        subcategory_matched=sub_matched,
                    )
                    st.session_state["enrichment_result"] = er

        er = st.session_state.get("enrichment_result")
        if er is not None and er.enriched:
            with col_enrich_info:
                src = er.data_source or "本地参考表"
                price_str = f"${er.unit_price_usd:,.2f} USD"
                if er.unit_price_low and er.unit_price_high:
                    price_str = f"${er.unit_price_low:,.0f}–${er.unit_price_high:,.0f} USD（参考均价 ${er.unit_price_usd:,.2f}）"
                margin_str = f"{er.profit_margin_pct:.0f}%" if er.profit_margin_pct else "未知"
                st.success(
                    f"市场查询结果：客单价 {price_str}，利润率 {margin_str}，"
                    f"数据来源: {src}",
                    icon="✅",
                )
        elif er is not None and not er.enriched:
            with col_enrich_info:
                st.info(
                    f"本地参考表未命中「{product_name.strip()}」，将使用行业默认值。",
                    icon="ℹ",
                )

        default_industry = matched
    else:
        default_industry = None
        sub_name = ""
        sub_matched = False

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        industry = st.selectbox(
            "行业类别",
            INDUSTRY_LIST,
            index=INDUSTRY_LIST.index(default_industry) if default_industry in INDUSTRY_LIST else 0,
        )
    with col_b:
        category = st.text_input("产品品类", value=industry, placeholder="可选自定义")

    # ── 参数详情（智能填充 + 可选手动修改） ──
    ind_defaults = INDUSTRY_DEFAULTS[industry]
    with col_c:
        target_market = st.selectbox(
            "目标市场", MARKET_LIST,
            index=MARKET_LIST.index(ind_defaults["target_market"]) if ind_defaults["target_market"] in MARKET_LIST else 0,
        )

    with st.expander("参数详情（可手动修改）", expanded=False):
        use_sys = st.checkbox(
            "使用系统推荐值（基于行业智能填充）",
            value=True,
            key="use_sys_defaults",
            help="勾选后自动使用行业基准数据填充单价/利润率/生命周期/转化周期，无需手动填写。",
        )

        # ── 从行业默认值 + 子类信息 + 富化数据推导推荐值 ──
        rec_unit_price = float(ind_defaults["unit_price_usd"])
        rec_margin = int(ind_defaults["profit_margin_pct"])
        rec_lifecycle = ind_defaults.get("lifecycle_stage", "成长期")
        rec_conv_days = int(ind_defaults["expected_conversion_days"])

        # 富化数据覆盖（优先级最高）
        enrichment_source = ""
        if er is not None and er.enriched:
            if er.unit_price_usd is not None:
                rec_unit_price = er.unit_price_usd
            if er.profit_margin_pct is not None:
                rec_margin = int(er.profit_margin_pct)
            if er.data_source:
                enrichment_source = er.data_source

        if use_sys:
            # ── 推荐值展示模式 ──
            unit_price = rec_unit_price
            margin = rec_margin
            lifecycle = rec_lifecycle
            conv_days = rec_conv_days

            enrich_note = ""
            if enrichment_source:
                enrich_note = f"，数据来源: {enrichment_source}"
            st.info(f"**已启用系统推荐值**（行业: {industry}{enrich_note}）", icon="ℹ")
            mc = st.columns(4)
            with mc[0]:
                st.metric("客单价", f"${unit_price:,.2f} USD", help="输入产品的平均销售单价，含运费（USD）。可使用「查询市场数据」获得实时市场参考价。")
            with mc[1]:
                st.metric("利润率", f"{margin}%", help="毛利润率（%），即 (售价-成本)/售价×100。可使用「查询市场数据」获得行业参考值。")
            with mc[2]:
                st.metric("生命周期", lifecycle, help="产品从上市到退市的预计阶段。新品或小配件填「新品」或「成长期」，成熟设备填「成熟期」。")
            with mc[3]:
                st.metric("转化周期", f"{conv_days} 天", help="从用户点击广告到完成购买的平均天数。标准快消品填 1-3 天，工业品客户决策周期长可填 14-60 天。")

            # 业务类型参数
            biz_type_param = st.selectbox(
                "B2B / B2C", ["B2B", "B2C"],
                index=0 if ind_defaults["business_type"] == "B2B" else 1,
                key="biz_param",
            )
        else:
            # ── 手动编辑模式 ──
            st.caption("取消勾选上方按钮后可手动修改各项参数。")

            lifecycle = st.selectbox(
                "生命周期",
                LIFECYCLE_LIST,
                index=LIFECYCLE_LIST.index(rec_lifecycle) if rec_lifecycle in LIFECYCLE_LIST else 1,
            )
            c1, c2 = st.columns([3, 2])
            with c1:
                up_min = max(1.0, rec_unit_price * 0.15)
                up_max = max(rec_unit_price * 6.0, 100.0)
                _up_slider = st.slider(
                    "客单价 (USD)",
                    min_value=up_min, max_value=up_max,
                    value=rec_unit_price,
                    step=max(1.0, round(rec_unit_price * 0.05, 1)),
                    key="up_slider",
                )
            with c2:
                unit_price = st.number_input(
                    "精确输入 (USD)", min_value=0.01,
                    value=_up_slider, format="%.2f", key="up_manual",
                )
            c3, c4 = st.columns([3, 2])
            with c3:
                _mg_slider = st.slider(
                    "利润率 (%)", min_value=1, max_value=95,
                    value=rec_margin, step=1, key="mg_slider",
                )
            with c4:
                margin = st.number_input(
                    "精确输入 (%)", min_value=1, max_value=95,
                    value=_mg_slider, step=1, key="mg_manual",
                )
            c5, c6 = st.columns([3, 2])
            with c5:
                cd_min = max(1, rec_conv_days - 10)
                cd_max = rec_conv_days + 30
                _cd_slider = st.slider(
                    "预期转化周期（天）",
                    min_value=cd_min, max_value=max(cd_max, 60),
                    value=rec_conv_days, step=1, key="cd_slider",
                )
            with c6:
                conv_days = st.number_input(
                    "精确输入（天）", min_value=1, max_value=365,
                    value=_cd_slider, step=1, key="cd_manual",
                )
            biz_type_param = st.selectbox(
                "B2B / B2C", ["B2B", "B2C"],
                index=0 if ind_defaults["business_type"] == "B2B" else 1,
                key="biz_param",
            )

    if st.button("添加产品", type="primary", use_container_width=True):
        if not product_name.strip():
            st.warning("请输入产品名称")
        else:
            pid = f"P-{st.session_state['next_product_id']:03d}"
            st.session_state["next_product_id"] += 1
            st.session_state["products"].append({
                "id": pid,
                "name": product_name.strip(),
                "category": category.strip() or industry,
                "industry": industry,
                "unit_price_usd": unit_price,
                "profit_margin_pct": margin,
                "target_market": target_market,
                "business_type": biz_type_param,
                "lifecycle_stage": lifecycle,
                "expected_conversion_days": conv_days,
                "subcategory": sub_name,
                "subcategory_matched": sub_matched,
                "enrichment_unit_price": er.unit_price_usd if (er is not None and er.enriched) else None,
                "enrichment_margin": er.profit_margin_pct if (er is not None and er.enriched) else None,
                "enrichment_source": er.data_source if (er is not None and er.enriched and er.data_source) else "",
                "enrichment_applied": bool(er is not None and er.enriched),
            })
            st.success(f"已添加：{product_name.strip()} ({pid})")
            # 清空输入框（保留富化结果供同一会话其他产品参考）
            if "enrichment_result" in st.session_state:
                del st.session_state["enrichment_result"]
            st.rerun()

    # ── 已添加的产品列表 ──
    if st.session_state["products"]:
        st.markdown("---")
        st.subheader(f"已添加产品（{len(st.session_state['products'])} 个）")
        products_df = pd.DataFrame(st.session_state["products"])
        display_cols = {
            "id": "ID",
            "name": "产品名称",
            "industry": "行业",
            "unit_price_usd": "客单价(USD)",
            "profit_margin_pct": "利润率(%)",
            "target_market": "目标市场",
            "business_type": "类型",
            "lifecycle_stage": "生命周期",
        }
        st.dataframe(
            products_df[list(display_cols.keys())].rename(columns=display_cols),
            use_container_width=True,
            hide_index=True,
        )

        # 删除 + 清空按钮
        cd1, cd2, cd3 = st.columns([2, 2, 2])
        with cd1:
            remove_id = st.selectbox(
                "选择要删除的产品",
                [p["id"] for p in st.session_state["products"]],
            )
        with cd2:
            if st.button("删除选中产品"):
                st.session_state["products"] = [
                    p for p in st.session_state["products"] if p["id"] != remove_id
                ]
                st.session_state["generated"] = False
                st.rerun()
        with cd3:
            if st.button("清空全部产品"):
                st.session_state["products"] = []
                st.session_state["generated"] = False
                st.rerun()

        # ── 生成策略按钮 ──
        st.markdown("---")
        if st.button("生成投流策略", type="primary", use_container_width=True):
            engine = AdsStrategyEngine()
            products_objs = [
                Product(
                    id=p["id"], name=p["name"], category=p["category"],
                    unit_price_usd=p["unit_price_usd"],
                    profit_margin_pct=p["profit_margin_pct"],
                    target_market=p["target_market"],
                    business_type=p["business_type"],
                    lifecycle_stage=p["lifecycle_stage"],
                    expected_conversion_days=p["expected_conversion_days"],
                    subcategory=p.get("subcategory", ""),
                    subcategory_matched=p.get("subcategory_matched", False),
                    enriched_unit_price=p.get("enrichment_unit_price"),
                    enriched_margin=p.get("enrichment_margin"),
                    enrichment_source=p.get("enrichment_source", ""),
                    enrichment_applied=p.get("enrichment_applied", False),
                )
                for p in st.session_state["products"]
            ]
            st.session_state["strategy_cards"] = engine.generate_all(products_objs)
            st.session_state["generated"] = True
            st.query_params["page"] = "策略结果"
            st.rerun()

    # ── 行业基准数据库速查 ──
    with st.expander("行业基准数据库速查"):
        bench_data = []
        for ind, vals in INDUSTRY_DEFAULTS.items():
            bench_data.append({
                "行业": ind,
                "类型": vals["business_type"],
                "客单价(USD)": vals["unit_price_usd"],
                "利润率(%)": vals["profit_margin_pct"],
                "CTR(%)": vals.get("expected_ctr", "--"),
                "CPC(USD)": vals.get("expected_cpc", "--"),
                "CPA(USD)": vals.get("expected_cpa", "--"),
                "ROAS": f"{vals['expected_roas']:.2f}x" if vals.get("expected_roas") else "--",
            })
        st.dataframe(pd.DataFrame(bench_data), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# Strategy Results Page
# ═══════════════════════════════════════════════════════════════════

def render_strategy_results():
    cards: List[StrategyCard] = st.session_state["strategy_cards"]

    st.header("投流策略结果")

    if not cards:
        st.info("暂无策略结果，请先在「产品管理」页添加产品并生成策略。")
        return

    # 切换模式
    col_v, col_e = st.columns([1, 2])
    with col_v:
        st.session_state["view_mode"] = st.radio(
            "展示模式", ["card", "table"],
            format_func=lambda x: "策略卡片" if x == "card" else "对比表格",
            horizontal=True,
            key="view_mode_radio",
        )

    # ── 导出 ──
    with col_e:
        ce1, ce2 = st.columns(2)
        with ce1:
            csv_data = ReportGenerator.to_csv(cards)
            st.download_button(
                "导出 CSV", csv_data, f"fb_strategies_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
            )
        with ce2:
            json_data = ReportGenerator.to_json(cards)
            st.download_button(
                "导出 JSON", json_data, f"fb_strategies_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                "application/json",
            )

    st.markdown("---")

    # 数据可信度横幅
    st.info(cards[0].data_confidence)

    if st.session_state["view_mode"] == "card":
        render_cards(cards)
    else:
        render_comparison_table(cards)


# ═══════════════════════════════════════════════════════════════════
# 三段式策略卡片
# ═══════════════════════════════════════════════════════════════════

def render_cards(cards: List[StrategyCard]):
    for card in cards:
        sc = score_color(card.priority_score)
        sl = score_label(card.priority_score)

        # ── KPI 基准对比判断 ──
        ctr_class, ctr_hint = bench_indicator(card.expected_ctr_pct, card.industry_ctr)
        cpc_class, cpc_hint = bench_indicator(card.expected_cpc, card.industry_cpc, invert=True)
        cpm_class, cpm_hint = bench_indicator(card.expected_cpm, None)  # CPM 来自市场
        cpa_class, cpa_hint = bench_indicator(card.max_cpa, card.industry_cpa, invert=True)

        # CPM 无行业单独基准，用市场整体值
        cpm_label = "（预估值）"

        audience_text = "、".join(card.audience_profiles[:3])

        # ── 运费 + 关税估算 ──
        unit_price = card.max_cpa * 10.0  # 从 CPA 反推近似单价
        ship = ShippingEstimator.estimate_shipping(
            product_name=card.product_name,
            unit_price=unit_price,
            quantity=100,
            transport_mode="sea",
            destination="US_West",
        )
        tariff = TariffCalculator.estimate_landed_cost(
            fob_price=unit_price,
            shipping_per_unit=ship["estimated_shipping_per_unit"],
        )
        ship_unit = ship["estimated_shipping_per_unit"]
        landed = tariff["landed_cost"]
        tariff_total = tariff["total_duty"]
        tariff_rate = tariff["effective_tariff_rate"]
        freshness_tag = getattr(card, 'data_freshness', 'normal')
        stale_warning = ' <span style="color:#ef4444;font-size:11px;">⚠ 数据超过12个月未更新</span>' if freshness_tag == "stale" else ""
        shipping_tariff_html = f"""
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:8px;">
                            <div><span style="color:#6b7280;">预估运费/件</span><br><strong style="color:#0891b2;">${ship_unit:.2f} USD</strong></div>
                            <div><span style="color:#6b7280;">预估关税/件</span><br><strong style="color:#d97706;">${tariff_total:.4f} USD</strong></div>
                            <div><span style="color:#6b7280;">落地总成本</span><br><strong style="font-size:15px;">${landed:.2f} USD</strong></div>
                        </div>
                        <div style="font-size:11px;color:#9ca3af;">
                            海运拼箱(美西) · 实际税率约 {tariff_rate}% · 基于 100 件批量估算{stale_warning}
                        </div>"""

        st.html(f"""
        <div class="strat-card">

            <!-- 顶层 — 产品名 + 评分 + ROI + 主推目标 -->
            <div class="strat-top">
                <div>
                    <span style="color:#6b7280;font-size:13px;">{card.category}</span><br>
                    <span class="strat-product-name">{card.product_name}</span>
                </div>
                <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
                    <span class="strat-score-badge {sc}">{card.priority_score}分 · {sl}</span>
                    <span class="strat-roi">ROI {card.roi_estimate:.2f}x</span>
                    <span class="strat-objective">
                        主推目标：<strong>{card.recommended_objective}</strong>
                    </span>
                </div>
            </div>

            <!-- 中层 — KPI 四格卡 -->
            <div class="strat-mid">
                <div class="kpi-cell">
                    <div class="kpi-label">CTR</div>
                    <div class="kpi-value">{format_pct(card.expected_ctr_pct)}</div>
                    <div class="kpi-bench {ctr_class}">{ctr_hint}</div>
                </div>
                <div class="kpi-cell">
                    <div class="kpi-label">CPC</div>
                    <div class="kpi-value">{format_usd(card.expected_cpc)}</div>
                    <div class="kpi-bench {cpc_class}">{cpc_hint}</div>
                </div>
                <div class="kpi-cell">
                    <div class="kpi-label">CPM</div>
                    <div class="kpi-value">{format_usd(card.expected_cpm)}</div>
                    <div class="kpi-bench bench-flat">{cpm_label}</div>
                </div>
                <div class="kpi-cell">
                    <div class="kpi-label">CPA 上限</div>
                    <div class="kpi-value">{format_usd(card.max_cpa)}</div>
                    <div class="kpi-bench {cpa_class}">{cpa_hint}</div>
                </div>
            </div>

            <!-- 底层 — 执行区 -->
            <div class="strat-bottom">
                <div class="exec-item">
                    <div class="exec-label">日预算</div>
                    <div class="exec-value">{format_usd(card.daily_budget_range[0])} – {format_usd(card.daily_budget_range[1])}</div>
                </div>
                <div class="exec-item">
                    <div class="exec-label">出价策略</div>
                    <div class="exec-value">{card.bid_strategy}</div>
                </div>
                <div class="exec-item">
                    <div class="exec-label">推荐受众</div>
                    <div class="exec-value" style="font-size:12px;">{audience_text}</div>
                </div>
                <div class="exec-item">
                    <div class="exec-label">投放时段</div>
                    <div class="exec-value">{card.recommended_peak_hours}</div>
                </div>
                <div class="exec-item">
                    <div class="exec-label">推荐版位</div>
                    <div class="exec-value" style="font-size:12px;">{', '.join(card.placement_preference)}</div>
                </div>
                <div class="exec-item">
                    <div class="exec-label">市场</div>
                    <div class="exec-value">{card.market} · {card.business_type}</div>
                </div>
            </div>

            <!-- 素材推荐模块 -->
            <div style="padding:14px 22px;border-top:1px solid #f0f0f0;background:#fafbff;">
                <div style="font-size:14px;font-weight:700;color:#2563eb;margin-bottom:10px;">
                    推荐素材类型
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;font-size:13px;">
                    <div>
                        <span style="color:#9ca3af;">格式：</span>
                        <strong>{card.creative_format}</strong>
                    </div>
                    <div>
                        <span style="color:#9ca3af;">比例：</span>
                        <strong>{card.creative_ratio}</strong>
                    </div>
                    <div>
                        <span style="color:#9ca3af;">CTA：</span>
                        <strong style="color:#2563eb;">{card.creative_cta}</strong>
                    </div>
                </div>
                <div style="margin-top:10px;font-size:12px;color:#6b7280;line-height:1.8;">
                    {''.join(f'<div style="display:flex;align-items:flex-start;gap:6px;"><span style="color:#22c55e;flex-shrink:0;">●</span><span>{tip}</span></div>' for tip in card.creative_tips)}
                </div>
            </div>

            <!-- 投放执行指南模块 -->
            <div style="padding:14px 22px;border-top:1px solid #f0f0f0;">
                <div style="font-size:14px;font-weight:700;color:#f59e0b;margin-bottom:10px;">
                    投放执行指南
                </div>
                <div style="font-size:12px;color:#4b5563;line-height:2.0;">
                    {''.join(f'<div>{step}</div>' for step in card.execution_steps)}
                </div>
                <div style="margin-top:8px;padding:8px 12px;background:#fffbeb;border-radius:6px;font-size:12px;color:#92400e;">
                    <strong>预算分配：</strong>{card.budget_split}
                </div>
                <div style="margin-top:6px;padding:8px 12px;background:#f0fdf4;border-radius:6px;font-size:12px;color:#166534;">
                    <strong>A/B 测试：</strong>{card.testing_strategy}
                </div>
            </div>

            <!-- 运费 + 关税估算折叠区 -->
            <div style="padding:14px 22px;border-top:1px solid #e5e7eb;background:#fafbfc;">
                <details style="font-size:13px;">
                    <summary style="cursor:pointer;font-weight:700;color:#0891b2;">  物流成本预估（运费 + 关税）</summary>
                    <div style="margin-top:12px;padding:12px;background:#f0f9ff;border-radius:8px;border:1px solid #bae6fd;">
                        {shipping_tariff_html}
                    </div>
                </details>
            </div>

            <!-- 数据源行 -->
            <div class="data-source-line">{card.data_confidence}</div>

        </div>
        """)


# ═══════════════════════════════════════════════════════════════════
# 对比表格（带 heat bar + USD）
# ═══════════════════════════════════════════════════════════════════

def render_comparison_table(cards: List[StrategyCard]):
    rows = []
    for card in cards:
        sc = score_color(card.priority_score)
        rows.append({
            "产品": card.product_name,
            "行业": card.category,
            "评分": card.priority_score,
            "评分等级": score_label(card.priority_score),
            "主推目标": card.recommended_objective,
            "日预算(USD)": f"{format_usd(card.daily_budget_range[0])} – {format_usd(card.daily_budget_range[1])}",
            "出价策略": card.bid_strategy,
            "CPA上限(USD)": format_usd(card.max_cpa),
            "CTR": format_pct(card.expected_ctr_pct),
            "CPC(USD)": format_usd(card.expected_cpc),
            "CPM(USD)": format_usd(card.expected_cpm),
            "ROI": f"{card.roi_estimate:.2f}x",
            "市场": card.market,
            "类型": card.business_type,
        })

    df = pd.DataFrame(rows)

    # 评分列加颜色
    def style_score(val):
        s = int(val)
        if s >= 80:
            color = "#22c55e"
        elif s >= 60:
            color = "#f59e0b"
        else:
            color = "#ef4444"
        return f"font-weight:700;color:{color}"

    styled = df.style.map(style_score, subset=["评分"])

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Heat bar 可视化
    st.markdown("### 综合评分散点对比")
    chart_data = pd.DataFrame([
        {"产品": c.product_name, "评分": c.priority_score, "ROI": c.roi_estimate}
        for c in cards
    ]).sort_values("评分", ascending=False)

    # 用 st.bar_chart 直观展示
    st.bar_chart(
        chart_data.set_index("产品")["评分"],
        color=["#22c55e"],
        use_container_width=True,
    )

    # Heat bar 单独列出
    for _, row in chart_data.iterrows():
        score_val = int(row["评分"])
        bar_width = score_val  # 0-100px
        bar_class = "heat-excellent" if score_val >= 80 else ("heat-medium" if score_val >= 60 else "heat-poor")
        st.html(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:3px 0;">
            <span style="width:120px;font-size:13px;">{row['产品']}</span>
            <span class="heat-bar {bar_class}" style="width:{bar_width}px;"></span>
            <span style="font-size:13px;font-weight:600;">{score_val}分</span>
        </div>
        """)


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    inject_css()
    init_session()

    st.title("Facebook 投流策略推荐工具")
    st.caption("基于 WordStream 2026 + DigitalPoint 2026 权威基准 · 17 行业覆盖")

    # ── 侧边栏导航（用 query_params 实现页面切换，避免修改已绑定 widget 的 session_state）──
    st.sidebar.title("导航")

    # 从 query_params 读取当前页面（首次访问默认为"产品管理"）
    query_page = st.query_params.get("page", "产品管理")

    # sidebar radio 的 index 由 query_params 决定
    page_options = ["产品管理", "策略结果"]
    default_idx = 0 if query_page == "产品管理" else 1

    selected = st.sidebar.radio(
        "页面切换",
        page_options,
        index=default_idx,
        key="sidebar_nav",
    )

    # 用户手动点击 radio 时，更新 query_params 并 rerun
    if selected != query_page:
        st.query_params["page"] = selected
        st.rerun()

    # 以 query_params 为准决定当前页面
    page = query_page

    if page == "产品管理":
        render_product_input()
    else:
        if st.session_state["generated"]:
            render_strategy_results()
        else:
            st.info("请先在「产品管理」页添加产品并点击「生成投流策略」按钮。")


if __name__ == "__main__":
    main()

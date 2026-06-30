"""
小众工业品 Facebook 广告数据调整系数
========================================

Facebook 无钢卷/活动板房/二手机械/化工原料等对应类目，
全部归入 "Industrial & Commercial"（WordStream 2025 基准：
  CTR 1.36% / CPC $0.86 / CPC(lead) $1.80 / CVR 9.34% / CPL $37.34）。

本模块提供小众工业品类相对于该基准的调整系数，
供 ProductEnricher 第四级查表使用。

用法：
    from utils.niche_industrial_data import NICHE_INDUSTRIAL_ADJUSTMENTS, apply_niche_adjustment
    result = apply_niche_adjustment("used excavator", baseline_ctr=1.36, baseline_cpc=0.86, ...)
"""

from typing import Dict, Any, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════
# 顶层元数据
# ═══════════════════════════════════════════════════════════════════
_META = {
    "baseline_industry": "Industrial & Commercial",
    "baseline_ctr": 1.36,      # WordStream 2025, Traffic campaigns, %
    "baseline_cpc": 0.86,      # WordStream 2025, Traffic campaigns, USD
    "baseline_cpc_lead": 1.80, # WordStream 2025, Lead campaigns, USD
    "baseline_cvr": 9.34,      # WordStream 2025, Lead campaigns, %
    "baseline_cpl": 37.34,     # WordStream 2025, Lead campaigns, USD
    "baseline_source": "WordStream Facebook Ads Benchmarks 2025 (554 US campaigns, Apr 2024-Jun 2025)",
    "global_ctr_median": 2.19, # Triple Whale 2025, 35000 brands
    "global_cpm_median": 14.19,# Triple Whale 2025
    "global_cpc_median": 0.70, # WordStream 2025
    "note": (
        "Facebook 无钢卷/活动板房/二手机械/化工原料等对应类目，"
        "全部归入 Industrial & Commercial。本模块提供小类目调整系数作为辅助参考"
    ),
}

# ═══════════════════════════════════════════════════════════════════
# 小众工业品调整系数表
#
# 每个条目结构：
#   关键词列表 → {
#       ctr_factor, cpc_factor, cvr_factor, cpl_factor,
#       confidence, data_source, notes
#   }
# ═══════════════════════════════════════════════════════════════════
NICHE_INDUSTRIAL_ADJUSTMENTS: Dict[str, Dict[str, Any]] = {
    # ── 钢材/金属材料类 ──
    "钢材_金属材料": {
        "keywords": [
            "steel coils", "steel plates", "steel pipes", "rebar", "metal sheets",
            "aluminum", "copper", "galvanized steel", "stainless steel", "wire rod",
            "angle steel", "H-beam", "channel steel", "steel coil", "steel plate",
            "steel pipe", "steel tube", "steel bar", "steel sheet", "steel strip",
            "steel wire", "steel rod", "steel beam", "steel channel", "steel angle",
            "carbon steel", "alloy steel", "steel roll", "hot rolled", "cold rolled",
            "galvanized", "steel", "钢材", "钢板", "钢卷", "钢管", "钢筋",
            "铝材", "铜材", "不锈钢", "螺纹钢", "型钢", "角钢", "槽钢", "工字钢",
            "metal", "金属材料", "钢铁", "钢坯", "钢锭", "热轧", "冷轧",
        ],
        "ctr_factor": 0.88,
        "cpc_factor": 1.15,
        "cvr_factor": 0.75,
        "cpl_factor": 1.35,
        "confidence": "medium",
        "data_source": "Meta Business Suite 2024 + Statista 2025 + 10100.com 钢材行业分析",
        "notes": (
            "钢材类广告在 Facebook 可能触发 Meta 商业政策审核，禁止使用绝对化用语。"
            "素材需使用工厂实拍+产品参数，避免'最低价''唯一'等表述。"
        ),
    },

    # ── 二手工程机械类 ──
    "二手工程机械": {
        "keywords": [
            "used excavator", "used bulldozer", "used loader", "used crane",
            "used forklift", "used truck", "used tractor", "used drilling rig",
            "used mining equipment", "second-hand machinery", "construction equipment",
            "heavy machinery", "mining machine", "road roller", "grader",
            "concrete pump", "used generator", "excavator", "bulldozer", "loader",
            "crane", "forklift", "construction machinery", "heavy equipment",
            "mining equipment", "engineering machinery", "二手挖掘机", "二手装载机",
            "二手起重机", "二手叉车", "二手卡车", "二手拖拉机", "二手工程机械",
            "二手设备", "工程机械", "挖掘机", "装载机", "推土机", "起重机",
            "压路机", "平地机", "混凝土泵车", "钻机", "矿用设备",
        ],
        "ctr_factor": 0.74,
        "cpc_factor": 2.68,
        "cvr_factor": 1.05,
        "cpl_factor": 1.87,
        "confidence": "high",
        "data_source": (
            "10100.com 重工机械案例 + ceglobal.cn 工程机械案例"
            " + geeksend.com 2026 + 搜狐 巴西市场调查2026"
        ),
        "notes": (
            "⚠️ 高风险：直接推广大型设备易被 Facebook 判定为 low-quality traffic"
            " 导致账户冻结。必须使用软转化路径（白皮书下载/方案咨询/验厂视频）。"
            "建议长尾精细化关键词如 'used 3.5t mini excavator Japan spec'"
            " 替代泛词 'excavator'。CPC 降低 52%，CVR 提升 35%。"
        ),
    },

    # ── 预制房屋/活动板房 ──
    "预制房屋_活动板房": {
        "keywords": [
            "prefab house", "modular house", "container house", "portable cabin",
            "prefabricated building", "steel structure building", "light steel villa",
            "mobile home", "prefab office", "sandwich panel house", "temporary building",
            "demountable house", "portable toilet", "guard house", "kiosk",
            "prefab", "modular home", "container home", "prefabricated house",
            "modular building", "steel structure", "light steel villa", "mobile home",
            "活动板房", "预制房屋", "集装箱房", "模块化房屋", "移动房屋",
            "轻钢别墅", "钢结构厂房", "临时建筑", "可拆卸房屋", "预制板房",
            "集装箱宿舍", "活动房", "板房", "彩钢板房",
        ],
        "ctr_factor": 0.92,
        "cpc_factor": 1.10,
        "cvr_factor": 0.60,
        "cpl_factor": 1.25,
        "confidence": "medium",
        "data_source": (
            "10100.com 轻钢别墅与建材分析 + econelgroup.com"
            " + 思雨神器 移动房屋出海"
        ),
        "notes": (
            "Facebook 禁止直接销售建筑材料原材料，仅可用于引流至独立站或收集表单。"
            "需准备 ISO 认证和工厂实拍图。"
            "视觉素材（3D 模型/视频）可提升停留时长 42%。"
        ),
    },

    # ── 化工产品类 ──
    "化工产品": {
        "keywords": [
            "chemical products", "chemical raw materials", "industrial chemicals",
            "petrochemical", "polymer", "resin", "adhesive", "coating", "paint",
            "pigment", "solvent", "catalyst", "reagent", "additive", "lubricant",
            "surfactant", "fertilizer", "pesticide", "pharmaceutical intermediate",
            "cleaning chemical", "water treatment chemical", "rubber chemical",
            "plastic raw material", "silicone", "epoxy", "polyurethane",
            "titanium dioxide", "carbon black", "activated carbon",
            "chemical", "chemicals", "化工", "化学品", "化工原料", "工业化学品",
            "树脂", "涂料", "油漆", "颜料", "溶剂", "催化剂", "试剂", "添加剂",
            "润滑剂", "表面活性剂", "化肥", "农药", "医药中间体",
            "水处理化学品", "橡胶化学品", "塑料原料", "硅胶", "环氧树脂",
            "聚氨酯", "钛白粉", "炭黑", "活性炭",
        ],
        "ctr_factor": 0.82,
        "cpc_factor": 1.05,
        "cvr_factor": 0.70,
        "cpl_factor": 1.15,
        "confidence": "medium",
        "data_source": (
            "qiyoutuo.com 2026化工B2B推广评测 + wanzhiweb.com 2026外贸推广成本"
            " + Visionary 2026 Google Ads Report"
        ),
        "notes": (
            "化工产品广告审核严格，需提供 MSDS（安全数据表）和合规资质。"
            "部分品类（农药/危险品）可能完全禁止投放。"
        ),
    },

    # ── 大宗工业原料/设备类兜底 ──
    "大宗工业原料_设备_兜底": {
        "keywords": [
            "bulk commodities", "raw materials", "industrial equipment",
            "mining", "quarrying", "oil & gas equipment", "power generation",
            "transmission line", "transformer", "industrial boiler",
            "waste treatment", "recycling machine", "大宗原料", "工业原料",
            "工业设备", "矿山设备", "采石设备", "石油设备", "发电设备",
            "输电线路", "变压器", "工业锅炉", "废物处理", "回收设备",
            "bulk material", "raw material", "industrial machine", "mining machine",
        ],
        "ctr_factor": 0.80,
        "cpc_factor": 1.20,
        "cvr_factor": 0.75,
        "cpl_factor": 1.40,
        "confidence": "low",
        "data_source": (
            "基于共性规律推断 + WordStream 2025 Industrial avg"
            " + 10100.com 多品类交叉"
        ),
        "notes": (
            "未细分品类兜底值。建议在实际投放中通过 A/B 测试积累自有数据。"
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def match_niche_category(product_name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """对产品名做关键词匹配，返回命中的品类名和调整数据。

    Args:
        product_name: 产品名称（大小写不敏感）

    Returns:
        (category_name, adjustment_dict) 或 None
    """
    name_lower = product_name.lower().strip()
    best_match = None
    best_score = 0

    for cat_name, cat_data in NICHE_INDUSTRIAL_ADJUSTMENTS.items():
        if cat_name == "_META":
            continue
        keywords = cat_data.get("keywords", [])
        # 计算匹配得分：完全匹配 > 子串匹配
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower == name_lower:
                score = max(score, 100)  # 完全匹配最高优先级
            elif kw_lower in name_lower or name_lower in kw_lower:
                score = max(score, len(kw_lower))  # 子串匹配按长度打分
        if score > best_score:
            best_score = score
            best_match = (cat_name, cat_data)

    if best_match and best_score > 0:
        return best_match
    return None


def apply_niche_adjustment(
    product_name: str,
    baseline_ctr: float = 1.36,
    baseline_cpc: float = 0.86,
    baseline_cvr: float = 9.34,
    baseline_cpl: float = 37.34,
) -> Optional[Dict[str, Any]]:
    """对产品应用小众工业品调整系数，返回调整后的 KPI 值和元数据。

    Returns:
        {
            "applied": True,
            "category": "钢材_金属材料",
            "adjusted_ctr": ...,
            "adjusted_cpc": ...,
            "adjusted_cvr": ...,
            "adjusted_cpl": ...,
            "factors": {...},
            "confidence": "...",
            "data_source": "...",
            "notes": "...",
        }
        或 None（未命中）
    """
    result = match_niche_category(product_name)
    if result is None:
        return None

    cat_name, cat_data = result
    factors = {
        "ctr_factor": cat_data["ctr_factor"],
        "cpc_factor": cat_data["cpc_factor"],
        "cvr_factor": cat_data["cvr_factor"],
        "cpl_factor": cat_data["cpl_factor"],
    }

    return {
        "applied": True,
        "category": cat_name,
        "baseline_ctr": baseline_ctr,
        "baseline_cpc": baseline_cpc,
        "baseline_cvr": baseline_cvr,
        "baseline_cpl": baseline_cpl,
        "adjusted_ctr": round(baseline_ctr * cat_data["ctr_factor"], 4),
        "adjusted_cpc": round(baseline_cpc * cat_data["cpc_factor"], 4),
        "adjusted_cvr": round(baseline_cvr * cat_data["cvr_factor"], 4),
        "adjusted_cpl": round(baseline_cpl * cat_data["cpl_factor"], 2),
        "factors": factors,
        "confidence": cat_data["confidence"],
        "data_source": cat_data["data_source"],
        "notes": cat_data["notes"],
    }

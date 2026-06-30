#!/usr/bin/env python3
"""
通用多产品 Facebook 投流策略推荐工具
基于 facebook-ads-analyzer 开源核心逻辑
支持交互式输入 + 智能推断 + 批量对比

基准数据来源：
  - Digital Point LLC (2026), $48M Meta广告支出样本
  - AdBacklog (2025), 跨行业广告基准报告
交叉验证后取中位数，修正偏差。
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ── 小众工业品数据层（v3.5 新增） ──
try:
    from utils.niche_industrial_data import (
        NICHE_INDUSTRIAL_ADJUSTMENTS,
        apply_niche_adjustment,
        match_niche_category,
    )
    _NICHE_INDUSTRIAL_AVAILABLE = True
except ImportError:
    _NICHE_INDUSTRIAL_AVAILABLE = False
    NICHE_INDUSTRIAL_ADJUSTMENTS = {}
    def apply_niche_adjustment(*args, **kwargs): return None
    def match_niche_category(*args, **kwargs): return None

# ═══════════════════════════════════════════════════════════════════
# 0. 常量 — 行业基准数据库 (13 个行业)
#    新增 expected_ctr / expected_cpc / expected_cpa / expected_roas
#    取自 DigitalPoint(2026) 与 AdBacklog(2025) 交叉验证中位数
# ═══════════════════════════════════════════════════════════════════

INDUSTRY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "工业耗材": {
        "unit_price_usd": 3.50,
        "profit_margin_pct": 35.0,
        "target_market": "北美",
        "business_type": "B2B",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 21,
        "description": "砂纸/砂带/磨具/紧固件/密封件",
        "keywords": ["砂纸", "砂带", "砂轮", "磨具", "磨料", "研磨", "紧固件", "密封件", "螺丝", "螺母",
                     "螺栓", "垫圈", "铆钉", "弹簧", "轴承", "阀门", "法兰", "管件", "接头", "泵",
                     "五金", "机械", "模具", "铸件", "锻件", "冲压件", "机加工", "CNC", "刀具", "钻头",
                     "丝锥", "板牙", "量具", "卡尺", "千分尺"],
        # 权威数据: DigitalPoint HomeServices + AdBacklog HomeImprovement → 中位数
        "expected_ctr": 1.42,
        "expected_cpc": 1.05,
        "expected_cpa": 44.66,
        "expected_roas": 4.38,
    },
    "消费电子": {
        "unit_price_usd": 45.00,
        "profit_margin_pct": 22.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 5,
        "description": "耳机/充电器/智能穿戴/手机配件",
        "keywords": ["耳机", "充电器", "蓝牙", "智能穿戴", "手机壳", "手机配件", "数据线", "充电宝",
                     "移动电源", "屏幕", "电路板", "PCB", "芯片", "传感器", "扬声器", "麦克风",
                     "摄像头", "电子", "数码", "平板", "笔记本"],
        # DigitalPoint E-commerce + AdBacklog Technology
        "expected_ctr": 1.59,
        "expected_cpc": 0.97,
        "expected_cpa": 55.21,
        "expected_roas": 3.42,
    },
    "服装配饰": {
        "unit_price_usd": 28.00,
        "profit_margin_pct": 55.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 3,
        "description": "服装/鞋帽/箱包/珠宝首饰",
        "keywords": ["服装", "衣服", "T恤", "衬衫", "裤子", "裙子", "外套", "夹克", "羽绒服",
                     "鞋", "运动鞋", "皮鞋", "靴子", "帽", "帽子", "箱包", "背包", "手提包",
                     "珠宝", "首饰", "项链", "手链", "戒指", "耳环", "袜子", "内衣"],
        # DigitalPoint Apparel + AdBacklog Apparel → 中位数
        "expected_ctr": 1.51,
        "expected_cpc": 0.85,
        "expected_cpa": 10.98,
        "expected_roas": 3.68,
    },
    "家居用品": {
        "unit_price_usd": 35.00,
        "profit_margin_pct": 40.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成熟期",
        "expected_conversion_days": 7,
        "description": "厨具/收纳/家纺/装饰品/灯具",
        "keywords": ["厨具", "锅", "刀", "砧板", "收纳", "储物", "家纺", "床上用品", "床单", "被套",
                     "装饰品", "摆件", "灯具", "台灯", "吊灯", "LED", "家具", "床", "沙发",
                     "桌子", "椅子", "窗帘", "地毯", "抱枕", "相框", "花瓶"],
        # DigitalPoint HomeServices + AdBacklog HomeImprovement → 中位数
        "expected_ctr": 1.29,
        "expected_cpc": 1.21,
        "expected_cpa": 44.66,
        "expected_roas": 4.38,
    },
    "美妆护肤": {
        "unit_price_usd": 22.00,
        "profit_margin_pct": 60.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 4,
        "description": "护肤品/彩妆/美发/香水/个人护理",
        "keywords": ["护肤", "面霜", "精华", "乳液", "化妆水", "面膜", "彩妆", "口红", "唇膏",
                     "粉底", "眼影", "眉笔", "美发", "洗发水", "护发素", "香水", "洗面奶",
                     "防晒", "BB霜", "CC霜", "卸妆", "美容", "美甲"],
        # AdBacklog Beauty (DigitalPoint 无直接对应)
        "expected_ctr": 1.51,
        "expected_cpc": 0.94,
        "expected_cpa": 25.49,
        "expected_roas": None,
    },
    "食品饮料": {
        "unit_price_usd": 15.00,
        "profit_margin_pct": 30.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 3,
        "description": "零食/饮品/保健食品/调味品",
        "keywords": ["零食", "薯片", "坚果", "糖果", "巧克力", "饼干", "饮品", "饮料", "果汁",
                     "茶叶", "茶", "咖啡", "保健食品", "蛋白粉", "维生素", "调味品", "酱油",
                     "醋", "酱料", "蜂蜜", "果酱", "方便面", "速食"],
        # AdBacklog Retail (DigitalPoint 无直接对应)
        "expected_ctr": 1.67,
        "expected_cpc": 0.68,
        "expected_cpa": 21.47,
        "expected_roas": None,
    },
    "运动户外": {
        "unit_price_usd": 55.00,
        "profit_margin_pct": 38.0,
        "target_market": "欧洲",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 6,
        "description": "健身器材/露营装备/骑行/瑜伽/钓鱼",
        "keywords": ["健身", "哑铃", "跑步机", "瑜伽", "瑜伽垫", "露营", "帐篷", "睡袋", "登山",
                     "户外", "骑行", "自行车", "钓鱼", "鱼竿", "运动", "球类", "篮球",
                     "足球", "羽毛球", "滑雪", "潜水", "冲浪", "滑板"],
        # DigitalPoint Fitness + AdBacklog Health/Fitness → 中位数
        "expected_ctr": 1.57,
        "expected_cpc": 1.05,
        "expected_cpa": 13.29,
        "expected_roas": 2.89,
    },
    "教育培训": {
        "unit_price_usd": 120.00,
        "profit_margin_pct": 65.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "新品",
        "expected_conversion_days": 14,
        "description": "在线课程/职业培训/语言学习/考试辅导",
        "keywords": ["课程", "培训", "在线教育", "网课", "语言学习", "英语", "考试辅导",
                     "职业培训", "认证", "教育", "教学", "教程", "辅导", "考研", "留学"],
        # DigitalPoint Education + AdBacklog Education → 中位数
        "expected_ctr": 1.32,
        "expected_cpc": 0.95,
        "expected_cpa": 7.85,
        "expected_roas": 2.94,
    },
    "软件SaaS": {
        "unit_price_usd": 99.00,
        "profit_margin_pct": 75.0,
        "target_market": "北美",
        "business_type": "B2B",
        "lifecycle_stage": "新品",
        "expected_conversion_days": 21,
        "description": "SaaS订阅/工具软件/云服务/API",
        "keywords": ["SaaS", "软件", "云服务", "API", "订阅", "平台", "系统", "CRM", "ERP",
                     "工具软件", "插件", "App", "小程序", "自动化", "数据分析", "AI"],
        # DigitalPoint SaaS + AdBacklog B2B → 中位数
        "expected_ctr": 1.05,
        "expected_cpc": 1.49,
        "expected_cpa": 23.77,
        "expected_roas": 2.18,
    },
    "医疗器械": {
        "unit_price_usd": 120.0,
        "profit_margin_pct": 35.0,
        "target_market": "北美",
        "business_type": "B2B",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 30,
        "description": "口罩/手套/血压计/轮椅/导管/手术器械等医疗用品",
        "keywords": ["诊断", "医疗", "手术", "试剂", "检测", "超声", "监护仪", "注射器",
                     "口罩", "防护", "消毒", "灭菌", "康复", "假肢", "矫形", "牙科",
                     "眼科", "实验室", "生化", "离心机", "移液器", "培养皿",
                     "手套", "血压计", "轮椅", "导管", "病床", "听诊器", "输液器",
                     "血糖仪", "体温计", "心电图", "X光"],
        "expected_ctr": 1.52,
        "expected_cpc": 1.35,
        "expected_cpa": 48.0,
        "expected_roas": 3.50,
    },
    "母婴用品": {
        "unit_price_usd": 25.00,
        "profit_margin_pct": 42.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 4,
        "description": "婴儿用品/玩具/孕妇装/儿童教育",
        "keywords": ["婴儿", "宝宝", "奶瓶", "尿布", "奶粉", "推车", "婴儿车", "玩具",
                     "积木", "娃娃", "孕妇", "孕期", "儿童", "童装", "童鞋", "早教"],
        # AdBacklog Retail (DigitalPoint 无直接对应)
        "expected_ctr": 1.67,
        "expected_cpc": 0.68,
        "expected_cpa": 21.47,
        "expected_roas": None,
    },
    "宠物用品": {
        "unit_price_usd": 20.00,
        "profit_margin_pct": 45.0,
        "target_market": "北美",
        "business_type": "B2C",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 3,
        "description": "宠物食品/玩具/窝垫/美容护理",
        "keywords": ["宠物", "猫", "狗", "猫粮", "狗粮", "宠物食品", "宠物玩具", "猫砂",
                     "狗窝", "猫爬架", "牵引绳", "项圈", "宠物美容", "水族", "鱼缸"],
        # AdBacklog Retail (DigitalPoint 无直接对应)
        "expected_ctr": 1.67,
        "expected_cpc": 0.68,
        "expected_cpa": 21.47,
        "expected_roas": None,
    },
    "汽车配件": {
        "unit_price_usd": 80.00,
        "profit_margin_pct": 30.0,
        "target_market": "欧洲",
        "business_type": "B2C",
        "lifecycle_stage": "成熟期",
        "expected_conversion_days": 10,
        "description": "车载电子/内外饰/保养用品/改装件",
        "keywords": ["汽车", "车载", "车灯", "刹车", "轮胎", "发动机", "润滑油", "机油",
                     "滤清器", "火花塞", "雨刷", "内饰", "外饰", "改装", "车贴",
                     "导航", "行车记录仪", "倒车影像", "充电桩", "电瓶", "蓄电池"],
        # DigitalPoint Automotive + AdBacklog Automotive → 中位数
        "expected_ctr": 0.99,
        "expected_cpc": 1.55,
        "expected_cpa": 43.84,
        "expected_roas": 3.14,
    },
    "工业电子": {
        "unit_price_usd": 25.0,
        "profit_margin_pct": 25.0,
        "target_market": "北美",
        "business_type": "B2B",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 14,
        "description": "PCB/显示屏/连接器/电源模块等工业电子产品",
        "keywords": ["工业电子", "PCB", "电路板", "显示屏", "连接器", "散热器", "电源模块",
                     "电子元器件", "防雷器", "端子", "排针", "排母", "电缆接头",
                     "工业显示器", "工控屏", "触摸屏", "LED驱动", "电源适配器",
                     "继电器", "接触器", "断路器", "熔断器", "开关电源"],
        "expected_ctr": 1.45,
        "expected_cpc": 1.15,
        "expected_cpa": 42.0,
        "expected_roas": 3.85,
    },
    "其他工业品": {
        "unit_price_usd": 15.00,
        "profit_margin_pct": 32.0,
        "target_market": "北美",
        "business_type": "B2B",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 25,
        "description": "其他未分类的工业B2B产品（取工业耗材/汽车配件中位数）",
        "keywords": ["工业", "工厂", "制造", "设备", "机器", "生产线", "原材料", "钢材",
                     "铜", "铝", "塑料", "橡胶", "化工", "化学", "纤维", "玻璃",
                     "陶瓷", "粉末", "冶金", "焊接", "喷涂", "电镀", "热处理"],
        "expected_ctr": 1.14,
        "expected_cpc": 1.38,
        "expected_cpa": 44.25,
        "expected_roas": 3.76,
    },
}

# ═══════════════════════════════════════════════════════════════════
# "其他工业品" 子类映射表
# ═══════════════════════════════════════════════════════════════════
# 当 SmartInferrer 无法匹配到具体行业时，产品会兜底到"其他工业品"。
# 本表对"其他工业品"做二次细分，使同类产品获得差异化基准数据。
#
# 字段说明：
#   keywords          — 子类关键词，用于匹配产品名
#   unit_price_usd    — 建议客单价 (USD)
#   profit_margin_pct — 建议利润率 (%)
#   lifecycle_stage   — 生命周期（导入期/成长期/成熟期/衰退期）
#   conversion_days   — 预期转化周期（天）
#   ctr_factor       — CTR 相对"其他工业品"基准的调整系数（乘性）
#   cpc_factor       — CPC 调整系数
#   cpa_factor       — CPA 调整系数
#   price_tier        — 单价档位：low / medium / high
#   decision_cycle    — 决策周期：short(≤7d) / medium(8-30d) / long(>30d)
#   repurchase_freq   — 复购频率：low / medium / high
#   audience_overlay  — 受众补充词（追加到基础 B2B 受众后）
#   confidence_base   — 本子类的默认可信度（因有细分数据，高于兜底）
# ────────────────────────────────────────────────────────────────────
INDUSTRIAL_SUBCATEGORIES: Dict[str, Dict[str, Any]] = {
    "流体设备": {
        "keywords": ["阀门", "阀", "管件", "管道", "泵", "法兰", "接头", "水龙头",
                     "水管", "油管", "气管", "液压", "气动", "密封", "流量计",
                     "过滤器", "减压阀", "止回阀", "球阀", "闸阀", "蝶阀",
                     "valve", "pump", "flange", "pipe", "fitting", "hydraulic",
                     "pneumatic", "flow meter", "filter", "centrifugal pump",
                     "check valve", "butterfly valve", "ball valve", "gate valve"],
        "unit_price_usd": 120.0,
        "profit_margin_pct": 28.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 18,
        "ctr_factor": 1.23,
        "cpc_factor": 0.80,
        "cpa_factor": 1.15,
        "price_tier": "medium",
        "decision_cycle": "medium",
        "repurchase_freq": "medium",
        "audience_overlay": ["工厂经理", "设备采购", "维护工程师", "流体系统设计师"],
        "confidence_base": "中",
    },
    "机械传动": {
        "keywords": ["轴承", "齿轮", "传动", "联轴器", "链轮", "皮带", "链条",
                     "减速机", "变速器", "离合器", "刹车片", "导轨", "滑块",
                     "丝杆", "螺母", "线性模组",
                     "bearing", "gear", "coupling", "sprocket", "belt", "chain",
                     "reducer", "gearbox", "clutch", "brake", "linear guide",
                     "ball screw", "lead screw", "roller bearing", "ball bearing"],
        "unit_price_usd": 45.0,
        "profit_margin_pct": 35.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 12,
        "ctr_factor": 1.21,
        "cpc_factor": 0.81,
        "cpa_factor": 0.85,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "high",
        "audience_overlay": ["机械工程师", "采购专员", "设备维护", "生产主管"],
        "confidence_base": "中",
    },
    "工业自动化": {
        "keywords": ["传感器", "仪表", "控制器", "PLC", "变频器", "伺服",
                     "编码器", "开关", "继电器", "触摸屏", "工控机", "SCADA",
                     "DCS", "变送器", "温度计", "压力传感器", "光电",
                     "sensor", "controller", "PLC", "VFD", "servo", "encoder",
                     "transmitter", "HMI", "relay", "actuator", "thermocouple",
                     "proximity sensor", "pressure transducer", "flow transmitter"],
        "unit_price_usd": 280.0,
        "profit_margin_pct": 40.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 30,
        "ctr_factor": 0.85,
        "cpc_factor": 1.15,
        "cpa_factor": 1.35,
        "price_tier": "high",
        "decision_cycle": "long",
        "repurchase_freq": "low",
        "audience_overlay": ["自动化工程师", "技术总监", "系统集成商", "电气工程师"],
        "confidence_base": "中高",
    },
    "工业耗材": {
        "keywords": ["紧固件", "密封件", "螺丝", "螺栓", "螺母", "垫圈",
                     "密封圈", "O型圈", "焊条", "砂轮", "切削液", "润滑油",
                     "润滑脂", "胶带", "扎带", "标签", "包装材料",
                     "fastener", "screw", "bolt", "nut", "washer", "seal",
                     "o-ring", "gasket", "lubricant", "grease", "adhesive",
                     "cutting fluid", "grinding wheel", "welding rod"],
        "unit_price_usd": 8.0,
        "profit_margin_pct": 25.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 7,
        "ctr_factor": 1.15,
        "cpc_factor": 0.85,
        "cpa_factor": 0.70,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "high",
        "audience_overlay": ["采购经理", "供应链管理", "生产主管", "仓储管理"],
        "confidence_base": "中低",
    },
    "电力设备": {
        "keywords": ["电机", "发电机", "变压器", "电缆", "开关柜", "断路器",
                     "马达", "变频器", "配电箱", "电缆桥架", "绝缘子", "电抗器",
                     "电容器", "蓄电池", "太阳能板", "逆变器",
                     "motor", "generator", "transformer", "cable", "switchgear",
                     "circuit breaker", "distribution box", "insulator", "capacitor",
                     "battery", "solar panel", "inverter", "electric motor"],
        "unit_price_usd": 350.0,
        "profit_margin_pct": 22.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 35,
        "ctr_factor": 0.80,
        "cpc_factor": 1.20,
        "cpa_factor": 1.45,
        "price_tier": "high",
        "decision_cycle": "long",
        "repurchase_freq": "low",
        "audience_overlay": ["电气工程师", "能源经理", "项目承包商", "设备采购"],
        "confidence_base": "中",
    },
    "工业化学品": {
        "keywords": ["化学品", "化学", "涂料", "油漆", "漆", "润滑油", "润滑脂",
                     "清洗剂", "溶剂", "胶粘剂", "密封胶", "树脂", "催化剂",
                     "添加剂", "表面处理", "电镀", "防锈", "脱脂", "阻燃",
                     "chemical", "coating", "paint", "lubricant", "solvent",
                     "adhesive", "resin", "catalyst", "additive", "rust inhibitor",
                     "electroplating", "sealant", "cleaner", "degreaser", "epoxy",
                     "flame retardant", "pigment", "primer"],
        "unit_price_usd": 55.0,
        "profit_margin_pct": 32.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 15,
        "ctr_factor": 0.90,
        "cpc_factor": 1.10,
        "cpa_factor": 1.10,
        "price_tier": "medium",
        "decision_cycle": "medium",
        "repurchase_freq": "high",
        "audience_overlay": ["化工厂采购", "实验室经理", "表面处理工程师", "涂料经销商"],
        "confidence_base": "中",
    },
    "包装材料": {
        "keywords": ["包装", "纸箱", "塑料袋", "气泡膜", "缠绕膜", "打包带",
                     "托盘", "木箱", "标签", "胶带", "缓冲材料", "泡沫",
                     "纸板", "容器", "瓶", "罐",
                     "packaging", "carton", "box", "plastic bag", "bubble wrap",
                     "stretch film", "pallet", "label", "tape", "foam",
                     "container", "bottle", "jar", "corrugated", "strapping"],
        "unit_price_usd": 3.0,
        "profit_margin_pct": 20.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 5,
        "ctr_factor": 1.20,
        "cpc_factor": 0.80,
        "cpa_factor": 0.60,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "high",
        "audience_overlay": ["包装采购", "物流经理", "电商运营", "食品厂采购"],
        "confidence_base": "中低",
    },
    "建筑材料": {
        "keywords": ["建筑材料", "水泥", "砖", "钢筋", "混凝土", "玻璃",
                     "瓷砖", "地板", "石材", "石膏板", "涂料", "防水材料",
                     "保温材料", "管道", "门窗", "铝材",
                     "construction", "cement", "brick", "concrete", "rebar",
                     "glass", "tile", "stone", "drywall", "insulation",
                     "waterproofing", "door", "window", "aluminum profile", "steel beam"],
        "unit_price_usd": 80.0,
        "profit_margin_pct": 18.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 25,
        "ctr_factor": 0.85,
        "cpc_factor": 1.05,
        "cpa_factor": 1.20,
        "price_tier": "medium",
        "decision_cycle": "medium",
        "repurchase_freq": "medium",
        "audience_overlay": ["建筑承包商", "项目经理", "建材经销商", "房地产开发商"],
        "confidence_base": "中",
    },
    "五金工具": {
        "keywords": ["五金", "工具", "扳手", "螺丝刀", "钳子", "锤子",
                     "电钻", "冲击钻", "钻头", "钻", "锯", "量具", "卷尺",
                     "手工具", "电动工具", "工具箱", "套筒", "锉刀", "千斤顶",
                     "tool", "wrench", "screwdriver", "pliers", "hammer",
                     "drill", "saw", "measure", "tape measure", "power tool",
                     "hand tool", "socket", "file", "jack", "cutter", "impact drill"],
        "unit_price_usd": 25.0,
        "profit_margin_pct": 30.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 8,
        "ctr_factor": 1.10,
        "cpc_factor": 0.90,
        "cpa_factor": 0.80,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "medium",
        "audience_overlay": ["维修技工", "工具经销商", "DIY爱好者", "车间主管"],
        "confidence_base": "中",
    },
    "安全防护": {
        "keywords": ["安全", "防护", "头盔", "安全帽", "手套", "口罩",
                     "防护服", "护目镜", "安全带", "劳保", "防毒面具",
                     "耳塞", "安全鞋", "反光背心", "消防器材", "灭火器",
                     "safety", "protection", "helmet", "glove", "mask",
                     "respirator", "goggle", "harness", "PPE", "earplug",
                     "safety shoe", "reflective vest", "fire extinguisher", "gas mask"],
        "unit_price_usd": 12.0,
        "profit_margin_pct": 35.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 10,
        "ctr_factor": 1.10,
        "cpc_factor": 0.90,
        "cpa_factor": 0.75,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "high",
        "audience_overlay": ["安全主管", "EHS经理", "劳保采购", "建筑安全员"],
        "confidence_base": "中",
    },
    "物流仓储": {
        "keywords": ["物流", "仓储", "货架", "叉车", "托盘", "堆垛机",
                     "输送机", "分拣机", "周转箱", "手推车", "升降平台",
                     "AGV", "仓库", "搬运车", "集装箱", "物流设备",
                     "传送带", "输送带",
                     "logistics", "warehouse", "racking", "forklift", "pallet",
                     "conveyor", "sorter", "trolley", "lift", "AGV",
                     "container", "stacker", "cart", "shelving", "dock",
                     "conveyor belt", "belt conveyor", "belt"],
        "unit_price_usd": 500.0,
        "profit_margin_pct": 25.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 30,
        "ctr_factor": 0.88,
        "cpc_factor": 1.08,
        "cpa_factor": 1.25,
        "price_tier": "high",
        "decision_cycle": "long",
        "repurchase_freq": "low",
        "audience_overlay": ["仓储经理", "物流总监", "供应链总监", "电商仓储管理"],
        "confidence_base": "中",
    },
    "环保设备": {
        "keywords": ["环保", "过滤", "净化", "除尘", "污水处理", "废气",
                     "固废", "水处理", "脱硫", "脱硝", "活性炭", "膜",
                     "垃圾处理", "回收", "空气净化",
                     "environmental", "filter", "purification", "dust collector",
                     "wastewater", "air pollution", "water treatment", "scrubber",
                     "activated carbon", "membrane", "desulfurization", "recycling"],
        "unit_price_usd": 2000.0,
        "profit_margin_pct": 30.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 45,
        "ctr_factor": 0.75,
        "cpc_factor": 1.25,
        "cpa_factor": 1.50,
        "price_tier": "high",
        "decision_cycle": "long",
        "repurchase_freq": "low",
        "audience_overlay": ["环保工程师", "政府环保部门", "工厂环保负责人", "EPC总包商"],
        "confidence_base": "中高",
    },
    "橡塑制品": {
        "keywords": ["橡胶", "塑料", "密封条", "胶管", "垫片", "O型圈",
                     "硅胶", "氟橡胶", "聚氨酯", "尼龙", "扎带", "注塑", "挤塑",
                     "软管", "密封件", "减震", "塑料件", "工程塑料",
                     "rubber", "plastic", "seal", "gasket", "o-ring",
                     "silicone", "hose", "polyurethane", "nylon", "injection molding",
                     "cable tie", "tie", "zip tie",
                     "extrusion", "bushing", "diaphragm", "elastomer", "PTFE"],
        "unit_price_usd": 5.0,
        "profit_margin_pct": 28.0,
        "lifecycle_stage": "成熟期",
        "conversion_days": 10,
        "ctr_factor": 1.05,
        "cpc_factor": 0.92,
        "cpa_factor": 0.85,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "high",
        "audience_overlay": ["橡胶制品采购", "汽车零部件采购", "模具工程师", "密封件经销商"],
        "confidence_base": "中",
    },
    "制冷暖通": {
        "keywords": ["制冷", "暖通", "空调", "压缩机", "冷凝器", "蒸发器",
                     "热交换器", "风机", "冷却塔", "冷媒", "通风", "供暖",
                     "HVAC", "制冷剂", "冷水机", "热泵",
                     "HVAC", "refrigeration", "air conditioning", "compressor",
                     "condenser", "evaporator", "heat exchanger", "fan", "cooling tower",
                     "chiller", "heat pump", "refrigerant", "thermostat", "AHU"],
        "unit_price_usd": 650.0,
        "profit_margin_pct": 28.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 28,
        "ctr_factor": 0.88,
        "cpc_factor": 1.08,
        "cpa_factor": 1.25,
        "price_tier": "high",
        "decision_cycle": "medium",
        "repurchase_freq": "low",
        "audience_overlay": ["暖通工程师", "建筑设备采购", "制冷设备经销商", "设施管理"],
        "confidence_base": "中",
    },

    "工业电子": {
        "keywords": ["工业电子", "显示屏", "PCB", "电路板", "散热器", "连接器", "电子元器件",
                     "电缆接头", "电源模块", "防雷器", "端子", "排针", "排母",
                     "display", "PCB board", "heat sink", "connector", "power module",
                     "surge protector", "terminal block", "electronic component",
                     "industrial display", "circuit board", "SPD", "wiring"],
        "unit_price_usd": 25.0,
        "profit_margin_pct": 25.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 14,
        "ctr_factor": 1.10,
        "cpc_factor": 0.88,
        "cpa_factor": 0.90,
        "price_tier": "low",
        "decision_cycle": "short",
        "repurchase_freq": "high",
        "audience_overlay": ["电子工程师", "采购专员", "EMS工厂", "产品设计师"],
        "confidence_base": "中",
    },
    "医疗器械": {
        "keywords": ["医疗", "口罩", "手套", "血压计", "轮椅", "导管", "手术器械",
                     "病床", "听诊器", "注射器", "输液器", "医用", "诊断", "康复",
                     "medical", "mask", "glove", "blood pressure", "wheelchair",
                     "catheter", "surgical", "hospital bed", "stethoscope", "syringe",
                     "infusion", "diagnostic", "rehabilitation", "PPE medical"],
        "unit_price_usd": 120.0,
        "profit_margin_pct": 35.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 30,
        "ctr_factor": 0.95,
        "cpc_factor": 1.02,
        "cpa_factor": 1.05,
        "price_tier": "medium",
        "decision_cycle": "medium",
        "repurchase_freq": "medium",
        "audience_overlay": ["医院采购", "医疗经销商", "诊所管理者", "康复中心"],
        "confidence_base": "中",
    },
    "通用工业": {
        # 未匹配到上述任何子类时的兜底（仍比完全无匹配好）
        "keywords": [],
        "unit_price_usd": 25.0,
        "profit_margin_pct": 30.0,
        "lifecycle_stage": "成长期",
        "conversion_days": 20,
        "ctr_factor": 1.0,
        "cpc_factor": 1.0,
        "cpa_factor": 1.0,
        "price_tier": "medium",
        "decision_cycle": "medium",
        "repurchase_freq": "medium",
        "audience_overlay": ["采购专员", "工程师", "工厂管理"],
        "confidence_base": "低",
    },
}


def match_industrial_subcategory(product_name: str) -> Tuple[str, int]:
    """在"其他工业品"分类内做关键词匹配，返回 (子类名, 命中数)。

    匹配策略（三层）：
    1. 精确关键词匹配（中文 + 英文，不分大小写）
    2. 关键词拆分 + 部分匹配（对包含 3+ 字符的输入，拆分后进行子串命中）
    3. 仍未命中 -> ("通用工业", 0)
    """
    name_lower = product_name.lower().strip()
    best_match = "通用工业"
    best_count = 0

    # ── 第 1 层：精确关键词匹配（子类关键词直接命中） ──
    for subcat, cfg in INDUSTRIAL_SUBCATEGORIES.items():
        if subcat == "通用工业":
            continue
        kw_list = cfg.get("keywords", [])
        hits = sum(1 for kw in kw_list if kw.lower() in name_lower)
        if hits > best_count:
            best_count = hits
            best_match = subcat

    if best_count > 0:
        return best_match, best_count

    # ── 第 2 层：关键词拆分 + 部分匹配（模糊兜底） ──
    # 将产品名按常见分隔符拆分，每段至少 2 个字符，逐一与子类关键词做子串匹配
    segments = re.split(r'[\s\-_/，,、·]+', product_name.strip())
    segments = [s.lower() for s in segments if len(s) >= 2]

    if segments:
        for subcat, cfg in INDUSTRIAL_SUBCATEGORIES.items():
            if subcat == "通用工业":
                continue
            kw_list = cfg.get("keywords", [])
            seg_hits = 0
            for seg in segments:
                for kw in kw_list:
                    kw_lower = kw.lower()
                    # 双向子串：输入片段包含关键词 或 关键词包含输入片段
                    if seg in kw_lower or kw_lower in seg:
                        seg_hits += 1
                        break
            if seg_hits > best_count:
                best_count = seg_hits
                best_match = subcat

    return best_match, best_count


# ═══════════════════════════════════════════════════════════════════
# 产品价格参考表 — 细粒度产品 → 价格范围映射
# 基于 AliBaba / Made-in-China / GlobalSources 等 B2B 平台市场数据
# 当子类匹配后，再按具体产品名做末级查表，获得更精准的单价区间
# ═══════════════════════════════════════════════════════════════════
PRODUCT_PRICE_REFERENCE: Dict[str, Dict[str, Any]] = {
    # ── 流体设备（16 种） ──
    "球阀":    {"unit_price_low": 20,  "unit_price_high": 80,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "闸阀":    {"unit_price_low": 50,  "unit_price_high": 200, "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "蝶阀":    {"unit_price_low": 50,  "unit_price_high": 300, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "止回阀":  {"unit_price_low": 15,  "unit_price_high": 60,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "不锈钢法兰": {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "离心泵":  {"unit_price_low": 500, "unit_price_high": 5000,"margin_pct": 20, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "水泵":    {"unit_price_low": 200, "unit_price_high": 2000,"margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "液压泵":  {"unit_price_low": 300, "unit_price_high": 3000,"margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "气动阀":  {"unit_price_low": 30,  "unit_price_high": 150, "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "不锈钢管": {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "减压阀":  {"unit_price_low": 25,  "unit_price_high": 120, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "流量计":  {"unit_price_low": 80,  "unit_price_high": 800, "margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "过滤器":  {"unit_price_low": 15,  "unit_price_high": 200, "margin_pct": 26, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "管接头":  {"unit_price_low": 2,   "unit_price_high": 20,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "磁力泵":  {"unit_price_low": 400, "unit_price_high": 4000,"margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "隔膜阀":  {"unit_price_low": 40,  "unit_price_high": 250, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # 流体设备追加（2026-06 扩展）
    "安全阀":  {"unit_price_low": 60,  "unit_price_high": 500, "margin_pct": 28, "source": "Global Sources 2026 B2B benchmark", "updated": "2026-06"},
    "电动蝶阀": {"unit_price_low": 100, "unit_price_high": 800, "margin_pct": 30, "source": "Global Sources 2026 B2B benchmark", "updated": "2026-06"},
    "气动球阀": {"unit_price_low": 40,  "unit_price_high": 200, "margin_pct": 28, "source": "Global Sources 2026 B2B benchmark", "updated": "2026-06"},
    "齿轮泵":  {"unit_price_low": 300, "unit_price_high": 3000,"margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "隔膜泵":  {"unit_price_low": 200, "unit_price_high": 2000,"margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "真空泵":  {"unit_price_low": 150, "unit_price_high": 3000,"margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "旋塞阀":  {"unit_price_low": 25,  "unit_price_high": 150, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "排污阀":  {"unit_price_low": 20,  "unit_price_high": 100, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "液位计":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "压力表":  {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 机械传动（16 种） ──
    "轴承":    {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "深沟球轴承": {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "齿轮":    {"unit_price_low": 10,  "unit_price_high": 200, "margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "滚珠丝杆": {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "联轴器":  {"unit_price_low": 8,   "unit_price_high": 80,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "减速机":  {"unit_price_low": 100, "unit_price_high": 2000,"margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "链条":    {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "同步带":  {"unit_price_low": 3,   "unit_price_high": 25,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "直线导轨": {"unit_price_low": 20,  "unit_price_high": 200, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "链轮":    {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "离合器":  {"unit_price_low": 30,  "unit_price_high": 300, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "锥齿轮":  {"unit_price_low": 15,  "unit_price_high": 150, "margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "滚针轴承": {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "蜗轮蜗杆": {"unit_price_low": 40,  "unit_price_high": 400, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "皮带轮":  {"unit_price_low": 8,   "unit_price_high": 80,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "线性模组": {"unit_price_low": 100, "unit_price_high": 1000,"margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 机械传动追加（2026-06 扩展）
    "圆锥滚子轴承": {"unit_price_low": 5,   "unit_price_high": 80,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "推力轴承":   {"unit_price_low": 8,   "unit_price_high": 100, "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "花键轴":    {"unit_price_low": 15,  "unit_price_high": 150, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "齿条":     {"unit_price_low": 20,  "unit_price_high": 200, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "万向节":    {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "同步轮":    {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "胀紧套":    {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "扭力限制器":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 工业自动化（15 种） ──
    "传感器":  {"unit_price_low": 20,  "unit_price_high": 500, "margin_pct": 40, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "温度传感器": {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 38, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "压力传感器": {"unit_price_low": 30,  "unit_price_high": 300, "margin_pct": 40, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "PLC控制器": {"unit_price_low": 100, "unit_price_high": 2000,"margin_pct": 42, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "变频器":  {"unit_price_low": 80,  "unit_price_high": 1500,"margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "触摸屏":  {"unit_price_low": 50,  "unit_price_high": 800, "margin_pct": 38, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "伺服电机": {"unit_price_low": 200, "unit_price_high": 3000,"margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "编码器":  {"unit_price_low": 30,  "unit_price_high": 500, "margin_pct": 40, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "光电开关": {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "继电器":  {"unit_price_low": 1,   "unit_price_high": 15,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "接近开关": {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "温度变送器": {"unit_price_low": 20,  "unit_price_high": 200, "margin_pct": 38, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "工控机":  {"unit_price_low": 300, "unit_price_high": 3000,"margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "电磁阀":  {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "步进电机": {"unit_price_low": 15,  "unit_price_high": 200, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 工业自动化追加（2026-06 扩展）
    "液位传感器":  {"unit_price_low": 30,  "unit_price_high": 300, "margin_pct": 38, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "流量传感器":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 40, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "伺服驱动器":  {"unit_price_low": 150, "unit_price_high": 2000,"margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "工业机器人手臂": {"unit_price_low": 3000,"unit_price_high": 30000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "开关电源":    {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "温度控制器":  {"unit_price_low": 15,  "unit_price_high": 150, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "时间继电器":  {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "工业交换机":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 工业耗材（15 种） ──
    "螺丝":    {"unit_price_low": 0.01,"unit_price_high": 0.5, "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "不锈钢螺丝": {"unit_price_low": 0.02,"unit_price_high": 1.0, "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "螺栓":    {"unit_price_low": 0.05,"unit_price_high": 3.0, "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "密封圈":  {"unit_price_low": 0.05,"unit_price_high": 2.0, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "O型圈":   {"unit_price_low": 0.01,"unit_price_high": 0.5, "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "焊条":    {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "砂轮":    {"unit_price_low": 1,   "unit_price_high": 20,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "切削液":  {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "扎带":    {"unit_price_low": 0.01,"unit_price_high": 0.1, "margin_pct": 15, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "垫圈":    {"unit_price_low": 0.01,"unit_price_high": 0.3, "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "弹簧垫圈": {"unit_price_low": 0.02,"unit_price_high": 0.5, "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "工业胶带": {"unit_price_low": 1,   "unit_price_high": 10,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "润滑脂":  {"unit_price_low": 3,   "unit_price_high": 25,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "自攻螺丝": {"unit_price_low": 0.01,"unit_price_high": 0.3, "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "铜焊条":  {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 电力设备（15 种） ──
    "电机":    {"unit_price_low": 50,  "unit_price_high": 2000,"margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "三相异步电机": {"unit_price_low": 100, "unit_price_high": 5000,"margin_pct": 20, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "发电机":  {"unit_price_low": 500, "unit_price_high": 20000,"margin_pct": 18,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "变压器":  {"unit_price_low": 100, "unit_price_high": 10000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "电缆":    {"unit_price_low": 1,   "unit_price_high": 50,  "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "开关柜":  {"unit_price_low": 500, "unit_price_high": 8000,"margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "断路器":  {"unit_price_low": 5,   "unit_price_high": 200, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "太阳能板": {"unit_price_low": 80,  "unit_price_high": 500, "margin_pct": 15, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "逆变器":  {"unit_price_low": 50,  "unit_price_high": 2000,"margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "配电箱":  {"unit_price_low": 30,  "unit_price_high": 500, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "电缆桥架": {"unit_price_low": 5,   "unit_price_high": 40,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "绝缘子":  {"unit_price_low": 0.5, "unit_price_high": 15,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "电抗器":  {"unit_price_low": 50,  "unit_price_high": 800, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "高压电缆": {"unit_price_low": 10,  "unit_price_high": 200, "margin_pct": 20, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "蓄电池":  {"unit_price_low": 20,  "unit_price_high": 300, "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # 电力设备追加（2026-06 扩展）
    "柴油发电机":   {"unit_price_low": 2000,"unit_price_high": 50000,"margin_pct": 15,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "风力发电机":   {"unit_price_low": 3000,"unit_price_high": 50000,"margin_pct": 20,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "配电柜":      {"unit_price_low": 200, "unit_price_high": 5000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "熔断器":      {"unit_price_low": 1,   "unit_price_high": 20,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "接触器":      {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "避雷器":      {"unit_price_low": 10,  "unit_price_high": 200, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "电力变压器油": {"unit_price_low": 3,   "unit_price_high": 15,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "铜排":        {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 15, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 其他常见工业品 ──
    "不锈钢阀门": {"unit_price_low": 30,  "unit_price_high": 500, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "铸件":    {"unit_price_low": 10,  "unit_price_high": 200, "margin_pct": 20, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "锻件":    {"unit_price_low": 20,  "unit_price_high": 500, "margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "钢管":    {"unit_price_low": 2,   "unit_price_high": 30,  "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "铝型材":  {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "模具":    {"unit_price_low": 500, "unit_price_high": 20000,"margin_pct": 30,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "CNC加工件": {"unit_price_low": 5,   "unit_price_high": 200, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "焊接件":  {"unit_price_low": 10,  "unit_price_high": 300, "margin_pct": 20, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 工业化学品（15 种） ──
    "工业涂料": {"unit_price_low": 10,  "unit_price_high": 80,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "防锈漆":  {"unit_price_low": 8,   "unit_price_high": 50,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "环氧树脂": {"unit_price_low": 15,  "unit_price_high": 120, "margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "工业润滑油": {"unit_price_low": 5,   "unit_price_high": 40,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "清洗剂":  {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "胶粘剂":  {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "密封胶":  {"unit_price_low": 3,   "unit_price_high": 25,  "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "催化剂":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "溶剂":    {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "表面处理剂": {"unit_price_low": 8,   "unit_price_high": 60,  "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "电镀液":  {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "粉末涂料": {"unit_price_low": 5,   "unit_price_high": 40,  "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "工业脱脂剂": {"unit_price_low": 4,   "unit_price_high": 30,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "聚氨酯涂料": {"unit_price_low": 12,  "unit_price_high": 100, "margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "阻燃剂":  {"unit_price_low": 8,   "unit_price_high": 80,  "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 工业化学品追加（2026-06 扩展）
    "工业酒精":    {"unit_price_low": 1,   "unit_price_high": 5,   "margin_pct": 18, "source": "TradeIndia 2026 B2B benchmark", "updated": "2026-06"},
    "水处理药剂":  {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "防腐涂料":    {"unit_price_low": 8,   "unit_price_high": 60,  "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "聚氨酯":      {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "有机硅":      {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 32, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "钛白粉":      {"unit_price_low": 2,   "unit_price_high": 10,  "margin_pct": 22, "source": "TradeIndia 2026 B2B benchmark", "updated": "2026-06"},
    "活性炭":      {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 包装材料（12 种） ──
    "瓦楞纸箱": {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "塑料包装袋": {"unit_price_low": 0.02,"unit_price_high": 0.5, "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "气泡膜":  {"unit_price_low": 0.5, "unit_price_high": 3,   "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "缠绕膜":  {"unit_price_low": 1,   "unit_price_high": 8,   "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "塑料托盘": {"unit_price_low": 10,  "unit_price_high": 80,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "木托盘":  {"unit_price_low": 8,   "unit_price_high": 40,  "margin_pct": 15, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "打包带":  {"unit_price_low": 0.5, "unit_price_high": 3,   "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "封箱胶带": {"unit_price_low": 0.3, "unit_price_high": 3,   "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "塑料瓶":  {"unit_price_low": 0.05,"unit_price_high": 0.5, "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "泡沫包装": {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "纸板":    {"unit_price_low": 0.3, "unit_price_high": 2,   "margin_pct": 15, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "铝箔袋":  {"unit_price_low": 0.05,"unit_price_high": 0.5, "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # 包装材料追加（2026-06 扩展）
    "纸浆模塑":     {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "可降解包装袋": {"unit_price_low": 0.05,"unit_price_high": 0.8, "margin_pct": 25, "source": "Global Sources 2026 B2B benchmark", "updated": "2026-06"},
    "真空包装袋":   {"unit_price_low": 0.05,"unit_price_high": 0.5, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "吨袋":        {"unit_price_low": 3,   "unit_price_high": 15,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "纸管":        {"unit_price_low": 0.3, "unit_price_high": 3,   "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 建筑材料（13 种） ──
    "水泥":    {"unit_price_low": 5,   "unit_price_high": 15,  "margin_pct": 12, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "钢筋":    {"unit_price_low": 0.5, "unit_price_high": 2,   "margin_pct": 10, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "混凝土":  {"unit_price_low": 50,  "unit_price_high": 150, "margin_pct": 15, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "瓷砖":    {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "钢化玻璃": {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "石膏板":  {"unit_price_low": 3,   "unit_price_high": 15,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "防水卷材": {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "保温板":  {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "铝型材":  {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "建筑模板": {"unit_price_low": 15,  "unit_price_high": 80,  "margin_pct": 18, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "PVC管道": {"unit_price_low": 2,   "unit_price_high": 20,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "建筑密封胶": {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "石材":    {"unit_price_low": 20,  "unit_price_high": 200, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 建筑材料追加（2026-06 扩展）
    "铝合金门窗": {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "H型钢":     {"unit_price_low": 0.5, "unit_price_high": 2,   "margin_pct": 10, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "岩棉板":    {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "木地板":    {"unit_price_low": 5,   "unit_price_high": 40,  "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "彩钢板":    {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 18, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 五金工具（14 种） ──
    "扳手":    {"unit_price_low": 3,   "unit_price_high": 25,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "螺丝刀":  {"unit_price_low": 1,   "unit_price_high": 10,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "钳子":    {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "电钻":    {"unit_price_low": 30,  "unit_price_high": 200, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "锤子":    {"unit_price_low": 3,   "unit_price_high": 20,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "卷尺":    {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "套筒扳手": {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "角磨机":  {"unit_price_low": 25,  "unit_price_high": 150, "margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "冲击钻":  {"unit_price_low": 40,  "unit_price_high": 300, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "手锯":    {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "锉刀":    {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "千斤顶":  {"unit_price_low": 20,  "unit_price_high": 200, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "工具箱":  {"unit_price_low": 10,  "unit_price_high": 80,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "棘轮扳手": {"unit_price_low": 8,   "unit_price_high": 60,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # 五金工具追加（2026-06 扩展）
    "液压千斤顶": {"unit_price_low": 30,  "unit_price_high": 300, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "电动扳手":   {"unit_price_low": 50,  "unit_price_high": 400, "margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "焊机":       {"unit_price_low": 100, "unit_price_high": 2000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "手电钻":     {"unit_price_low": 20,  "unit_price_high": 150, "margin_pct": 22, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "台钳":       {"unit_price_low": 15,  "unit_price_high": 100, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 安全防护（12 种） ──
    "安全帽":  {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "防护手套": {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "N95口罩": {"unit_price_low": 0.1, "unit_price_high": 2,   "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "防护服":  {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "护目镜":  {"unit_price_low": 1,   "unit_price_high": 10,  "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "安全带":  {"unit_price_low": 10,  "unit_price_high": 80,  "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "安全鞋":  {"unit_price_low": 8,   "unit_price_high": 50,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "反光背心": {"unit_price_low": 2,   "unit_price_high": 10,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "灭火器":  {"unit_price_low": 10,  "unit_price_high": 80,  "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "防毒面具": {"unit_price_low": 15,  "unit_price_high": 150, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "耳塞":    {"unit_price_low": 0.1, "unit_price_high": 2,   "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "防护面罩": {"unit_price_low": 3,   "unit_price_high": 25,  "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # 安全防护追加（2026-06 扩展）
    "安全绳":    {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "防静电服":  {"unit_price_low": 8,   "unit_price_high": 80,  "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "警示胶带":  {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "洗眼器":    {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 物流仓储（11 种） ──
    "货架":    {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "叉车":    {"unit_price_low": 3000,"unit_price_high": 30000,"margin_pct": 18,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "塑料托盘": {"unit_price_low": 10,  "unit_price_high": 80,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "手动叉车": {"unit_price_low": 200, "unit_price_high": 2000,"margin_pct": 20, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "输送机":  {"unit_price_low": 1000,"unit_price_high": 10000,"margin_pct": 22,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "周转箱":  {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "升降平台": {"unit_price_low": 500, "unit_price_high": 5000,"margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "手推车":  {"unit_price_low": 30,  "unit_price_high": 200, "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "堆垛机":  {"unit_price_low": 5000,"unit_price_high": 50000,"margin_pct": 20,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "仓储笼":  {"unit_price_low": 20,  "unit_price_high": 150, "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "AGV小车": {"unit_price_low": 5000,"unit_price_high": 50000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 物流仓储追加（2026-06 扩展）
    "工业脚轮":     {"unit_price_low": 2,   "unit_price_high": 20,  "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "工业风扇":     {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "缠绕包装机":   {"unit_price_low": 500, "unit_price_high": 5000,"margin_pct": 28,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "升降平台":     {"unit_price_low": 500, "unit_price_high": 5000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 环保设备（10 种） ──
    "除尘器":  {"unit_price_low": 1000,"unit_price_high": 10000,"margin_pct": 28,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "污水处理设备": {"unit_price_low": 5000,"unit_price_high": 50000,"margin_pct": 30,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "过滤器":  {"unit_price_low": 15,  "unit_price_high": 200, "margin_pct": 26, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "活性炭":  {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "脱硫设备": {"unit_price_low": 10000,"unit_price_high": 100000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "废气处理塔": {"unit_price_low": 2000,"unit_price_high": 20000,"margin_pct": 28,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "水处理膜": {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "垃圾压缩机": {"unit_price_low": 3000,"unit_price_high": 30000,"margin_pct": 22,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "空气净化器": {"unit_price_low": 200, "unit_price_high": 2000,"margin_pct": 30,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "油烟净化器": {"unit_price_low": 300, "unit_price_high": 3000,"margin_pct": 28,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 环保设备追加（2026-06 扩展）
    "布袋除尘器":   {"unit_price_low": 2000, "unit_price_high": 20000,"margin_pct": 28,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "RO反渗透膜":   {"unit_price_low": 200,  "unit_price_high": 2000, "margin_pct": 35,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "脱硫塔":       {"unit_price_low": 5000, "unit_price_high": 50000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "垃圾焚烧炉":   {"unit_price_low": 10000,"unit_price_high": 100000,"margin_pct": 20,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 橡塑制品（13 种） ──
    "橡胶密封圈": {"unit_price_low": 0.05,"unit_price_high": 2,   "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "硅胶管":  {"unit_price_low": 1,   "unit_price_high": 10,  "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "氟橡胶O型圈": {"unit_price_low": 0.1, "unit_price_high": 3,   "margin_pct": 32, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "橡胶垫片": {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "塑料注塑件": {"unit_price_low": 0.5, "unit_price_high": 20,  "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "尼龙扎带": {"unit_price_low": 0.01,"unit_price_high": 0.1, "margin_pct": 15, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "聚氨酯密封件": {"unit_price_low": 1,   "unit_price_high": 15,  "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "橡胶软管": {"unit_price_low": 2,   "unit_price_high": 15,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "硅胶密封条": {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "PTFE垫片": {"unit_price_low": 1,   "unit_price_high": 10,  "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "减震橡胶": {"unit_price_low": 2,   "unit_price_high": 20,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "塑料桶":  {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "工程塑料件": {"unit_price_low": 5,   "unit_price_high": 100, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # 橡塑制品追加（2026-06 扩展）
    "橡胶板":       {"unit_price_low": 3,   "unit_price_high": 30,  "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "PVC板":        {"unit_price_low": 5,   "unit_price_high": 40,  "margin_pct": 22, "source": "TradeIndia 2026 B2B benchmark", "updated": "2026-06"},
    "聚四氟乙烯板": {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "硅胶垫":       {"unit_price_low": 0.5, "unit_price_high": 5,   "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # ── 制冷暖通（12 种） ──
    "空调压缩机": {"unit_price_low": 100, "unit_price_high": 1000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "冷凝器":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "蒸发器":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "热交换器": {"unit_price_low": 200, "unit_price_high": 5000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "冷却塔":  {"unit_price_low": 1000,"unit_price_high": 10000,"margin_pct": 22,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "工业风机": {"unit_price_low": 50,  "unit_price_high": 800, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "冷水机":  {"unit_price_low": 1500,"unit_price_high": 15000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "热泵":    {"unit_price_low": 2000,"unit_price_high": 20000,"margin_pct": 22,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "冷媒":    {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "温控器":  {"unit_price_low": 10,  "unit_price_high": 100, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "通风管道": {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "空调风机盘管": {"unit_price_low": 50, "unit_price_high": 500, "margin_pct": 25, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 工业电子（新增 2026-06）──
    "工业显示屏":    {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 25, "source": "Global Sources 2026 B2B benchmark", "updated": "2026-06"},
    "PCB板":         {"unit_price_low": 1,   "unit_price_high": 20,  "margin_pct": 20, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "散热器":        {"unit_price_low": 5,   "unit_price_high": 100, "margin_pct": 25, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "连接器":        {"unit_price_low": 0.1, "unit_price_high": 5,   "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "电子元器件套件": {"unit_price_low": 0.01,"unit_price_high": 1,   "margin_pct": 15, "source": "TradeIndia 2026 B2B benchmark", "updated": "2026-06"},
    "电缆接头":      {"unit_price_low": 0.5, "unit_price_high": 10,  "margin_pct": 22, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "工业电源模块":  {"unit_price_low": 20,  "unit_price_high": 200, "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "防雷器":        {"unit_price_low": 5,   "unit_price_high": 50,  "margin_pct": 30, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    # ── 医疗器械（新增 2026-06）──
    "医用口罩":      {"unit_price_low": 0.05,"unit_price_high": 0.5, "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "一次性手套":    {"unit_price_low": 0.02,"unit_price_high": 0.2, "margin_pct": 30, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    "血压计":        {"unit_price_low": 15,  "unit_price_high": 100, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "轮椅":          {"unit_price_low": 80,  "unit_price_high": 500, "margin_pct": 28, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "医用导管":      {"unit_price_low": 1,   "unit_price_high": 20,  "margin_pct": 40, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "手术器械套装":  {"unit_price_low": 50,  "unit_price_high": 500, "margin_pct": 35, "source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "病床":          {"unit_price_low": 200, "unit_price_high": 2000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "听诊器":        {"unit_price_low": 5,   "unit_price_high": 30,  "margin_pct": 35, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"},
    # 制冷暖通追加（2026-06 扩展）
    "制冷压缩机": {"unit_price_low": 500, "unit_price_high": 5000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "板式换热器": {"unit_price_low": 200, "unit_price_high": 3000,"margin_pct": 28,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "冷风机":     {"unit_price_low": 300, "unit_price_high": 3000,"margin_pct": 25,"source": "Made-in-China 2026 B2B index", "updated": "2026-06"},
    "膨胀阀":     {"unit_price_low": 15,  "unit_price_high": 150, "margin_pct": 28, "source": "AliBaba 2026 B2B benchmark", "updated": "2026-06"}
}


# ═══════════════════════════════════════════════════════════════════
# 产品数据富化结果数据结构
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EnrichmentResult:
    """产品市场数据查询结果"""
    product_name: str
    unit_price_usd: Optional[float] = None      # 查询到的市场参考单价
    unit_price_low: Optional[float] = None       # 单价区间下限
    unit_price_high: Optional[float] = None      # 单价区间上限
    profit_margin_pct: Optional[float] = None    # 查询到的行业利润率
    data_source: str = ""                        # 数据来源标注
    confidence: str = "medium"                   # 置信度: high / medium / low
    data_freshness: str = "normal"               # 数据新鲜度: fresh(<6月) / normal / stale(>12月)
    updated: str = ""                             # 数据最后更新时间 (YYYY-MM)
    enriched: bool = False                       # 是否成功富化
    search_query: Optional[str] = None           # 生成的搜索查询词
    niche_industrial_category: str = ""           # 小众工业品品类名（v3.5 new）
    niche_adjustment: Optional[Dict] = None       # 小众工业品调整信息（v3.5 new）


class ProductEnricher:
    """产品数据实时查询富化器。

    通过多级查表（精确匹配 → 子类参考 → 行业兜底）获取产品市场参考数据。
    设计为可独立调用的模块，支持扩展外部搜索接口。
    """

    # ── 搜索查询模板（供外部搜索接口使用） ──
    SEARCH_TEMPLATES = [
        "{product} 批发价格 B2B USD",
        "{product} wholesale price per unit",
        "{product} average market price industry",
        "{product} unit price FOB China",
        "{product} 利润率 行业 B2B",
    ]

    @staticmethod
    def generate_search_queries(product_name: str) -> List[str]:
        """生成产品市场数据的搜索查询词列表。"""
        return [tmpl.format(product=product_name) for tmpl in ProductEnricher.SEARCH_TEMPLATES]

    @staticmethod
    def _calc_freshness(updated: str) -> str:
        """根据 updated (YYYY-MM) 计算数据新鲜度。"""
        if not updated:
            return "normal"
        try:
            from datetime import datetime
            parts = updated.split("-")
            if len(parts) == 2:
                y, m = int(parts[0]), int(parts[1])
                dt = datetime(y, m, 1)
                months = (datetime(2026, 6, 30) - dt).days / 30.44
                if months < 6:
                    return "fresh"
                elif months > 12:
                    return "stale"
                else:
                    return "normal"
        except Exception:
            pass
        return "normal"

    @staticmethod
    def _lookup_product_price(product_name: str) -> Optional[Dict[str, Any]]:
        """在 PRODUCT_PRICE_REFERENCE 中做末级关键词查表。

        匹配策略：
        1. 精确匹配产品名
        2. 关键词子串匹配（产品名包含参考词，或参考词包含在产品名中）
        """
        name_lower = product_name.lower().strip()

        # 精确匹配
        for ref_name, ref_data in PRODUCT_PRICE_REFERENCE.items():
            if ref_name == product_name.strip():
                return ref_data

        # 子串匹配（按最长匹配优先）
        best_match = None
        best_len = 0
        for ref_name, ref_data in PRODUCT_PRICE_REFERENCE.items():
            ref_lower = ref_name.lower()
            if ref_lower in name_lower and len(ref_lower) > best_len:
                best_match = ref_data
                best_len = len(ref_lower)
            elif name_lower in ref_lower and len(name_lower) > best_len:
                best_match = ref_data
                best_len = len(name_lower)

        return best_match

    @staticmethod
    def _lookup_subcategory_price(
        subcategory: str, subcategory_matched: bool
    ) -> Optional[Dict[str, Any]]:
        """从 INDUSTRIAL_SUBCATEGORIES 获取子类级别的参考价格。"""
        if not subcategory or not subcategory_matched:
            return None
        sub = INDUSTRIAL_SUBCATEGORIES.get(subcategory)
        if not sub or subcategory == "通用工业":
            return None
        return {
            "unit_price": sub["unit_price_usd"],
            "margin_pct": sub["profit_margin_pct"],
            "source": f"子类参考: {subcategory} (INDUSTRIAL_SUBCATEGORIES)",
        }

    @staticmethod
    def enrich(
        product_name: str,
        subcategory: str = "",
        subcategory_matched: bool = False,
        search_fn: Optional[callable] = None,
    ) -> EnrichmentResult:
        """查询产品市场数据，返回 EnrichmentResult。

        查询优先级：
        1. PRODUCT_PRICE_REFERENCE 末级查表（最精确）
        2. INDUSTRIAL_SUBCATEGORIES 子类参考（次精确）
        3. 小众工业品匹配（v3.5，关键词匹配 NICHE_INDUSTRIAL_ADJUSTMENTS）
        4. 生成搜索查询词（供外部搜索接口使用）

        Args:
            product_name: 产品名称
            subcategory: 已匹配的工业子类名（可为空）
            subcategory_matched: 子类是否成功匹配
            search_fn: 外部搜索函数，签名为 fn(query: str) -> Optional[dict]
                       当传入时，会调用该函数进行实时网络搜索

        Returns:
            EnrichmentResult 实例
        """
        result = EnrichmentResult(product_name=product_name)

        # ── 第 1 级：末级产品查表 ──
        ref = ProductEnricher._lookup_product_price(product_name)
        if ref:
            low = ref["unit_price_low"]
            high = ref["unit_price_high"]
            result.unit_price_usd = round((low + high) / 2.0, 2)
            result.unit_price_low = low
            result.unit_price_high = high
            result.profit_margin_pct = ref["margin_pct"]
            result.data_source = ref["source"]
            result.updated = ref.get("updated", "2026-01")
            result.data_freshness = ProductEnricher._calc_freshness(result.updated)
            result.confidence = "medium"
            result.enriched = True
            result.search_query = ProductEnricher.generate_search_queries(product_name)[0]
            return result

        # ── 第 2 级：子类参考 ──
        sub_ref = ProductEnricher._lookup_subcategory_price(subcategory, subcategory_matched)
        if sub_ref:
            result.unit_price_usd = sub_ref["unit_price"]
            result.profit_margin_pct = sub_ref["margin_pct"]
            result.data_source = sub_ref["source"]
            result.confidence = "low"
            result.enriched = True
            result.search_query = ProductEnricher.generate_search_queries(product_name)[0]
            return result

        # ── 第 3 级（新增 v3.5）：小众工业品调整 — 关键词匹配 ──
        if _NICHE_INDUSTRIAL_AVAILABLE:
            niche_info = apply_niche_adjustment(product_name)
            if niche_info and niche_info.get("applied"):
                result.niche_industrial_category = niche_info["category"]
                result.niche_adjustment = niche_info
                # 不修改 unit_price/margin（保留默认值），仅标记以便后续 KPI 调整
                result.data_source = f"小众工业品调整: {niche_info['category']}"
                result.confidence = "low"
                result.enriched = True
                result.search_query = ProductEnricher.generate_search_queries(product_name)[0]
                return result

        # ── 第 4 级：未匹配 — 生成搜索建议 ──
        result.search_query = ProductEnricher.generate_search_queries(product_name)[0]
        result.data_source = "no local match — consider external search"
        result.confidence = "unknown"
        result.enriched = False
        return result

    @staticmethod
    def enrich_with_search(
        product_name: str,
        search_fn: callable,
        subcategory: str = "",
        subcategory_matched: bool = False,
    ) -> EnrichmentResult:
        """带外部搜索的富化方法。

        先走本地查表，未命中时调用外部搜索接口。
        search_fn 签名为 fn(query: str) -> Optional[Dict[str, Any]]
        返回 dict 应包含: unit_price_usd, profit_margin_pct, data_source (可选)
        """
        # 先走本地逻辑
        result = ProductEnricher.enrich(product_name, subcategory, subcategory_matched)

        # 本地已命中则直接返回
        if result.enriched:
            return result

        # 尝试外部搜索
        if search_fn is None:
            return result

        queries = ProductEnricher.generate_search_queries(product_name)
        for q in queries:
            try:
                raw = search_fn(q)
                if raw and isinstance(raw, dict) and raw.get("unit_price_usd"):
                    result.unit_price_usd = float(raw["unit_price_usd"])
                    result.profit_margin_pct = (
                        float(raw["profit_margin_pct"])
                        if raw.get("profit_margin_pct") is not None
                        else None
                    )
                    result.unit_price_low = (
                        float(raw["unit_price_low"])
                        if raw.get("unit_price_low") is not None
                        else None
                    )
                    result.unit_price_high = (
                        float(raw["unit_price_high"])
                        if raw.get("unit_price_high") is not None
                        else None
                    )
                    result.data_source = raw.get("data_source", f"web search: {q}")
                    result.confidence = "medium"
                    result.enriched = True
                    result.search_query = q
                    break
            except Exception:
                continue

        return result


# 素材创意矩阵 — 基于 GitHub ad-creative-strategy-guide + 行业最佳实践
CREATIVE_MATRIX: Dict[str, Dict[str, Any]] = {
    # 按广告目标分
    "CONVERSIONS": {
        "primary_format": "轮播广告 (Carousel)",
        "ratio": "1:1 或 4:5",
        "cta": "Shop Now",
        "tips": [
            "3-5张卡片：痛点 → 解决方案 → 用户证言 → 行动号召",
            "每张卡片搭配独立短文案，突出不同卖点",
            "使用高对比度产品图，背景简洁突出主体",
            "移动端优先：关键信息放在画面60%区域",
        ],
    },
    "ENGAGEMENT": {
        "primary_format": "视频广告 (Video)",
        "ratio": "9:16 竖屏",
        "cta": "Learn More",
        "tips": [
            "前3秒必须抓住注意力，直接展示核心卖点",
            "视频时长控制在15秒内，必须添加字幕（85%静音观看）",
            "使用演示类内容：产品使用过程、before/after对比",
            "结尾加明确的互动引导（提问/投票/话题标签）",
        ],
    },
    "REACH": {
        "primary_format": "单图广告 (Single Image)",
        "ratio": "4:5 垂直格式",
        "cta": "Shop Now",
        "tips": [
            "大号加粗文案，确保5英寸屏幕可读",
            "产品占画面70%以上，背景极简",
            "颜色对比强烈，提升拇指滑动停留率",
            "一个画面只传递一个核心信息",
        ],
    },
    "LEAD_GENERATION": {
        "primary_format": "线索表单广告 (Lead Form)",
        "ratio": "1:1 或 4:5",
        "cta": "Sign Up",
        "tips": [
            "主图使用白皮书封面/样品图/案例对比图",
            "标题直接说明价值（如：'免费获取行业采购指南'）",
            "表单字段精简到3-5个，降低填写阻力",
            "B2B场景使用专业沉稳色调（深蓝/灰/白）",
        ],
    },
}

# B2B/B2C 差异化素材策略
BIZ_CREATIVE_OVERLAY: Dict[str, Dict[str, Any]] = {
    "B2B": {
        "extra_tips": [
            "优先使用白皮书/案例研究作为内容钩子",
            "强调ROI数据和生产效率提升",
            "工厂实拍/生产线/质检流程增强信任感",
        ],
        "preferred_cta": "Download 或 Get Quote",
    },
    "B2C": {
        "extra_tips": [
            "优先使用UGC（用户生成内容）/买家秀素材",
            "生活方式场景图 > 纯产品图",
            "限时优惠/折扣倒计时增强紧迫感",
        ],
        "preferred_cta": "Shop Now",
    },
}

# 生命周期阶段素材策略
LIFECYCLE_CREATIVE: Dict[str, Dict[str, Any]] = {
    "新品": {
        "strategy": "教育市场 + 建立认知",
        "formats": ["视频讲解 (15-30s)", "单图品牌介绍"],
        "angle": "技术创新/解决痛点/差异化优势",
    },
    "成长期": {
        "strategy": "社交证明 + 扩大覆盖",
        "formats": ["轮播广告 (对比+证言)", "UGC视频"],
        "angle": "用户好评/使用场景/竞品对比",
    },
    "成熟期": {
        "strategy": "再营销 + 提升转化",
        "formats": ["DPA动态产品广告", "限时优惠单图"],
        "angle": "老客专享/限时折扣/搭配推荐",
    },
    "衰退期": {
        "strategy": "清仓 + 最大化ROI",
        "formats": ["折扣单图", "最后机会轮播"],
        "angle": "超低价清仓/库存告急/最后机会",
    },
}

# 各生命周期阶段 → [互动目标权重, 转化目标权重, 流量目标权重]
LIFECYCLE_WEIGHTS: Dict[str, List[float]] = {
    "新品":   [0.50, 0.20, 0.30],
    "成长期": [0.30, 0.45, 0.25],
    "成熟期": [0.10, 0.65, 0.25],
    "衰退期": [0.05, 0.80, 0.15],
}

# 目标市场 → [推荐投放时段(UTC), 日预算系数, 基准CPM, 基准CPC, 基准CTR]
# 修正：基于 DigitalPoint(2026) 全行业均值对齐
# 北美 CPC=$1.70(原$0.85→上调), CPM=$12.50(保持), CTR=1.50%(原1.20%→微调)
# 其他市场按原有相对系数等比调整
MARKET_PROFILES: Dict[str, Dict[str, Any]] = {
    "北美":   {"peak_hours": "15:00-03:00 UTC", "budget_coeff": 1.00, "cpm": 12.50, "cpc": 1.70, "ctr_pct": 1.50},
    "欧洲":   {"peak_hours": "07:00-21:00 UTC", "budget_coeff": 0.85, "cpm": 10.00, "cpc": 1.30, "ctr_pct": 1.69},
    "东南亚": {"peak_hours": "03:00-15:00 UTC", "budget_coeff": 0.45, "cpm": 3.50,  "cpc": 0.36, "ctr_pct": 2.25},
    "中东":   {"peak_hours": "07:00-20:00 UTC", "budget_coeff": 0.55, "cpm": 5.00,  "cpc": 0.60, "ctr_pct": 1.88},
    "南美":   {"peak_hours": "13:00-02:00 UTC", "budget_coeff": 0.40, "cpm": 3.00,  "cpc": 0.30, "ctr_pct": 2.13},
    "大洋洲": {"peak_hours": "21:00-08:00 UTC", "budget_coeff": 0.90, "cpm": 11.00, "cpc": 1.50, "ctr_pct": 1.56},
}

BUSINESS_TYPE_STRATEGY: Dict[str, Dict[str, Any]] = {
    "B2B": {
        "audience": [
            "采购经理 / Supply Chain Manager",
            "企业主 / Business Owner",
            "行业批发商 / Wholesaler",
            "运营总监 / Operations Director",
        ],
        "lookalike": "现有B2B客户列表 / 展会名片 / LinkedIn匹配",
        "placements": ["Facebook Feed", "Instagram Feed", "Audience Network"],
        "bid_strategy": "target_cost",
        "bid_adj": 1.15,
    },
    "B2C": {
        "audience": [
            "兴趣人群 / Interest-based Audience",
            "竞品粉丝 / Competitor Page Fans",
            "电商活跃用户 / Online Shoppers",
            "生活方式匹配人群 / Lifestyle Lookalike",
        ],
        "lookalike": "网站访客 / 加购未支付 / 已购买客户",
        "placements": ["Facebook Feed", "Instagram Feed", "Instagram Reels", "Facebook Marketplace"],
        "bid_strategy": "lowest_cost",
        "bid_adj": 1.0,
    },
}

OBJECTIVE_LABELS: Dict[str, str] = {
    "REACH": "覆盖",
    "BRAND_AWARENESS": "品牌认知",
    "ENGAGEMENT": "互动",
    "VIDEO_VIEWS": "视频观看",
    "LEAD_GENERATION": "线索",
    "MESSAGES": "消息互动",
    "CONVERSIONS": "转化量",
    "CATALOG_SALES": "目录销售",
    "STORE_TRAFFIC": "门店客流",
}


# ═══════════════════════════════════════════════════════════════════
# 0-b. 模型版本 & 校准因子 & 数据来源标注
# ═══════════════════════════════════════════════════════════════════

MODEL_VERSION = "v3.5"
MODEL_LAST_UPDATED = "2026-06-30"

# KPI 数据来源标注模板 — 每个指标的数据源与可信度等级
KPI_DATA_SOURCE_TEMPLATE: Dict[str, Dict[str, Any]] = {
    "ctr": {
        "source": "Digital Point 2026 基准 + 行业校准系数",
        "confidence": "高",
        "confidence_pct": 85,
    },
    "cpc": {
        "source": "AdBacklog 2025 基准 + 市场调整系数",
        "confidence": "中高",
        "confidence_pct": 78,
    },
    "cpm": {
        "source": "Digital Point 2026 市场基准",
        "confidence": "高",
        "confidence_pct": 82,
    },
    "cpa": {
        "source": "AdBacklog 2025 行业基准 + 产品客单价校准",
        "confidence": "中",
        "confidence_pct": 70,
    },
}

# 行业级校准因子 — 控制各行业 KPI 预估的浮动范围（比例值）
# 每个系数表示 ± 该比例的范围，如 ctr_range=0.15 表示 CTR 预估浮动 ±15%
CALIBRATION_FACTORS: Dict[str, Dict[str, Any]] = {
    "工业耗材":   {"ctr_range": 0.15, "cpc_range": 0.12, "cpa_range": 0.20, "cpm_range": 0.10, "confidence": "中高"},
    "消费电子":   {"ctr_range": 0.18, "cpc_range": 0.10, "cpa_range": 0.22, "cpm_range": 0.10, "confidence": "中"},
    "服装配饰":   {"ctr_range": 0.15, "cpc_range": 0.12, "cpa_range": 0.18, "cpm_range": 0.10, "confidence": "中高"},
    "家居用品":   {"ctr_range": 0.16, "cpc_range": 0.13, "cpa_range": 0.21, "cpm_range": 0.10, "confidence": "中"},
    "美妆护肤":   {"ctr_range": 0.20, "cpc_range": 0.15, "cpa_range": 0.25, "cpm_range": 0.12, "confidence": "中低"},
    "食品饮料":   {"ctr_range": 0.22, "cpc_range": 0.15, "cpa_range": 0.28, "cpm_range": 0.12, "confidence": "低"},
    "运动户外":   {"ctr_range": 0.15, "cpc_range": 0.12, "cpa_range": 0.18, "cpm_range": 0.10, "confidence": "中高"},
    "教育培训":   {"ctr_range": 0.14, "cpc_range": 0.10, "cpa_range": 0.16, "cpm_range": 0.08, "confidence": "高"},
    "软件SaaS":   {"ctr_range": 0.12, "cpc_range": 0.10, "cpa_range": 0.15, "cpm_range": 0.08, "confidence": "高"},
    "医疗器械":   {"ctr_range": 0.20, "cpc_range": 0.15, "cpa_range": 0.25, "cpm_range": 0.12, "confidence": "中低"},
    "母婴用品":   {"ctr_range": 0.22, "cpc_range": 0.15, "cpa_range": 0.28, "cpm_range": 0.12, "confidence": "低"},
    "宠物用品":   {"ctr_range": 0.22, "cpc_range": 0.15, "cpa_range": 0.28, "cpm_range": 0.12, "confidence": "低"},
    "汽车配件":   {"ctr_range": 0.12, "cpc_range": 0.10, "cpa_range": 0.16, "cpm_range": 0.08, "confidence": "高"},
    "工业电子": {
        "unit_price_usd": 25.0,
        "profit_margin_pct": 25.0,
        "target_market": "北美",
        "business_type": "B2B",
        "lifecycle_stage": "成长期",
        "expected_conversion_days": 14,
        "description": "PCB/显示屏/连接器/电源模块等工业电子产品",
        "keywords": ["工业电子", "PCB", "电路板", "显示屏", "连接器", "散热器", "电源模块",
                     "电子元器件", "防雷器", "端子", "排针", "排母", "电缆接头",
                     "工业显示器", "工控屏", "触摸屏", "LED驱动", "电源适配器",
                     "继电器", "接触器", "断路器", "熔断器", "开关电源"],
        "expected_ctr": 1.45,
        "expected_cpc": 1.15,
        "expected_cpa": 42.0,
        "expected_roas": 3.85,
    },
    "其他工业品": {"ctr_range": 0.18, "cpc_range": 0.14, "cpa_range": 0.22, "cpm_range": 0.10, "confidence": "中"},
}


# ═══════════════════════════════════════════════════════════════════
# 1. 数据模型
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Product:
    id: str
    name: str
    category: str
    unit_price_usd: float
    profit_margin_pct: float
    target_market: str
    business_type: str          # B2B / B2C
    lifecycle_stage: str        # 新品/成长期/成熟期/衰退期
    expected_conversion_days: int

    # 工业子类匹配（仅"其他工业品"行业使用，其他行业留空）
    subcategory: str = ""
    subcategory_matched: bool = False

    # 产品数据富化（来自 ProductEnricher 查询）
    enriched_unit_price: Optional[float] = None      # 富化后的市场参考单价
    enriched_margin: Optional[float] = None          # 富化后的行业利润率
    enrichment_source: str = ""                      # 数据来源标注（如 "AliBaba 2026 B2B benchmark"）
    enrichment_applied: bool = False                 # 是否应用了富化数据

    def effective_unit_price(self) -> float:
        """返回有效客单价：优先使用富化数据，否则使用原始值。"""
        if self.enrichment_applied and self.enriched_unit_price is not None:
            return self.enriched_unit_price
        return self.unit_price_usd

    def effective_margin(self) -> float:
        """返回有效利润率：优先使用富化数据，否则使用原始值。"""
        if self.enrichment_applied and self.enriched_margin is not None:
            return self.enriched_margin
        return self.profit_margin_pct


@dataclass
class StrategyCard:
    product_id: str
    product_name: str
    category: str
    market: str
    business_type: str
    lifecycle_stage: str

    # 目标权重
    recommended_objective: str
    objective_weights: Dict[str, float]

    # 预算 & 出价
    daily_budget_range: Tuple[float, float]
    bid_range: Tuple[float, float]
    bid_strategy: str
    bid_adj: float
    max_cpa: float

    # KPI 预估（综合市场和行业基准）
    expected_ctr_pct: float
    expected_cpc: float
    expected_cpm: float
    expected_cpa: float

    # 行业级权威基准（来自 DIGITALPOINT + ADBACKLOG 交叉验证）
    industry_ctr: Optional[float] = None
    industry_cpc: Optional[float] = None
    industry_cpa: Optional[float] = None
    industry_roas: Optional[float] = None

    # ROI 预估
    roi_estimate: float = 0.0

    # 投放细节
    audience_profiles: List[str] = field(default_factory=list)
    lookalike_source: str = ""
    recommended_peak_hours: str = ""
    placement_preference: List[str] = field(default_factory=list)

    # 综合评分 (0-100)
    priority_score: int = 0

    # 数据来源可信度标记
    data_confidence: str = (
        "数据源: Digital Point 2026 + AdBacklog 2025 | Meta $48M+ 样本"
    )

    # ── KPI 置信区间（基准值已有 expected_* 字段，这里是浮动范围） ──
    ctr_range: Tuple[float, float] = (0.0, 0.0)
    cpc_range: Tuple[float, float] = (0.0, 0.0)
    cpm_range: Tuple[float, float] = (0.0, 0.0)
    cpa_range: Tuple[float, float] = (0.0, 0.0)

    # KPI 数据来源与可信度标注
    kpi_data_sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 是否应用了历史数据校准
    calibration_applied: bool = False

    # 模型版本标识
    model_version: str = ""

    # 工业子类匹配（仅"其他工业品"行业有效，其他行业为空）
    subcategory: str = ""
    subcategory_matched: bool = False

    # 创意素材推荐
    creative_format: str = ""           # 推荐素材类型：单图/轮播/视频/合集/线索表单
    creative_ratio: str = ""            # 推荐比例：1:1 / 4:5 / 9:16
    creative_cta: str = ""             # 推荐 CTA：Shop Now / Learn More / Sign Up 等
    creative_tips: List[str] = field(default_factory=list)  # 3-5条素材制作建议

    # 投放执行指南
    execution_steps: List[str] = field(default_factory=list)  # 5-6步操作步骤
    budget_split: str = ""             # 预算分配建议
    testing_strategy: str = ""         # A/B测试策略


def _upgrade_confidence(current: str) -> str:
    """置信度升级映射：低→中低→中→中高→高"""
    mapping = {"低": "中低", "中低": "中", "中": "中高", "中高": "高", "高": "高"}
    return mapping.get(current, current)


# ═══════════════════════════════════════════════════════════════════
# 2. 核心策略引擎
# ═══════════════════════════════════════════════════════════════════

class AdsStrategyEngine:
    """多产品投流策略引擎 — 综合市场全景 + 行业细分权威基准 + 置信区间 + 历史校准"""

    DAILY_BUDGET_BASE = 50.0       # 北美基准日预算 (USD)
    BID_MULTIPLIER_LOW = 0.80
    BID_MULTIPLIER_HIGH = 1.30
    CPA_BUFFER = 0.40              # CPA上限 = 客单价 × 利润率 × 0.40

    def __init__(self):
        self._calibrator: Optional[HistoricalCalibrator] = None
        self._calibration_applied = False

    def set_calibrator(self, calibrator: HistoricalCalibrator):
        """设置历史数据校准器"""
        self._calibrator = calibrator
        self._calibration_applied = True

    def clear_calibrator(self):
        """清除历史数据校准"""
        self._calibrator = None
        self._calibration_applied = False

    def generate(self, product: Product) -> StrategyCard:
        # ── 市场级别基准 ──
        market = MARKET_PROFILES.get(product.target_market)
        if not market:
            raise ValueError(f"未知目标市场: {product.target_market}")

        # ── 行业级别权威基准 ──
        industry = INDUSTRY_DEFAULTS.get(product.category, {})

        # ── 工业子类匹配与差异化调整（仅"其他工业品"行业） ──
        subcategory = getattr(product, "subcategory", "")
        subcategory_matched = getattr(product, "subcategory_matched", False)

        if product.category == "其他工业品" and subcategory:
            sub = INDUSTRIAL_SUBCATEGORIES.get(subcategory)
        else:
            sub = None

        # 预期 CPM 始终来自市场
        expected_cpm = market["cpm"]

        # 预期 CPC：优先使用行业权威数据（更精准），否则回退到市场均值
        ind_cpc = industry.get("expected_cpc")
        expected_cpc = ind_cpc if ind_cpc is not None else market["cpc"]

        # 预期 CTR：优先使用行业权威数据
        ind_ctr = industry.get("expected_ctr")
        expected_ctr_pct = ind_ctr if ind_ctr is not None else market["ctr_pct"]

        # 预期 CPA：优先使用行业权威数据，否则用 CPA 公式计算
        # 使用 effective 值（若已富化则用富化数据，否则用原始值）
        eff_price = product.effective_unit_price()
        eff_margin = product.effective_margin()
        ind_cpa = industry.get("expected_cpa")
        cpa_calculated = eff_price * (eff_margin / 100.0) * self.CPA_BUFFER
        expected_cpa = ind_cpa if ind_cpa is not None else cpa_calculated

        # ── 小众工业品调整（v3.5）：第四级匹配，最高优先级 ──
        niche_cat = getattr(product, "niche_industrial_category", "")
        niche_adj = getattr(product, "niche_adjustment", None)
        niche_info_out = None  # 用于写入 StrategyCard

        if niche_adj and niche_adj.get("applied"):
            niche_info_out = niche_adj
            factors = niche_adj["factors"]
            orig_ctr_before_niche = expected_ctr_pct
            orig_cpc_before_niche = expected_cpc
            # 注意：这里 expected_ctr_pct/expected_cpc 目前仍是行业基准值
            # niche 基于 WordStream Industrial 基准（ctr 1.36%, cpc 0.86）调整
            baseline_ctr = niche_adj.get("baseline_ctr", 1.36)
            baseline_cpc = niche_adj.get("baseline_cpc", 0.86)
            baseline_cvr = niche_adj.get("baseline_cvr", 9.34)
            baseline_cpl = niche_adj.get("baseline_cpl", 37.34)

            expected_ctr_pct = round(baseline_ctr * factors["ctr_factor"], 4)
            expected_cpc = round(baseline_cpc * factors["cpc_factor"], 4)
            # cpu/cpl 用于后续 CVR/CPL 预估值
            niche_cvr = round(baseline_cvr * factors["cvr_factor"], 4)
            niche_cpl = round(baseline_cpl * factors["cpl_factor"], 2)

            # 在 niche_info_out 中记录调整前后的值（用于前端展示）
            niche_info_out["pre_ctr"] = orig_ctr_before_niche
            niche_info_out["pre_cpc"] = orig_cpc_before_niche
            niche_info_out["pre_cvr"] = baseline_cvr
            niche_info_out["pre_cpl"] = baseline_cpl

        # ── 工业子类因子：对兜底基准做差异化调节 ──
        if sub:
            expected_ctr_pct = round(expected_ctr_pct * sub["ctr_factor"], 2)
            expected_cpc = round(expected_cpc * sub["cpc_factor"], 3)
            expected_cpa = round(expected_cpa * sub["cpa_factor"], 2)

        # ── CPC 产品级差异化：基于产品实际客单价微调 ──
        # 公式：CPC 调整系数 = (产品有效单价 / 行业默认单价) ^ 0.25
        # 幂指数 0.25 确保调整幅度温和（即使单价差 10 倍，CPC 仅差约 1.8 倍）
        industry_default_price = industry.get("unit_price_usd")
        if industry_default_price and industry_default_price > 0 and eff_price > 0:
            cpc_adj = (eff_price / industry_default_price) ** 0.25
            # 钳制在 0.5x ~ 2.0x 范围内，避免极端值
            cpc_adj = max(0.5, min(2.0, cpc_adj))
            expected_cpc = round(expected_cpc * cpc_adj, 3)

        # CPA 上限基于产品自身数据
        max_cpa = cpa_calculated

        # ── B2B / B2C 策略 ──
        bt = BUSINESS_TYPE_STRATEGY[product.business_type]
        bid_strategy = bt["bid_strategy"]
        bid_adj = bt["bid_adj"]

        # ── 生命周期权重 & 目标选择 ──
        weights = LIFECYCLE_WEIGHTS[product.lifecycle_stage]
        eng, conv, traf = weights
        if conv >= eng and conv >= traf:
            recommended_objective = "CONVERSIONS"
        elif eng >= conv and eng >= traf:
            recommended_objective = "ENGAGEMENT"
        else:
            recommended_objective = "REACH"

        # ── 日预算 ──
        budget_coeff = market["budget_coeff"]
        daily_low = self.DAILY_BUDGET_BASE * budget_coeff * bid_adj
        daily_high = daily_low * 3.0

        # ── 出价区间（基于市场CPC + B2B/B2C调整） ──
        bid_low = expected_cpc * self.BID_MULTIPLIER_LOW * bid_adj
        bid_high = expected_cpc * self.BID_MULTIPLIER_HIGH * bid_adj

        # ── ROI 预估 ──
        ind_roas = industry.get("expected_roas")
        if ind_roas is not None:
            roi_estimate = ind_roas
        elif expected_cpa > 0:
            avg_order_value = eff_price
            roi_estimate = avg_order_value / expected_cpa
        else:
            roi_estimate = 0.0

        # ── 历史数据校准（若已导入） ──
        orig_ctr = expected_ctr_pct
        orig_cpc = expected_cpc
        orig_cpa = expected_cpa
        if self._calibrator is not None and self._calibration_applied:
            expected_ctr_pct = self._calibrator.apply_bias(product.category, "ctr", expected_ctr_pct)
            expected_cpc = self._calibrator.apply_bias(product.category, "cpc", expected_cpc)
            expected_cpa = self._calibrator.apply_bias(product.category, "cpa", expected_cpa)

        # ── 置信区间计算（基于行业校准因子） ──
        calib = CALIBRATION_FACTORS.get(product.category, CALIBRATION_FACTORS["其他工业品"])
        ctr_low = round(expected_ctr_pct * (1 - calib["ctr_range"]), 2)
        ctr_high = round(expected_ctr_pct * (1 + calib["ctr_range"]), 2)
        cpc_low = round(expected_cpc * (1 - calib["cpc_range"]), 3)
        cpc_high = round(expected_cpc * (1 + calib["cpc_range"]), 3)
        cpm_low = round(expected_cpm * (1 - calib["cpm_range"]), 2)
        cpm_high = round(expected_cpm * (1 + calib["cpm_range"]), 2)
        cpa_low = round(expected_cpa * (1 - calib["cpa_range"]), 2)
        cpa_high = round(expected_cpa * (1 + calib["cpa_range"]), 2)

        # ── KPI 数据来源与可信度标注 ──
        kpi_sources = {}
        for metric in ["ctr", "cpc", "cpm", "cpa"]:
            src = dict(KPI_DATA_SOURCE_TEMPLATE[metric])
            if self._calibration_applied:
                src["source"] += " + 历史数据偏差校准"
                src["confidence_pct"] = min(95, src["confidence_pct"] + 8)
                src["confidence"] = _upgrade_confidence(src["confidence"])
            kpi_sources[metric] = src

        # ── 综合评分 (0-100) ──
        score = self._calc_score(product, expected_cpa, roi_estimate, expected_ctr_pct)

        card = StrategyCard(
            product_id=product.id,
            product_name=product.name,
            category=product.category,
            market=product.target_market,
            business_type=product.business_type,
            lifecycle_stage=product.lifecycle_stage,
            recommended_objective=recommended_objective,
            objective_weights={
                "engagement": eng,
                "conversions": conv,
                "traffic": traf,
            },
            daily_budget_range=(round(daily_low, 2), round(daily_high, 2)),
            bid_range=(round(bid_low, 4), round(bid_high, 4)),
            bid_strategy=bid_strategy,
            bid_adj=bid_adj,
            max_cpa=round(max_cpa, 2),
            expected_ctr_pct=round(expected_ctr_pct, 2),
            expected_cpc=round(expected_cpc, 3),
            expected_cpm=round(expected_cpm, 2),
            expected_cpa=round(expected_cpa, 2),
            industry_ctr=industry.get("expected_ctr"),
            industry_cpc=industry.get("expected_cpc"),
            industry_cpa=industry.get("expected_cpa"),
            industry_roas=industry.get("expected_roas"),
            roi_estimate=round(roi_estimate, 2),
            # KPI 置信区间
            ctr_range=(ctr_low, ctr_high),
            cpc_range=(cpc_low, cpc_high),
            cpm_range=(cpm_low, cpm_high),
            cpa_range=(cpa_low, cpa_high),
            # 数据来源与可信度
            kpi_data_sources=kpi_sources,
            calibration_applied=self._calibration_applied,
            model_version=MODEL_VERSION,
            # 工业子类匹配
            subcategory=subcategory,
            subcategory_matched=subcategory_matched,
            audience_profiles=bt["audience"],
            lookalike_source=bt["lookalike"],
            recommended_peak_hours=market["peak_hours"],
            placement_preference=bt["placements"],
            priority_score=score,
        )

        # ── 子类受众叠加 ──
        if sub and sub.get("audience_overlay"):
            existing = set(card.audience_profiles)
            for a in sub["audience_overlay"]:
                if a not in existing:
                    card.audience_profiles.append(a)

        # ── 子类可信度覆盖 ──
        if product.category == "其他工业品":
            if subcategory_matched:
                conf_note = (
                    f"已匹配子类：{subcategory}，置信度{sub.get('confidence_base', '中')}。"
                    f"基于产品关键词细分，建议导入历史数据进一步校准。"
                )
            else:
                conf_note = (
                    f"兜底分类（{subcategory}），置信度较低。"
                    f"产品未匹配到具体子类，建议导入历史数据校准以获得更准确的预估。"
                )
            card.data_confidence = conf_note + " " + card.data_confidence

        # ── 富化数据来源标注 ──
        if product.enrichment_applied and product.enrichment_source:
            card.kpi_data_sources["enrichment"] = {
                "source": product.enrichment_source,
                "unit_price_usd": product.enriched_unit_price,
                "profit_margin_pct": product.enriched_margin,
                "note": "产品市场数据富化结果，置信度高于行业默认值",
            }
            card.data_confidence = (
                f"[市场富化] 数据来源: {product.enrichment_source} | "
                + card.data_confidence
            )

        # ── 素材创意推荐 ──
        obj_matrix = CREATIVE_MATRIX.get(
            recommended_objective,
            CREATIVE_MATRIX["CONVERSIONS"]
        )
        biz_overlay = BIZ_CREATIVE_OVERLAY.get(product.business_type, BIZ_CREATIVE_OVERLAY["B2C"])
        life_creative = LIFECYCLE_CREATIVE.get(product.lifecycle_stage, LIFECYCLE_CREATIVE["成长期"])

        # 合并 tips
        creative_tips_list = list(obj_matrix["tips"])
        creative_tips_list.extend(biz_overlay["extra_tips"])

        card.creative_format = obj_matrix["primary_format"]
        card.creative_ratio = obj_matrix["ratio"]
        card.creative_cta = biz_overlay["preferred_cta"] if product.business_type == "B2B" else obj_matrix["cta"]
        card.creative_tips = creative_tips_list

        # ── 投放执行指南 ──
        budget_low, budget_high = card.daily_budget_range
        card.budget_split = (
            f"测试期（前7天）：日预算 ${budget_low:.0f} USD，70%用于主力广告组 + 30%用于A/B测试；"
            f"稳定期：日预算 ${budget_high:.0f} USD，80%主力 + 20%探索新受众"
        )

        card.testing_strategy = (
            f"创建 3-5 组{obj_matrix['primary_format']}变体，测试变量：主图/封面帧 vs 文案 vs CTA；"
            f"每个广告组最低预算 ${max(10, budget_low * 0.15):.0f} USD/天，运行至少72小时后对比数据，保留CTR/ROAS最优组并放量"
        )

        card.execution_steps = [
            f"1. 素材准备：制作 3-5 组{obj_matrix['primary_format']}，{obj_matrix['ratio']}比例，CTA 使用「{card.creative_cta}」",
            f"2. 受众设置：在 Ads Manager 创建 {card.business_type} 受众组，使用 {card.lookalike_source} 作为 Lookalike 种子",
            f"3. 预算配置：设置 Campaign Budget Optimization (CBO)，日预算 ${budget_low:.0f} USD，出价策略 {card.bid_strategy}",
            f"4. 版位选择：勾选 {'、'.join(card.placement_preference)}，如需扩量可开启 Advantage+ Placements",
            f"5. 上线监控：前 3 天不调整，第 4 天起对比广告组数据（CTR/CPC/CPA），关闭表现低于均值 30% 的广告组",
            f"6. 迭代优化：每周更新一次素材避免疲劳，CPA 稳定后可逐步提升日预算 20-30%/周至 ${budget_high:.0f} USD",
        ]

        return card

    def generate_all(self, products: List[Product]) -> List[StrategyCard]:
        cards = [self.generate(p) for p in products]
        cards.sort(key=lambda c: c.priority_score, reverse=True)
        return cards

    @staticmethod
    def _calc_score(
        product: Product,
        expected_cpa: float,
        roi_estimate: float,
        expected_ctr_pct: float,
    ) -> int:
        """综合评分 0-100：生命周期 20 + 利润率 30 + 客单价 15 + ROI 35"""
        score = 0.0

        # 生命周期 (0-20)
        stage_bonus = {"衰退期": 4, "成熟期": 8, "成长期": 16, "新品": 20}
        score += stage_bonus.get(product.lifecycle_stage, 8)

        # 利润率 (0-30)
        margin = product.profit_margin_pct
        score += min(30, margin * 0.5)

        # 客单价 (0-15)
        if product.unit_price_usd <= 10:
            score += 5
        elif product.unit_price_usd <= 30:
            score += 8
        elif product.unit_price_usd <= 60:
            score += 10
        elif product.unit_price_usd <= 150:
            score += 13
        else:
            score += 15

        # ROI (0-35)
        if roi_estimate >= 5.0:
            score += 35
        elif roi_estimate >= 3.5:
            score += 28
        elif roi_estimate >= 2.5:
            score += 21
        elif roi_estimate >= 1.5:
            score += 14
        elif roi_estimate >= 1.0:
            score += 7
        else:
            score += 3

        return min(100, int(round(score)))


# ═══════════════════════════════════════════════════════════════════
# 3. 智能推断器
# ═══════════════════════════════════════════════════════════════════

class SmartInferrer:
    """智能推断器 — 基于关键词自动匹配行业，兜底到「其他工业品」"""

    @staticmethod
    def match_industry(product_name: str, business_type: str = "B2B") -> Tuple[str, int]:
        """根据产品名中的关键词匹配行业，返回 (行业名, 命中关键词数)"""
        best_match = None
        best_count = 0
        name_lower = product_name.lower()

        for industry, defaults in INDUSTRY_DEFAULTS.items():
            kw_list = defaults.get("keywords", [])
            hits = sum(1 for kw in kw_list if kw.lower() in name_lower)
            if hits > best_count:
                best_count = hits
                best_match = industry

        if best_match and best_count > 0:
            return best_match, best_count

        # 无匹配时，B2B 兜底「其他工业品」，B2C 兜底「消费电子」
        fallback = "其他工业品" if business_type == "B2B" else "消费电子"
        return fallback, 0

    @staticmethod
    def infer(name: str, category: str, industry: str,
              subcategory: str = "", subcategory_matched: bool = False,
              enrichment: Optional[EnrichmentResult] = None) -> Product:
        """根据行业名推断产品参数。

        支持富化数据覆盖：若传入了 enrichment 且 enriched=True，
        则用富化数据覆盖单价/利润率，否则用行业默认值。

        对"其他工业品"，若提供了子类则优先使用子类基准（但富化数据优先级最高）。
        """
        defaults = INDUSTRY_DEFAULTS.get(industry)
        if not defaults:
            raise ValueError(
                f"不支持行业: {industry}。可选: {list(INDUSTRY_DEFAULTS.keys())}"
            )

        # ── 确定基础值 ──
        unit_price = defaults["unit_price_usd"]
        margin_pct = defaults["profit_margin_pct"]
        lifecycle = defaults["lifecycle_stage"]
        conv_days = defaults["expected_conversion_days"]

        # ── "其他工业品"子类覆盖 ──
        if industry == "其他工业品" and subcategory:
            sub = INDUSTRIAL_SUBCATEGORIES.get(subcategory)
            if sub:
                unit_price = sub["unit_price_usd"]
                margin_pct = sub["profit_margin_pct"]
                lifecycle = sub["lifecycle_stage"]
                conv_days = sub["conversion_days"]

        # ── 富化数据覆盖（最高优先级） ──
        enrichment_source = ""
        enrichment_applied = False
        enriched_up = None
        enriched_mg = None
        if enrichment is not None and enrichment.enriched:
            if enrichment.unit_price_usd is not None:
                enriched_up = enrichment.unit_price_usd
                unit_price = enrichment.unit_price_usd
                enrichment_applied = True
            if enrichment.profit_margin_pct is not None:
                enriched_mg = enrichment.profit_margin_pct
                margin_pct = enrichment.profit_margin_pct
                enrichment_applied = True
            if enrichment.data_source:
                enrichment_source = enrichment.data_source

        # ── 小众工业品标记（来自 ProductEnricher） ──
        niche_cat = ""
        niche_adj = None
        if enrichment is not None and enrichment.niche_industrial_category:
            niche_cat = enrichment.niche_industrial_category
            niche_adj = enrichment.niche_adjustment

        return Product(
            id="",
            name=name,
            category=category or industry,
            unit_price_usd=unit_price,
            profit_margin_pct=margin_pct,
            target_market=defaults["target_market"],
            business_type=defaults["business_type"],
            lifecycle_stage=lifecycle,
            expected_conversion_days=conv_days,
            enriched_unit_price=enriched_up,
            enriched_margin=enriched_mg,
            enrichment_source=enrichment_source,
            enrichment_applied=enrichment_applied,
            niche_industrial_category=niche_cat,
            niche_adjustment=niche_adj,
        )

    @staticmethod
    def match_full(product_name: str,
                   business_type: str = "B2B") -> Tuple[str, int, str, int, bool]:
        """一步完成行业匹配 + 子类匹配，返回 (行业, 命中数, 子类, 子类命中数, 子类匹配成功)。

        此方法取代单独调用 match_industry() + match_industrial_subcategory() 的组合，
        确保子类匹配仅在兜底到"其他工业品"时触发，避免误匹配。
        """
        industry, hits = SmartInferrer.match_industry(product_name, business_type)
        if industry == "其他工业品":
            subcat, sub_hits = match_industrial_subcategory(product_name)
            return industry, hits, subcat, sub_hits, (sub_hits > 0)
        return industry, hits, "", 0, False


# ═══════════════════════════════════════════════════════════════════
# 4. 历史数据校准器
# ═══════════════════════════════════════════════════════════════════

class HistoricalCalibrator:
    """基于用户历史投放数据计算偏差系数，用于修正 KPI 预估。

    输入 CSV 格式要求：
        product, industry, actual_ctr, actual_cvr, actual_cpa, actual_cpc
    所有率值以百分比形式（如 1.5 表示 1.5%），金额以 USD。
    """

    REQUIRED_COLUMNS = {"product", "industry", "actual_ctr", "actual_cpa"}

    def __init__(self):
        self._bias_cache: Dict[str, Dict[str, float]] = {}

    def load_from_csv(self, csv_text: str) -> Tuple[bool, str, Optional[Dict[str, Dict[str, float]]]]:
        """解析 CSV 文本，计算每行业的偏差系数。

        Returns:
            (success, message, bias_dict)
            bias_dict: {industry: {"ctr_bias": 1.05, "cpa_bias": 0.92, ...}}
        """
        import csv
        from io import StringIO

        try:
            reader = csv.DictReader(StringIO(csv_text))
            rows = list(reader)
        except Exception as e:
            return False, f"CSV 解析失败: {e}", None

        if not rows:
            return False, "CSV 文件为空或无有效数据行", None

        # 校验列名
        columns = set(reader.fieldnames or [])
        missing = self.REQUIRED_COLUMNS - columns
        if missing:
            return False, f"缺少必要列: {', '.join(missing)}。需要: {', '.join(self.REQUIRED_COLUMNS)}", None

        # 解析数据行
        parsed = []
        for i, row in enumerate(rows, start=2):
            try:
                ind = row.get("industry", "").strip()
                product = row.get("product", "").strip()
                if not ind or not product:
                    continue
                actual_ctr = float(row.get("actual_ctr", 0))
                actual_cpa = float(row.get("actual_cpa", 0))
                actual_cpc = float(row.get("actual_cpc", 0)) if row.get("actual_cpc", "").strip() else None
                if actual_ctr <= 0 or actual_cpa <= 0:
                    continue
                parsed.append({
                    "industry": ind,
                    "product": product,
                    "actual_ctr": actual_ctr,
                    "actual_cpa": actual_cpa,
                    "actual_cpc": actual_cpc,
                })
            except (ValueError, KeyError) as e:
                return False, f"第 {i} 行数据解析错误: {e}", None

        if not parsed:
            return False, "无有效数据行（所有行的 CTR/CPA 必须 > 0）", None

        # 按行业分组计算偏差
        industry_groups: Dict[str, List[dict]] = {}
        for item in parsed:
            ind = item["industry"]
            industry_groups.setdefault(ind, []).append(item)

        bias_dict: Dict[str, Dict[str, float]] = {}

        for ind, items in industry_groups.items():
            # 获取该行业的权威基准
            defaults = INDUSTRY_DEFAULTS.get(ind)
            if not defaults:
                continue

            bench_ctr = defaults.get("expected_ctr")
            bench_cpa = defaults.get("expected_cpa")
            bench_cpc = defaults.get("expected_cpc")

            ctr_biases = []
            cpa_biases = []
            cpc_biases = []

            for item in items:
                if bench_ctr and bench_ctr > 0:
                    ctr_biases.append(item["actual_ctr"] / bench_ctr)
                if bench_cpa and bench_cpa > 0:
                    cpa_biases.append(item["actual_cpa"] / bench_cpa)
                if bench_cpc and bench_cpc > 0 and item["actual_cpc"] is not None:
                    cpc_biases.append(item["actual_cpc"] / bench_cpc)

            entry: Dict[str, float] = {}
            if ctr_biases:
                entry["ctr_bias"] = round(sum(ctr_biases) / len(ctr_biases), 4)
            if cpa_biases:
                entry["cpa_bias"] = round(sum(cpa_biases) / len(cpa_biases), 4)
            if cpc_biases:
                entry["cpc_bias"] = round(sum(cpc_biases) / len(cpc_biases), 4)
            entry["sample_count"] = len(items)

            if entry:
                bias_dict[ind] = entry

        if not bias_dict:
            return False, "未能计算出任何行业的偏差系数（检查行业名是否与系统内置行业一致）", None

        self._bias_cache = bias_dict
        sample_total = sum(v.get("sample_count", 0) for v in bias_dict.values())
        msg = (f"成功导入 {len(parsed)} 条数据，覆盖 {len(bias_dict)} 个行业，"
               f"总样本 {sample_total} 条。偏差系数已就绪。")
        return True, msg, bias_dict

    def get_bias(self, industry: str) -> Dict[str, float]:
        """获取指定行业的偏差系数"""
        return self._bias_cache.get(industry, {})

    def apply_bias(self, industry: str, metric: str, value: float) -> float:
        """对预估值应用历史偏差校正"""
        bias_entry = self._bias_cache.get(industry, {})
        bias_key = f"{metric}_bias"
        bias = bias_entry.get(bias_key, 1.0)
        return round(value * bias, 4)


# ═══════════════════════════════════════════════════════════════════
# 4-b. 运费估算器 (ShippingEstimator)
# ═══════════════════════════════════════════════════════════════════

class ShippingEstimator:
    """海运/空运/FBA 头程运费估算器。
    基于 2026 年中美航线市场价格数据（来源：航逸国际物流/恒盛通物流）。"""

    # 海运拼箱基准价 (USD/立方米，美西)
    SEA_LCL_USD_PER_CBM = 70.0  # 中间值 65~85
    # 海运整柜 (40HQ 美西，普船）
    SEA_FCL_40HQ = 4100.0  # 中间值 3800~4400
    # 空运基准价 (USD/kg)
    AIR_USD_PER_KG = 5.5  # 中美普货

    # 目的地系数
    DESTINATION_FACTOR = {"US_West": 1.0, "US_Central": 1.15, "US_East": 1.35}

    @staticmethod
    def estimate_shipping(product_name: str, unit_price: float, quantity: int = 100,
                         transport_mode: str = "sea", destination: str = "US_West") -> Dict[str, Any]:
        """估算单件运费。
        Args:
            product_name: 产品名称
            unit_price: 单价 (USD)
            quantity: 批量数量
            transport_mode: 运输方式 sea/air/fba
            destination: 目的地 US_West/US_Central/US_East
        Returns:
            estimated_shipping_per_unit, total_freight, confidence
        """
        dest_factor = ShippingEstimator.DESTINATION_FACTOR.get(destination, 1.0)

        # 根据单价推断体积/重量
        if unit_price > 500:
            vol_per_unit = 0.01   # 高价精密 → 小体积 (0.01 cbm)
            kg_per_unit = 2.0
        elif unit_price > 50:
            vol_per_unit = 0.05   # 中等体积
            kg_per_unit = 5.0
        else:
            vol_per_unit = 0.10   # 低价值工业品 → 大体积
            kg_per_unit = 10.0

        if transport_mode == "air":
            # 空运：按 kg 估算
            total_kg = kg_per_unit * quantity
            total_freight = total_kg * ShippingEstimator.AIR_USD_PER_KG * dest_factor
            per_unit = total_freight / quantity
            confidence = "medium"
        elif transport_mode == "fba":
            # FBA 头程：海运 + 末端派送（海运基础上 + 30%）
            total_vol = vol_per_unit * quantity
            sea_cost = total_vol * ShippingEstimator.SEA_LCL_USD_PER_CBM * dest_factor
            total_freight = sea_cost * 1.30
            per_unit = total_freight / quantity
            confidence = "medium"
        else:
            # 海运拼箱 (sea)
            total_vol = vol_per_unit * quantity
            total_freight = total_vol * ShippingEstimator.SEA_LCL_USD_PER_CBM * dest_factor
            per_unit = total_freight / quantity
            confidence = "high"

        return {
            "estimated_shipping_per_unit": round(per_unit, 2),
            "total_freight": round(total_freight, 2),
            "transport_mode": transport_mode,
            "volume_per_unit_cbm": round(vol_per_unit, 4),
            "kg_per_unit": kg_per_unit,
            "confidence": confidence,
        }


# ═══════════════════════════════════════════════════════════════════
# 4-c. 关税影响计算器 (TariffCalculator)
# ═══════════════════════════════════════════════════════════════════

class TariffCalculator:
    """关税影响估算器。
    基于 2026 年美国对华关税政策数据（来源：Summit Sourcing CN）。
    默认基准：Section 301 关税约 7.5% + 基础关税 ~5% + MPF 0.3464% + HMF 0.125%"""

    BASE_TARIFF = 0.075       # Section 301
    GENERAL_DUTY = 0.05       # 基础关税
    MPF_RATE = 0.003464       # 货物处理费
    HMF_RATE = 0.00125        # 港口维护费

    @staticmethod
    def estimate_landed_cost(fob_price: float, shipping_per_unit: float = 0) -> Dict[str, Any]:
        """计算含税落地成本。
        Args:
            fob_price: FOB 单价 (USD)
            shipping_per_unit: 单件运费 (USD)
        Returns:
            landed_cost, total_duty, effective_tariff_rate
        """
        customs_value = fob_price + shipping_per_unit

        # Section 301 + 基础关税
        section_301 = fob_price * TariffCalculator.BASE_TARIFF
        general_duty = fob_price * TariffCalculator.GENERAL_DUTY

        # MPF: min $29.66, max $575.35 per entry, simplified to per-unit rate
        mpf = customs_value * TariffCalculator.MPF_RATE

        # HMF: 0.125% of customs value
        hmf = customs_value * TariffCalculator.HMF_RATE

        total_duty = section_301 + general_duty + mpf + hmf
        landed_cost = fob_price + shipping_per_unit + total_duty
        effective_rate = (total_duty / fob_price) if fob_price > 0 else 0

        return {
            "fob_price": round(fob_price, 2),
            "shipping_per_unit": round(shipping_per_unit, 2),
            "section_301_duty": round(section_301, 4),
            "general_duty": round(general_duty, 4),
            "mpf": round(mpf, 4),
            "hmf": round(hmf, 4),
            "total_duty": round(total_duty, 4),
            "landed_cost": round(landed_cost, 2),
            "effective_tariff_rate": round(effective_rate * 100, 2),
        }


# ═══════════════════════════════════════════════════════════════════
# 5. 报告输出
# ═══════════════════════════════════════════════════════════════════

class ReportGenerator:

    @staticmethod
    def to_json(cards: List[StrategyCard]) -> str:
        return json.dumps(
            [asdict(c) for c in cards],
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    @staticmethod
    def to_csv(cards: List[StrategyCard]) -> str:
        import csv
        from io import StringIO

        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "产品名称", "品类", "市场", "类型", "生命周期",
            "主推目标", "日预算下限(USD)", "日预算上限(USD)",
            "出价下限(USD)", "出价上限(USD)", "出价策略",
            "CPA上限(USD)", "预期CTR(%)", "CTR区间下限(%)", "CTR区间上限(%)",
            "预期CPC(USD)", "CPC区间下限(USD)", "CPC区间上限(USD)",
            "预期CPM(USD)", "CPM区间下限(USD)", "CPM区间上限(USD)",
            "预期CPA(USD)", "CPA区间下限(USD)", "CPA区间上限(USD)",
            "ROI预估", "综合评分", "模型版本", "已校准", "工业子类", "子类已匹配",
        ])
        for c in cards:
            writer.writerow([
                c.product_name, c.category, c.market, c.business_type,
                c.lifecycle_stage, c.recommended_objective,
                c.daily_budget_range[0], c.daily_budget_range[1],
                c.bid_range[0], c.bid_range[1], c.bid_strategy,
                c.max_cpa,
                c.expected_ctr_pct, c.ctr_range[0], c.ctr_range[1],
                c.expected_cpc, c.cpc_range[0], c.cpc_range[1],
                c.expected_cpm, c.cpm_range[0], c.cpm_range[1],
                c.expected_cpa, c.cpa_range[0], c.cpa_range[1],
                f"{c.roi_estimate:.2f}x", c.priority_score,
                c.model_version, "是" if c.calibration_applied else "否",
                c.subcategory, "是" if c.subcategory_matched else "否",
            ])
        return buf.getvalue()

    @staticmethod
    def to_report(cards: List[StrategyCard]) -> str:
        """生成可读的 Markdown 报告"""

        def _sub_line(card):
            if not card.subcategory:
                return ""
            match_status = "已匹配" if card.subcategory_matched else "未匹配到具体子类"
            return f"- 工业子类: {card.subcategory} ({match_status})"

        lines = [
            f"# Facebook 投流策略报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"产品数量: {len(cards)}",
            "",
            "> 数据来源可信度：基于 2025-2026 行业公开基准，48M+ Meta 广告样本交叉验证",
            "",
        ]
        for i, c in enumerate(cards, 1):
            lines += [
                f"## {i}. {c.product_name} ({c.product_id})",
                f"- 品类: {c.category} | 市场: {c.market} | {c.business_type} | {c.lifecycle_stage}",
                f"{_sub_line(c)}",
                f"- 主推目标: {OBJECTIVE_LABELS.get(c.recommended_objective, c.recommended_objective)}",
                f"- 综合评分: {c.priority_score}/100",
                "",
                "### 预算 & 出价",
                f"- 日预算: ${c.daily_budget_range[0]:.0f} ~ ${c.daily_budget_range[1]:.0f}",
                f"- 出价: ${c.bid_range[0]:.4f} ~ ${c.bid_range[1]:.4f}",
                f"- 出价策略: {c.bid_strategy}",
                f"- CPA 上限: ${c.max_cpa:.2f}",
                "",
                "### KPI 预估",
                f"- 预期 CTR: {c.expected_ctr_pct:.2f}%  (区间: {c.ctr_range[0]:.2f}% – {c.ctr_range[1]:.2f}%)",
                f"- 预期 CPC: ${c.expected_cpc:.3f}  (区间: ${c.cpc_range[0]:.3f} – ${c.cpc_range[1]:.3f} USD)",
                f"- 预期 CPM: ${c.expected_cpm:.2f}  (区间: ${c.cpm_range[0]:.2f} – ${c.cpm_range[1]:.2f} USD)",
                f"- 预期 CPA: ${c.expected_cpa:.2f}  (区间: ${c.cpa_range[0]:.2f} – ${c.cpa_range[1]:.2f} USD)",
                f"- ROI 预估: {c.roi_estimate:.2f}x",
                "",
                "### KPI 数据来源与可信度",
                f"- CTR: {c.kpi_data_sources.get('ctr', {{}}).get('source', 'N/A')}  (可信度: {c.kpi_data_sources.get('ctr', {{}}).get('confidence', '--')})",
                f"- CPC: {c.kpi_data_sources.get('cpc', {{}}).get('source', 'N/A')}  (可信度: {c.kpi_data_sources.get('cpc', {{}}).get('confidence', '--')})",
                f"- CPM: {c.kpi_data_sources.get('cpm', {{}}).get('source', 'N/A')}  (可信度: {c.kpi_data_sources.get('cpm', {{}}).get('confidence', '--')})",
                f"- CPA: {c.kpi_data_sources.get('cpa', {{}}).get('source', 'N/A')}  (可信度: {c.kpi_data_sources.get('cpa', {{}}).get('confidence', '--')})",
                "",
                "### 行业权威基准 (DigitalPoint 2026 / AdBacklog 2025)",
                f"- 行业 CTR: {c.industry_ctr if c.industry_ctr else 'N/A'}%",
                f"- 行业 CPC: ${c.industry_cpc if c.industry_cpc else 'N/A'}",
                f"- 行业 CPA: ${c.industry_cpa if c.industry_cpa else 'N/A'}",
                f"- 行业 ROAS: {f'{c.industry_roas:.2f}x' if c.industry_roas else 'N/A'}",
                "",
                "### 投放设置",
                f"- 受众定向: {', '.join(c.audience_profiles)}",
                f"- Lookalike: {c.lookalike_source}",
                f"- 投放时段: {c.recommended_peak_hours}",
                f"- 版位: {', '.join(c.placement_preference)}",
                "",
                f"数据可信度: {c.data_confidence}",
                "",
                "---",
                "",
            ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 5. CLI 入口
# ═══════════════════════════════════════════════════════════════════

def interactive_cli():
    """交互式命令行入口"""
    print("=" * 60)
    print("  Facebook 投流策略推荐工具 v2.1")
    print("  数据基准: DigitalPoint LLC (2026) + AdBacklog (2025)")
    print("=" * 60)
    print("模式:")
    print("  1. 完整手动输入")
    print("  2. 智能推断（仅需产品名称 + 行业）")
    print("  3. 批量对比")
    print("  4. 加载配置文件")
    print("  5. 行业基准库浏览")
    print("  0. 退出")

    while True:
        try:
            choice = input("\n选择模式 (0-5): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if choice == "0":
            break
        elif choice == "5":
            print("\n行业基准数据速查:\n")
            for name, d in INDUSTRY_DEFAULTS.items():
                ind_ctr = d.get("expected_ctr")
                ind_cpc = d.get("expected_cpc")
                ind_cpa = d.get("expected_cpa")
                ind_roas = d.get("expected_roas")
                ctr_str = f"CTR={ind_ctr:.2f}%" if ind_ctr else "CTR=N/A"
                cpc_str = f"CPC=${ind_cpc:.2f}" if ind_cpc else "CPC=N/A"
                cpa_str = f"CPA=${ind_cpa:.2f}" if ind_cpa else "CPA=N/A"
                roas_str = f"ROAS={ind_roas:.2f}x" if ind_roas else "ROAS=N/A"
                print(
                    f"  {name:6s} | "
                    f"${d['unit_price_usd']:6.2f} | "
                    f"{d['profit_margin_pct']:3.0f}% | "
                    f"{d['target_market']} | "
                    f"{d['business_type']} | "
                    f"{d['lifecycle_stage']} | "
                    f"{ctr_str} | {cpc_str} | {cpa_str} | {roas_str}"
                )
        elif choice in ("1", "2", "3", "4"):
            mode_map = {"1": "manual", "2": "infer", "3": "batch", "4": "config"}
            mode = mode_map[choice]

            engine = AdsStrategyEngine()
            inferrer = SmartInferrer()
            products = []

            if mode == "manual":
                print("\n--- 完整手动输入 ---")
                while True:
                    name = input("产品名称 (空回车结束): ").strip()
                    if not name:
                        break
                    cat = input("产品类别 (行业): ").strip()
                    try:
                        price = float(input("客单价 (USD): "))
                    except ValueError:
                        print("无效数值，跳过")
                        continue
                    try:
                        margin = float(input("利润率 (%): "))
                    except ValueError:
                        margin = 35.0
                    market = input("目标市场 (北美/欧洲/东南亚/中东/南美/大洋洲，默认北美): ") or "北美"
                    bt = input("B2B/B2C (默认 B2C): ") or "B2C"
                    stage = input("生命周期 (新品/成长期/成熟期/衰退期，默认成长期): ") or "成长期"
                    try:
                        days = int(input("转化周期 (天, 默认7): ") or "7")
                    except ValueError:
                        days = 7
                    products.append(Product(
                        id=f"P{len(products)+1:03d}",
                        name=name, category=cat,
                        unit_price_usd=price, profit_margin_pct=margin,
                        target_market=market, business_type=bt,
                        lifecycle_stage=stage, expected_conversion_days=days,
                    ))

            elif mode == "infer":
                print("\n--- 智能推断模式 ---")
                print("可选行业: " + ", ".join(INDUSTRY_DEFAULTS.keys()))
                while True:
                    name = input("产品名称 (空回车结束): ").strip()
                    if not name:
                        break
                    industry = input("所属行业: ").strip()
                    if industry not in INDUSTRY_DEFAULTS:
                        print(f"未知行业，可选: {list(INDUSTRY_DEFAULTS.keys())}")
                        continue
                    cat = input(f"产品类别 (默认={industry}): ").strip() or industry
                    product = inferrer.infer(name, cat, industry)
                    product.id = f"INF{len(products)+1:03d}"
                    products.append(product)
                    print(f"  已添加: {product.name} | ${product.unit_price_usd} | {product.target_market} | {product.business_type}")

            elif mode == "config":
                path = input("配置文件路径 (JSON): ").strip()
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    for item in config:
                        products.append(Product(**item))
                    print(f"已加载 {len(products)} 个产品")
                else:
                    print("文件不存在")

            if not products:
                print("未添加任何产品，返回主菜单")
                continue

            cards = engine.generate_all(products)
            print("\n" + ReportGenerator.to_report(cards))

            # 如果只有一个产品，直接输出
            if len(products) == 1 and mode != "batch":
                continue

        else:
            print("无效选项，请输入 0-5")


if __name__ == "__main__":
    # 若以命令行模式参数运行
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # 批量模式: python fb_ads_recommender.py --report products.json
        config_path = sys.argv[2] if len(sys.argv) > 2 else "products_config.json"
        if os.path.exists(config_path):
            engine = AdsStrategyEngine()
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            products = [Product(**item) for item in config]
            cards = engine.generate_all(products)
            report = ReportGenerator.to_report(cards)
            print(report)
            # 同时写 JSON
            json_out = ReportGenerator.to_json(cards)
            report_path = os.path.join(os.path.dirname(config_path) or ".", "strategy_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(json_out)
            print(f"\nJSON 报告已写入: {report_path}")
        else:
            print(f"配置文件不存在: {config_path}")
    else:
        interactive_cli()

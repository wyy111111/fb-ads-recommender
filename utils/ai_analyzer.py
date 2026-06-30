"""
AI 策略分析引擎 — 基于策略卡片数据生成多维度智能洞察
v1.0 — 内置专家规则系统，模拟 AI 分析师输出
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from fb_ads_recommender import (
    StrategyCard,
    INDUSTRY_DEFAULTS,
    MARKET_PROFILES,
)


# ═══════════════════════════════════════════════════════════════════
# 1. 分析结果数据模型
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RiskItem:
    """单个风险项"""
    level: str          # high / medium / low
    title: str
    detail: str
    mitigation: str


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    area: str           # budget / creative / targeting / bidding
    priority: int       # 1=最高, 5=最低
    suggestion: str
    expected_impact: str
    difficulty: str     # easy / medium / hard


@dataclass
class CreativeAngle:
    """创意角度"""
    angle_name: str
    hook: str           # 钩子文案
    format_fit: str     # 适合的素材格式
    target_emotion: str # 目标情绪


@dataclass
class AIAnalysisResult:
    """AI 分析结果汇总"""
    product_name: str
    category: str
    market: str
    business_type: str

    # 策略摘要
    strategy_summary: str = ""
    one_line_verdict: str = ""

    # 预算分析
    budget_assessment: str = ""
    budget_score: int = 0           # 0-100
    budget_suggestion: str = ""

    # 创意分析
    creative_angles: List[CreativeAngle] = field(default_factory=list)
    creative_best_practices: List[str] = field(default_factory=list)
    creative_formula: str = ""       # 创意公式

    # 风险分析
    risks: List[RiskItem] = field(default_factory=list)
    overall_risk_level: str = ""    # low / medium / high

    # 优化建议
    optimizations: List[OptimizationSuggestion] = field(default_factory=list)

    # 竞品定位
    competitive_position: str = ""
    competitive_advantages: List[str] = field(default_factory=list)
    competitive_watchouts: List[str] = field(default_factory=list)

    # 投放节奏
    campaign_phases: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    model_version: str = "ai-analyzer-v1.0"
    analysis_timestamp: str = ""


# ═══════════════════════════════════════════════════════════════════
# 2. 核心分析引擎
# ═══════════════════════════════════════════════════════════════════

class AIStrategyAnalyzer:
    """AI 策略分析引擎 — 基于规则系统的智能洞察生成器"""

    # ── 行业创意公式库 ──
    CREATIVE_FORMULAS = {
        "工业耗材": "展示生产线实拍 → 对比测试数据 → 询盘引导 → 工厂VR参观",
        "消费电子": "场景痛点 → 产品特写 → 功能演示 → 限时优惠 → 立即购买",
        "服装配饰": "模特穿搭 → 细节放大 → 场景切换 → 好评截图 → 收藏加购",
        "家居用品": "改造前后对比 → 使用步骤 → 多场景展示 → 价格锚点 → 链接点击",
        "美妆护肤": "素颜 vs 妆后 → 成分解析 → 真人测评 → 「你也能做到」",
        "食品饮料": "开箱试吃 → 产地溯源 → 制作过程 → 场景搭配 → 尝鲜优惠",
        "运动户外": "极限场景使用 → 功能拆解 → 达人展示 → 挑战活动 → 加入社群",
        "教育培训": "学员逆袭故事 → 课程片段 → 导师背书 → 限时名额 → 免费试听",
        "软件SaaS": "数据仪表盘 → 功能对比表 → 用户证言 → ROI计算器 → 免费试用",
        "医疗器械": "产品合规认证 → 临床数据 → 专家背书 → 采购指南 → 询盘通道",
        "母婴用品": "萌娃使用场景 → 安全材质 → 妈妈测评 → 限时团购 → 加入育儿群",
        "宠物用品": "宠物使用实拍 → 材质安全 → 对比普通产品 → 铲屎官好评 → 活动入口",
        "汽车配件": "安装前后对比 → 性能测试 → 车型匹配 → 质保承诺 → 专业安装指引",
        "工业电子": "技术规格表 → 样品展示 → 认证资质 → 定制方案 → B2B询盘",
        "其他工业品": "工厂实拍 → 产品规格 → 质检报告 → 装箱出货 → 询盘通道",
    }

    # ── 行业风险矩阵 ──
    RISK_MATRIX: Dict[str, List[Dict[str, str]]] = {
        "industrial": [  # B2B 工业品通用
            {"level": "high", "title": "转化周期长",
             "detail": "B2B工业品平均转化周期21天以上，Facebook归因窗口仅7天",
             "mitigation": "设置14天点击+1天浏览归因，搭配Google Analytics全链路跟踪"},
            {"level": "medium", "title": "受众池过小",
             "detail": "精准定向可能导致受众规模不足（<1000人/day）",
             "mitigation": "开启Advantage+ Audience扩展，放宽10-20%兴趣限制"},
            {"level": "low", "title": "创意疲劳",
             "detail": "B2B买家接触点少，同一创意曝光2周后CTR快速下降",
             "mitigation": "每周更新2-3套素材，按5:3:2分配预算到新/中/旧素材"},
            {"level": "medium", "title": "CPC高于行业均值风险",
             "detail": "B2B工业品CPC通常是B2C的2-3倍，需精细控制",
             "mitigation": "使用Cost Cap出价，设置CPA上限=目标CPA×1.3"},
        ],
        "b2c_hard": [  # B2C 高价/长决策周期
            {"level": "medium", "title": "购物车放弃率高",
             "detail": "高价商品购物车放弃率可达70%+，需多重触达",
             "mitigation": "设置动态再营销广告，配合弃购挽回邮件+折扣码"},
            {"level": "medium", "title": "信任壁垒",
             "detail": "首次购买高价商品需建立信任，直接转化投放ROI偏低",
             "mitigation": "先用视频观看/主页浏览做流量目标预热，再切到转化目标"},
        ],
        "b2c_fast": [  # B2C 快消品
            {"level": "medium", "title": "竞争激烈",
             "detail": "快消品类CPM高，竞品出价频繁波动",
             "mitigation": "设置CPM上限，每周监测竞品广告频率，动态调整出价"},
            {"level": "low", "title": "退货率风险",
             "detail": "冲动消费导致退货率高于预期",
             "mitigation": "产品页明确尺寸/材质说明，视频展示真实使用效果"},
        ],
    }

    @staticmethod
    def analyze(card: StrategyCard) -> AIAnalysisResult:
        """对单个策略卡片执行完整 AI 分析。"""
        from datetime import datetime

        result = AIAnalysisResult(
            product_name=card.product_name,
            category=card.category,
            market=card.market,
            business_type=card.business_type,
            analysis_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        # 1. 策略摘要
        result.strategy_summary = AIStrategyAnalyzer._generate_summary(card)
        result.one_line_verdict = AIStrategyAnalyzer._generate_verdict(card)

        # 2. 预算分析
        budget = AIStrategyAnalyzer._analyze_budget(card)
        result.budget_assessment = budget["assessment"]
        result.budget_score = budget["score"]
        result.budget_suggestion = budget["suggestion"]

        # 3. 创意分析
        result.creative_angles = AIStrategyAnalyzer._generate_creative_angles(card)
        result.creative_best_practices = AIStrategyAnalyzer._get_best_practices(card)
        result.creative_formula = AIStrategyAnalyzer.CREATIVE_FORMULAS.get(
            card.category, "产品亮点 → 用户痛点 → 解决方案 → 行动号召"
        )

        # 4. 风险分析
        result.risks = AIStrategyAnalyzer._assess_risks(card)
        result.overall_risk_level = AIStrategyAnalyzer._calc_risk_level(result.risks)

        # 5. 优化建议
        result.optimizations = AIStrategyAnalyzer._generate_optimizations(card)

        # 6. 竞品定位
        result.competitive_position = AIStrategyAnalyzer._competitive_position(card)
        result.competitive_advantages = AIStrategyAnalyzer._competitive_advantages(card)
        result.competitive_watchouts = AIStrategyAnalyzer._competitive_watchouts(card)

        # 7. 投放节奏
        result.campaign_phases = AIStrategyAnalyzer._campaign_phases(card)

        return result

    @staticmethod
    def _generate_summary(card: StrategyCard) -> str:
        """生成策略摘要（自然语言）"""
        ind_ctr = card.industry_ctr
        ind_cpc = card.industry_cpc
        ind_cpa = card.industry_cpa

        ctr_vs = "高于" if card.expected_ctr_pct >= (ind_ctr or 0) * 0.9 else "略低于"
        cpc_vs = "低于" if card.expected_cpc <= (ind_cpc or 999) * 1.1 else "高于"
        cpa_vs = "低于" if card.expected_cpa <= (ind_cpa or 999) * 1.1 else "高于"

        parts = [
            f"**{card.product_name}**属于**{card.category}**品类，面向**{card.market}**市场的{card.business_type}业务。",
            f"当前为**{card.lifecycle_stage}**阶段，主推**{card.recommended_objective}**目标。",
            f"综合评分**{card.priority_score}/100**，ROI预估**{card.roi_estimate:.2f}x**。",
        ]

        # KPI 对比
        if ind_ctr and ind_cpc and ind_cpa:
            parts.append(
                f"预估CTR {card.expected_ctr_pct:.2f}% ({ctr_vs}行业基准{ind_ctr:.2f}%)，"
                f"CPC ${card.expected_cpc:.3f} USD ({cpc_vs}行业${ind_cpc:.3f} USD)，"
                f"CPA ${card.expected_cpa:.2f} USD ({cpa_vs}行业${ind_cpa:.2f} USD)。"
            )
        elif ind_ctr:
            parts.append(
                f"预估CTR {card.expected_ctr_pct:.2f}% ({ctr_vs}行业基准{ind_ctr:.2f}%)。"
            )

        # 策略建议
        budget_str = f"日预算 ${card.daily_budget_range[0]:.0f}–${card.daily_budget_range[1]:.0f} USD"
        if card.priority_score >= 80:
            parts.append(f"该产品投放潜力优秀，建议{budget_str}，{card.bid_strategy}出价，重点投放{', '.join(card.placement_preference[:2])}版位。")
        elif card.priority_score >= 60:
            parts.append(f"该产品投放潜力中等，建议{budget_str}，{card.bid_strategy}出价，优先测试{card.audience_profiles[0] if card.audience_profiles else '核心受众'}。")
        else:
            parts.append(f"该产品投放潜力需谨慎评估，建议{budget_str}小额测试，{card.bid_strategy}出价控制风险。")

        return "\n\n".join(parts)

    @staticmethod
    def _generate_verdict(card: StrategyCard) -> str:
        """一行定论"""
        if card.priority_score >= 85:
            tier = "强烈推荐加大投放"
        elif card.priority_score >= 70:
            tier = "推荐正常投放，持续优化"
        elif card.priority_score >= 55:
            tier = "谨慎投放，优先测试验证"
        else:
            tier = "建议暂缓投放，优化产品后再试"

        roi_part = f"预期ROI {card.roi_estimate:.1f}x" if card.roi_estimate > 0 else "ROI待验证"

        return f"{tier} | {roi_part} | {card.recommended_objective}目标 | {card.bid_strategy}出价"

    @staticmethod
    def _analyze_budget(card: StrategyCard) -> Dict[str, Any]:
        """预算合理性分析"""
        daily_low, daily_high = card.daily_budget_range
        objective = card.recommended_objective

        # 目标对应的最小有效日预算 (USD)
        MIN_EFFECTIVE_BUDGET = {
            "CONVERSIONS": 30,
            "ENGAGEMENT": 10,
            "REACH": 5,
            "LEAD_GENERATION": 40,
            "APP_INSTALLS": 20,
            "VIDEO_VIEWS": 5,
            "TRAFFIC": 5,
        }

        min_budget = MIN_EFFECTIVE_BUDGET.get(objective, 20)

        if daily_low >= min_budget * 2:
            assessment = f"日预算 ${daily_low:.0f}–${daily_high:.0f} USD 充足，超出{objective}目标最低有效预算(${min_budget} USD/天)2倍以上，可稳定获取转化数据。"
            score = 85
            suggestion = "将 70% 预算分配给已验证的受众+版位组合，30% 用于探索新受众和创意测试。"
        elif daily_low >= min_budget:
            assessment = f"日预算 ${daily_low:.0f}–${daily_high:.0f} USD 合理，达到{objective}目标最低有效预算(${min_budget} USD/天)，可满足基本学习需求。"
            score = 65
            suggestion = "建议集中预算在1-2个广告组，避免过度拆分导致学习不足。"
        else:
            assessment = f"日预算 ${daily_low:.0f}–${daily_high:.0f} USD 偏低，低于{objective}目标建议最低预算(${min_budget} USD/天)，可能影响广告学习效果和转化数据稳定性。"
            score = 35
            suggestion = f"建议将日预算提升至至少 ${min_budget} USD，或切换为 {_min_budget_objective(objective)} 目标以获得更优的投放效率。"

        # B2B 额外建议
        if card.business_type == "B2B":
            assessment += " B2B业务建议设置更长的学习期（7-14天），不要在前3天根据CPA波动频繁调整。"
            suggestion += " 同时建议分配15-20%预算给再营销受众（网站访客/视频观看者）。"

        return {"assessment": assessment, "score": score, "suggestion": suggestion}

    @staticmethod
    def _generate_creative_angles(card: StrategyCard) -> List[CreativeAngle]:
        """生成创意角度建议"""
        category = card.category
        bt = card.business_type
        stage = card.lifecycle_stage

        # 通用角度库
        angle_pool = []

        # B2B 专属角度
        if bt == "B2B":
            angle_pool += [
                CreativeAngle(
                    angle_name="工厂实力展示",
                    hook="从原料到成品，每一道工序我们都有质检把控",
                    format_fit="视频广告 (15-30s)",
                    target_emotion="信任感+专业性",
                ),
                CreativeAngle(
                    angle_name="客户案例背书",
                    hook="已经服务全球{XX}家企业，这是他们的真实反馈",
                    format_fit="轮播广告 (Carousel)",
                    target_emotion="社会认同+安全感",
                ),
                CreativeAngle(
                    angle_name="定制方案",
                    hook="不需要标准品？我们支持OEM/ODM定制，7天出样",
                    format_fit="单图广告 (Single Image)",
                    target_emotion="掌控感+个性化",
                ),
                CreativeAngle(
                    angle_name="免费样品/目录",
                    hook="不确定质量？先拿样品测试，满意再下单",
                    format_fit="线索表单广告 (Lead Form)",
                    target_emotion="0风险+好奇心",
                ),
            ]

        # B2C 专属角度
        if bt == "B2C":
            angle_pool += [
                CreativeAngle(
                    angle_name="痛点解决",
                    hook="还在为{XX}烦恼？用这个，5分钟解决",
                    format_fit="视频广告 (15s, 9:16)",
                    target_emotion="焦虑→解脱",
                ),
                CreativeAngle(
                    angle_name="场景化展示",
                    hook="想象一下，{XX场景}有了它是什么样的体验",
                    format_fit="轮播广告 (Carousel, 4:5)",
                    target_emotion="向往+渴望",
                ),
                CreativeAngle(
                    angle_name="性价比对比",
                    hook="花${XX}就能买到${XXX}的品质，为什么还要多花钱？",
                    format_fit="单图广告 (1:1)",
                    target_emotion="精明感+捡漏心理",
                ),
                CreativeAngle(
                    angle_name="限时稀缺",
                    hook="首批500件已售罄，第二批补货仅剩{XX}件",
                    format_fit="视频广告 (Reels, 9:16)",
                    target_emotion="紧迫感+FOMO",
                ),
            ]

        # 按生命周期筛选
        if stage == "新品":
            angle_pool = [a for a in angle_pool if a.angle_name in ["痛点解决", "场景化展示", "工厂实力展示", "免费样品/目录"]]
        elif stage == "成长期":
            angle_pool = [a for a in angle_pool if a.angle_name in ["客户案例背书", "性价比对比", "定制方案"]]
        elif stage == "成熟期":
            angle_pool = [a for a in angle_pool if a.angle_name in ["限时稀缺", "性价比对比", "客户案例背书"]]

        # 确保至少有3个
        if len(angle_pool) < 3:
            angle_pool += [
                CreativeAngle(angle_name="产品测评", hook="真实用户{XX}天后体验：这些细节让我意外", format_fit="视频广告", target_emotion="好奇心+信任"),
                CreativeAngle(angle_name="教程/技巧", hook="90%的人不知道的{XX}使用技巧", format_fit="轮播广告", target_emotion="实用价值+分享欲"),
            ]

        return angle_pool[:5]  # 最多5个

    @staticmethod
    def _get_best_practices(card: StrategyCard) -> List[str]:
        """创意最佳实践"""
        practices = [
            "前3秒必须出现产品核心卖点或问题场景，前3秒流失率决定视频完播率",
            "所有视频素材必须添加字幕，85%用户静音观看",
            f"CTA按钮与素材内容高度一致：{card.creative_cta if card.creative_cta else 'Shop Now'}",
        ]

        if card.business_type == "B2B":
            practices += [
                "B2B买家关注技术参数和认证：素材中必须展示关键认证标识（CE/FDA/ISO等）",
                "Lead Form 广告：表单字段≤5个（姓名/公司/邮箱/电话/需求量），减少放弃率",
            ]
        else:
            practices += [
                "移动端优先设计：关键信息放在画面中央60%区域",
                "使用UGC（用户生成内容）风格素材，原生感素材比精美广告片CTR高28%（Meta 2025数据）",
                "轮播广告每张卡片独立卖点，引导用户滑动查看更多",
            ]

        # 数据支撑
        practices.append(
            f"建议同时投放2-3套素材，每周根据CTR数据淘汰底部20%，补充新素材"
        )

        return practices

    @staticmethod
    def _assess_risks(card: StrategyCard) -> List[RiskItem]:
        """风险评估"""
        risks = []

        # 1. 评分风险
        if card.priority_score < 60:
            risks.append(RiskItem(
                level="high", title="综合评分偏低",
                detail=f"评分 {card.priority_score}/100，低于推荐投放阈值(60分)。",
                mitigation=f"先优化产品定价或利润率，当前利润率约{card.max_cpa / max(card.unit_price if hasattr(card,'unit_price') else card.max_cpa*10, 0.01)*100:.0f}%可能偏低。"
            ))

        # 2. CPC风险
        if card.industry_cpc and card.expected_cpc > card.industry_cpc * 1.3:
            risks.append(RiskItem(
                level="medium", title="CPC显著高于行业基准",
                detail=f"预期CPC ${card.expected_cpc:.3f} USD 高于行业${card.industry_cpc:.3f} USD的30%+",
                mitigation="使用Cost Cap出价控制单次点击成本；优化受众定向减少无效曝光。"
            ))

        # 3. CPA风险
        if card.industry_cpa and card.expected_cpa > card.industry_cpa * 1.5:
            risks.append(RiskItem(
                level="high", title="CPA严重超标",
                detail=f"预期CPA ${card.expected_cpa:.2f} USD 远超行业${card.industry_cpa:.2f} USD",
                mitigation="设置严格的CPA上限(cost cap)，先以Traffic或Engagement目标积累数据后再切Conversion。"
            ))

        # 4. B2B 特有风险
        if card.business_type == "B2B":
            risks.append(RiskItem(
                level="medium", title="B2B归因黑洞",
                detail="B2B交易常通过邮件/电话/展会完成，Facebook无法追踪线下转化",
                mitigation="接入CRM offline conversions API；使用UTM参数追踪；设置Lead为中间目标。"
            ))
            risks.append(RiskItem(
                level="medium", title="受众规模限制",
                detail=f"B2B精准定向可能导致日展示量<5000，影响算法学习",
                mitigation="结合Lookalike受众(1-3%)扩展；开启Advantage+ Audience。"
            ))

        # 5. 小众品类风险
        niche_info = getattr(card, 'niche_adjustment_info', None)
        if niche_info and niche_info.get("applied"):
            risks.append(RiskItem(
                level="medium", title="小众品类预估不确定性",
                detail=f"属于{niche_info.get('category','')}，Facebook无对应类目，KPI预估置信度较低",
                mitigation="以50%预算做探索投放，收集7天实际数据后再校准模型参数。"
            ))

        # 6. 通用风险
        risks.append(RiskItem(
            level="low", title="iOS14+信号丢失",
            detail="iOS用户ATT授权率约30%，影响转化追踪和再营销精准度",
            mitigation="已配置8个转化事件优先级；启用Aggregated Event Measurement。"
        ))

        return risks

    @staticmethod
    def _calc_risk_level(risks: List[RiskItem]) -> str:
        if any(r.level == "high" for r in risks):
            return "high"
        high_med = sum(1 for r in risks if r.level in ("high", "medium"))
        if high_med >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _generate_optimizations(card: StrategyCard) -> List[OptimizationSuggestion]:
        """生成优化建议列表"""
        opts = []

        # 预算优化
        if card.daily_budget_range[0] < 50:
            opts.append(OptimizationSuggestion(
                area="budget", priority=1,
                suggestion=f"日预算从${card.daily_budget_range[0]:.0f}提升至$50+ USD，保证每天至少获取15-25次转化以稳定算法学习",
                expected_impact="CPA波动降低30-50%，转化成本更稳定",
                difficulty="easy",
            ))

        # 受众优化
        if card.business_type == "B2B":
            opts.append(OptimizationSuggestion(
                area="targeting", priority=2,
                suggestion="创建3层再营销漏斗：网站访客(30天)→视频观看75%(90天)→Lead未转化(180天)，分别设置不同出价",
                expected_impact="整体转化率提升20-40%",
                difficulty="medium",
            ))

        # 创意优化
        opts.append(OptimizationSuggestion(
            area="creative", priority=3,
            suggestion="启动动态创意测试(Dynamic Creative)，同时测试3个标题×3个图片×2个CTA共18种组合",
            expected_impact="快速找到最佳素材组合，CTR预期提升15-25%",
            difficulty="easy",
        ))

        # 出价优化
        if card.priority_score >= 70:
            opts.append(OptimizationSuggestion(
                area="bidding", priority=4,
                suggestion="从{bid}切换为Cost Cap with min ROAS，设置目标ROAS={roi}x".format(
                    bid=card.bid_strategy,
                    roi=max(1.5, card.roi_estimate * 0.8),
                ),
                expected_impact="兼顾转化量与ROI，防止CPA失控",
                difficulty="medium",
            ))

        # 版位优化
        opts.append(OptimizationSuggestion(
            area="targeting", priority=5,
            suggestion="关闭Audience Network版位（如果已开启），该版位无效点击率高且转化质量低",
            expected_impact="CPC可降低10-15%，转化率更真实",
            difficulty="easy",
        ))

        return opts

    @staticmethod
    def _competitive_position(card: StrategyCard) -> str:
        """竞品定位分析"""
        if card.business_type == "B2B":
            if card.priority_score >= 80:
                return "在B2B工业品赛道中处于**优势区**——ROI预估高于行业均值，产品定价和利润率具备竞争力。建议以「品质+定制能力」为核心差异化点，避开纯价格竞争。"
            elif card.priority_score >= 60:
                return "在B2B赛道中处于**竞争区**——与行业平均水平接近。需要在「响应速度」「最小起订量灵活性」「样品支持」等软性服务上建立优势。"
            else:
                return "在B2B赛道中处于**挑战区**——CPC/CPA高于行业均值。建议先优化产品定价或生产成本，或转向竞争较小的细分市场（如特定材质/规格的专业品类）。"
        else:
            if card.priority_score >= 80:
                return "在B2C消费品赛道中处于**增长区**——ROI和CTR均优于行业平均。建议加快投放节奏，抢占品类心智。关注竞品动态，维持素材更新频率。"
            elif card.priority_score >= 60:
                return "在B2C赛道中处于**混战区**——与大量竞品直接竞争。需要通过独特的品牌故事或视觉风格建立差异化，避免陷入纯价格战。"
            else:
                return "在B2C赛道中处于**红海区**——竞争激烈且ROI偏低。建议重新定位目标受众或切换到细分利基市场。考虑使用UGC+KOL组合策略降低CPM。"

    @staticmethod
    def _competitive_advantages(card: StrategyCard) -> List[str]:
        """竞争优势"""
        advantages = []
        if card.roi_estimate > 3:
            advantages.append(f"ROI预估 {card.roi_estimate:.1f}x，高于行业均值，具备持续投放的经济可行性")
        if card.expected_ctr_pct > 1.5:
            advantages.append(f"CTR预估 {card.expected_ctr_pct:.2f}%，高于1.5%阈值，说明产品与受众匹配度良好")
        if card.business_type == "B2B":
            advantages.append("B2B业务天然具有高客单价和高客户生命周期价值，LTV:CAC比值通常优于B2C")
        if card.priority_score >= 75:
            advantages.append("综合评分优秀，市场机会窗口明确，建议快速行动抢占先机")
        if not advantages:
            advantages.append("需要通过小规模测试验证真实数据后再评估优势")
        return advantages

    @staticmethod
    def _competitive_watchouts(card: StrategyCard) -> List[str]:
        """竞品警示"""
        watchouts = []
        if card.business_type == "B2B":
            watchouts.append("阿里巴巴国际站/Amazon Business的B2B买家也在增加，需评估是否多平台布局")
            watchouts.append("同行可能在用更低价格或更灵活的支付条款（如OA 30/60天）抢单")
        else:
            watchouts.append("TikTok Shop正在瓜分社媒电商流量，考虑同步测试TikTok广告")
            watchouts.append("亚马逊同品类卖家可能同时在投Facebook引流，CPM可能被推高")

        if card.industry_ctr and card.expected_ctr_pct < card.industry_ctr:
            watchouts.append(f"CTR低于行业基准（{card.expected_ctr_pct:.2f}% vs {card.industry_ctr:.2f}%），竞品素材可能更具吸引力，需重点关注创意迭代")
        return watchouts

    @staticmethod
    def _campaign_phases(card: StrategyCard) -> List[Dict[str, Any]]:
        """投放阶段规划"""
        daily = card.daily_budget_range[1]

        phases = [
            {
                "phase": "Phase 1: 测试期 (第1-7天)",
                "budget_pct": 40,
                "daily_usd": round(daily * 0.4),
                "objective": "Traffic 或 Engagement",
                "actions": [
                    "投放2-3套不同创意角度的素材",
                    "测试3组不同受众（核心兴趣/Lookalike/广泛定向）",
                    "不做任何出价调整，让算法充分学习",
                    f"每天至少获取500次展示以获取统计显著性",
                ],
                "success_criteria": f"CTR ≥ {card.expected_ctr_pct * 0.7:.2f}% 且 CPC ≤ ${card.expected_cpc * 1.5:.3f} USD",
            },
            {
                "phase": "Phase 2: 优化期 (第8-14天)",
                "budget_pct": 35,
                "daily_usd": round(daily * 0.35),
                "objective": card.recommended_objective,
                "actions": [
                    "淘汰CTR后20%的素材，用Top素材扩展新受众",
                    "根据Phase 1数据调整出价策略",
                    "设置再营销广告组（覆盖已互动但未转化用户）",
                    "分析分时数据，优化投放时段",
                ],
                "success_criteria": f"CPA ≤ ${card.expected_cpa:.2f} USD 且 转化量 ≥ 15/周",
            },
            {
                "phase": "Phase 3: 放量期 (第15天+)",
                "budget_pct": 25,
                "daily_usd": round(daily * 0.25),
                "objective": "Conversions (价值优化)",
                "actions": [
                    "将已验证的受众+创意组合规模化",
                    "开启CBO(Campaign Budget Optimization)自动分配预算",
                    "设置min ROAS出价保护利润率",
                    "每周更新一次新素材，防止疲劳",
                ],
                "success_criteria": f"ROAS ≥ {max(1.5, card.roi_estimate * 0.8):.1f}x 且 CPA稳定在 {{card.expected_cpa:.2f}} USD ±20%",
            },
        ]

        return phases


def _min_budget_objective(objective: str) -> str:
    """当预算不足时推荐的降级目标"""
    mapping = {
        "CONVERSIONS": "Traffic（流量）或 Video Views（视频观看）",
        "LEAD_GENERATION": "Traffic（流量）先收集网站访问数据",
        "APP_INSTALLS": "Reach（覆盖）先提升品牌认知",
    }
    return mapping.get(objective, "Traffic（流量）")

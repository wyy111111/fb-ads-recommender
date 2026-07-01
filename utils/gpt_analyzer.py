"""
GPT 外部 AI 分析器（本地使用，不入库）

通过 OpenAI API 对策略卡片做补充分析（文案创意 / 跨行业类比 / 头脑风暴角度）。
规则引擎（ai_analyzer.py）已覆盖：风险矩阵 / 创意公式 / 预算评估 / 竞品定位 / 投放阶段规划。

用法：
  1. 在项目根目录创建 .env 文件，写入 OPENAI_API_KEY=sk-xxx
  2. 或设置系统环境变量 OPENAI_API_KEY
  3. 在 Streamlit 策略结果页打开"GPT 补充分析"开关
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

# 延迟导入，不影响无 OpenAI SDK 环境下的正常运行
_openai_available = False
try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    pass


class GPTAnalyzer:
    """调用外部 AI（DeepSeek / OpenAI）对策略卡片做创意和文案维度的补充分析。"""

    # ── 可配置项：根据 KEY 自动选择提供商 ──
    _PROVIDER_CONFIG: Dict[str, Dict[str, Any]] = {
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "max_tokens": 1500,
        },
        "openai": {
            "base_url": None,  # 使用默认
            "model": "gpt-4o",
            "max_tokens": 1500,
        },
    }

    TEMPERATURE = 0.7
    TIMEOUT = 45  # 秒

    @classmethod
    def _detect_provider(cls) -> Optional[tuple]:
        """检测可用提供商，返回 (client, provider_name, model, max_tokens)。"""
        if not _openai_available:
            return None

        api_key = os.getenv("DEEPSEEK_API_KEY") or ""
        if api_key:
            cfg = cls._PROVIDER_CONFIG["deepseek"]
            client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=cls.TIMEOUT)
            return (client, "deepseek", cfg["model"], cfg["max_tokens"])

        api_key = os.getenv("OPENAI_API_KEY") or ""
        if not api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
            except ImportError:
                pass

        if not api_key:
            return None

        # 判断 key 前缀决定提供商
        if api_key.startswith("sk-") and len(api_key) < 50:
            cfg = cls._PROVIDER_CONFIG["deepseek"]
            client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=cls.TIMEOUT)
            return (client, "deepseek", cfg["model"], cfg["max_tokens"])

        cfg = cls._PROVIDER_CONFIG["openai"]
        client = OpenAI(api_key=api_key, timeout=cls.TIMEOUT)
        return (client, "openai", cfg["model"], cfg["max_tokens"])

    @classmethod
    def _build_system_prompt(cls) -> str:
        return (
            "你是 Facebook 投流策略高级顾问，专注 B2B/B2C 广告优化。\n"
            "规则引擎已完成：风险矩阵评估、行业创意公式配对、预算评价、竞品定位建议、投放阶段规划。\n"
            "你的任务是补充以下维度：\n"
            "1. 广告文案创意（2-3 条可直接使用的 Facebook 广告文案建议）\n"
            "2. 跨行业类比灵感（借鉴其他行业的成功打法）\n"
            "3. 容易被忽视的优化盲点\n"
            "输出使用中文，结构清晰，每条建议不超过 100 字。"
        )

    @classmethod
    def _build_user_prompt(cls, cards_json: str, product_info: str) -> str:
        return (
            f"产品信息：\n{product_info}\n\n"
            f"策略卡片（JSON）：\n{cards_json}\n\n"
            "请给出 3 个章节：文案创意建议、跨行业灵感、优化盲点提示。"
        )

    @classmethod
    def analyze(cls, cards: List, product_name: str = "",
                industry: str = "", unit_price: float = 0.0,
                margin_pct: float = 0.0) -> Optional[str]:
        """
        调用 GPT 做补充分析。

        Args:
            cards: 策略卡片列表
            product_name: 产品名
            industry: 行业类别
            unit_price: 单价 (USD)
            margin_pct: 利润率 (%)

        Returns:
            分析文本，失败返回 None
        """
        prov = cls._detect_provider()
        if prov is None:
            return None
        client, _, model, max_tokens = prov

        # 精简卡片数据，避免 token 浪费
        slim_cards = []
        for c in cards:
            slim_cards.append({
                "objective": getattr(c, "objective_display", getattr(c, "objective", "")),
                "daily_budget": getattr(c, "display_budget", ""),
                "target_cpa": getattr(c, "target_cpa", ""),
                "ctr_pct": getattr(c, "ctr_pct", ""),
                "cvr_pct": getattr(c, "cvr_pct", ""),
                "ad_angels": getattr(c, "creative_angles", []),
                "risk_level": getattr(c, "risk_level", ""),
                "lifecycle": getattr(c, "lifecycle_stage", ""),
                "campaign_structure": getattr(c, "campaign_structure", ""),
            })

        product_info = (
            f"产品：{product_name}，行业：{industry}，"
            f"单价：${unit_price:.2f} USD，利润率：{margin_pct:.0f}%"
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": cls._build_system_prompt()},
                    {"role": "user", "content": cls._build_user_prompt(
                        json.dumps(slim_cards, ensure_ascii=False, indent=2),
                        product_info,
                    )},
                ],
                max_tokens=max_tokens,
                temperature=cls.TEMPERATURE,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[GPT 调用失败] {e}"

    # ── 新增：策略卡片 AI 建议生成 ──
    @classmethod
    def generate_card_suggestions(
        cls,
        card_dict: dict,
        product_name: str,
        product_category: str,
        business_type: str,
    ) -> Optional[dict]:
        """
        调用 AI 生成单张策略卡片的素材推荐和执行指南。

        Args:
            card_dict: 策略卡片关键字段（objective, daily_budget, market, ctr_pct 等）
            product_name: 产品名称
            product_category: 行业类别
            business_type: B2B / B2C

        Returns:
            {
                "ai_creative": {"format": str, "ratio": str, "cta": str, "tips": [str]},
                "ai_execution": {"steps": [str], "budget_split": str, "testing_strategy": str}
            }
            失败返回 None
        """
        prov = cls._detect_provider()
        if prov is None:
            return None
        client, provider_name, model, _ = prov

        system = (
            "你是 Facebook 广告投流专家。你需要根据产品信息和策略卡片数据，输出中文投放建议。\n"
            "输出必须为严格的 JSON 格式，包含两部分：\n\n"
            "1. ai_creative: 素材推荐\n"
            "   - format: 素材格式（单图/轮播/视频/合集）\n"
            "   - ratio: 推荐比例（1:1/4:5/9:16/16:9）\n"
            "   - cta: 推荐 CTA 按钮文案\n"
            "   - tips: 3-5 条素材制作建议，每条不超过 80 字\n\n"
            "2. ai_execution: 投放执行指南\n"
            "   - steps: 5-6 步操作步骤，每条不超过 80 字\n"
            "   - budget_split: 预算分配建议，不超过 80 字\n"
            "   - testing_strategy: A/B 测试策略，不超过 80 字\n\n"
            "要求：所有文案用中文输出，简洁有力，每条不超过 80 字。只输出 JSON，不要有任何额外文字。"
        )

        user = (
            f"产品名称：{product_name}\n"
            f"行业类别：{product_category}\n"
            f"业务类型：{business_type}\n"
            f"策略卡片数据：{json.dumps(card_dict, ensure_ascii=False, indent=2)}"
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=1200,
                temperature=cls.TEMPERATURE,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            # 校验必要字段
            creative = data.get("ai_creative", {})
            execution = data.get("ai_execution", {})
            if not creative or not execution:
                return None
            if not all(k in creative for k in ("format", "ratio", "cta", "tips")):
                return None
            if not all(k in execution for k in ("steps", "budget_split", "testing_strategy")):
                return None

            return {
                "ai_creative": creative,
                "ai_execution": execution,
            }
        except Exception:
            return None

    # ── GPT 市场数据搜索 ──
    @classmethod
    def search_market_data(cls, query: str) -> Optional[Dict[str, Any]]:
        """
        调用 GPT 搜索产品市场数据（单价、利润率）。

        Args:
            query: 搜索查询词，如 "drone price USD profit margin"

        Returns:
            dict 包含 unit_price_usd, profit_margin_pct, data_source 等字段
            失败返回 None
        """
        prov = cls._detect_provider()
        if prov is None:
            return None
        client, provider_name, model, max_tokens = prov

        system = (
            "你是市场调研专家，负责从公开信息中估算产品市场参考价和行业利润率。\n"
            "用户会给你一个搜索查询词，你需要返回：\n"
            "1. 产品单价（USD）\n"
            "2. 行业平均利润率（%）\n"
            "3. 数据来源说明（如 '基于 Amazon / Alibaba / industry reports'）\n"
            "4. 可选：单价区间（low/high）\n"
            "输出必须是 JSON 格式，只包含以下字段：\n"
            "- unit_price_usd: float\n"
            "- profit_margin_pct: float\n"
            "- unit_price_low: float (可选)\n"
            "- unit_price_high: float (可选)\n"
            "- data_source: string\n"
            "如果无法确定，返回 null 值。"
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"搜索查询：{query}"},
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            # 验证必要字段
            if "unit_price_usd" not in data or "profit_margin_pct" not in data:
                return None

            # 确保数值类型
            data["unit_price_usd"] = float(data["unit_price_usd"])
            data["profit_margin_pct"] = float(data["profit_margin_pct"])
            if "unit_price_low" in data and data["unit_price_low"] is not None:
                data["unit_price_low"] = float(data["unit_price_low"])
            if "unit_price_high" in data and data["unit_price_high"] is not None:
                data["unit_price_high"] = float(data["unit_price_high"])

            data["data_source"] = data.get("data_source", f"GPT web search: {query}")
            return data

        except Exception as e:
            return None

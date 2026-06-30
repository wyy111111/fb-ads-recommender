---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 306d6d8a0f34c9f1907121b340ed06b5_ad61f443737f11f1897e5254002afed2
    ReservedCode1: IPCZULiTmRDVCuSDkRLlUnZiIt7EoG6CQR4oTG/XkDFdncps3E74L2rsQhNlgvOUuPmnwPK5EGrBuJ7t2H4nkaWtUOAwVshj1IQyJSodXjKY0r4QPVmQJTagxYFSRpzKg3aad4ADVxt54pbVembkxFGuVn9ocO7NhRRXD9nJECiJkkzsYPazPlNTABg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 306d6d8a0f34c9f1907121b340ed06b5_ad61f443737f11f1897e5254002afed2
    ReservedCode2: IPCZULiTmRDVCuSDkRLlUnZiIt7EoG6CQR4oTG/XkDFdncps3E74L2rsQhNlgvOUuPmnwPK5EGrBuJ7t2H4nkaWtUOAwVshj1IQyJSodXjKY0r4QPVmQJTagxYFSRpzKg3aad4ADVxt54pbVembkxFGuVn9ocO7NhRRXD9nJECiJkkzsYPazPlNTABg=
---



# Facebook 投流策略推荐工具 v2.0

基于 facebook-ads-analyzer 开源核心逻辑的通用多产品 Facebook 投流策略推荐引擎。支持交互式输入、智能行业推断、批量对比分析。

## 快速开始

```bash
cd output
python fb_ads_recommender.py
```

运行后进入交互式菜单，支持 5 种模式：

| 选项 | 模式 | 说明 |
|:----:|------|------|
| 1 | 完整输入 | 逐项填写产品信息，实时生成策略卡片 |
| 2 | 智能推断 | 仅输入产品名称 + 行业，自动推断所有参数 |
| 3 | 批量模式 | 一行一个产品，批量生成横向对比表 |
| 4 | 加载配置 | 从 `products_config.json` 批量加载产品 |
| 5 | 行业库 | 查看内置 13 个行业的基准参数 |

## 文件说明

| 文件 | 用途 |
|------|------|
| `fb_ads_recommender.py` | 主引擎 — 交互式 CLI + 策略生成 + 报告输出 |
| `products_config.json` | 产品配置文件（7 个跨行业示例产品） |
| `strategy_report.json` | 运行后生成的 JSON 策略报告 |
| `strategy_report.txt` | 运行后生成的纯文本报告 |

## 内置行业基准数据库（13 个行业）

智能推断模式下，仅需输入产品名称和行业，系统自动填充默认参数：

| # | 行业 | 默认客单价 | 默认利润率 | B2B/B2C | 默认市场 | 转化周期 |
|:-:|------|:---------:|:---------:|:-------:|:--------:|:--------:|
| 1 | 工业耗材 | $3.50 | 35% | B2B | 北美 | 21天 |
| 2 | 消费电子 | $45.00 | 22% | B2C | 北美 | 5天 |
| 3 | 服装配饰 | $28.00 | 55% | B2C | 北美 | 3天 |
| 4 | 家居用品 | $35.00 | 40% | B2C | 北美 | 7天 |
| 5 | 美妆护肤 | $22.00 | 60% | B2C | 北美 | 4天 |
| 6 | 食品饮料 | $15.00 | 30% | B2C | 北美 | 3天 |
| 7 | 运动户外 | $55.00 | 38% | B2C | 欧洲 | 6天 |
| 8 | 教育培训 | $120.00 | 65% | B2C | 北美 | 14天 |
| 9 | 软件SaaS | $99.00 | 75% | B2B | 北美 | 21天 |
| 10 | 医疗器械 | $250.00 | 45% | B2B | 北美 | 45天 |
| 11 | 母婴用品 | $25.00 | 42% | B2C | 北美 | 4天 |
| 12 | 宠物用品 | $20.00 | 45% | B2C | 北美 | 3天 |
| 13 | 汽车配件 | $80.00 | 30% | B2C | 欧洲 | 10天 |

## 策略引擎逻辑

### 广告目标权重（按生命周期）

| 生命周期 | 互动目标 | 转化目标 | 流量目标 |
|----------|:--------:|:--------:|:--------:|
| 新品     | 50%      | 20%      | 30%      |
| 成长期   | 30%      | 45%      | 25%      |
| 成熟期   | 10%      | 65%      | 25%      |
| 衰退期   | 5%       | 80%      | 15%      |

### B2B vs B2C 差异化策略

| 维度 | B2B | B2C |
|------|-----|-----|
| 受众 | 采购经理/企业主/批发商 | 兴趣人群/竞品粉丝/电商用户 |
| 出价策略 | target_cost | lowest_cost |
| 出价系数 | ×1.15 | ×1.0 |
| Lookalike 源 | 客户列表/展会名片 | 网站访客/加购用户 |
| 基准转化率 | 1.5% | 3.0% |

### CPA 上限 & ROI 预估

```
CPA 上限 = 客单价 × 利润率 × 0.40
ROI 预估 = (客单价 × 利润率) / 预期 CPA
```

### 综合优先级评分（0-100 分）

多因子加权：
- 生命周期阶段：新品 20 / 成长期 25 / 成熟期 15 / 衰退期 5
- 利润率贡献：最高 30 分
- 客单价贡献：最高 15 分
- ROI 贡献：最高 35 分

### 目标市场差异化

| 市场 | 日预算系数 | 基准 CPC | 基准 CPM | 基准 CTR |
|------|:---------:|:--------:|:--------:|:--------:|
| 北美 | 1.00 | $0.85 | $12.50 | 1.20% |
| 欧洲 | 0.85 | $0.65 | $10.00 | 1.35% |
| 东南亚 | 0.45 | $0.18 | $3.50 | 1.80% |
| 中东 | 0.55 | $0.30 | $5.00 | 1.50% |
| 南美 | 0.40 | $0.15 | $3.00 | 1.70% |
| 大洋洲 | 0.90 | $0.75 | $11.00 | 1.25% |

## 策略卡片输出内容

每个产品生成完整策略卡片，包含：
- 推荐广告目标（互动/转化/流量）+ 权重分解
- 建议日预算区间（USD）
- 建议出价区间 + 出价策略
- 可承受 CPA 上限
- 推荐受众特征 + Lookalike 源 + 版位偏好
- 推荐投放时段
- 预期 CTR / CPC / CPM / CPA 基准值
- ROI 预估（倍数）
- 综合优先级评分（0-100）

## 批量模式示例

运行模式 3，输入：
```
蓝牙耳机 | 消费电子 | 消费电子
抗衰老精华 | 美妆护肤 | 美妆护肤
露营吊床 | 运动户外 | 运动户外
```

自动生成 3 个产品的策略卡片 + 横向对比表格。

## 在代码中集成

```python
from fb_ads_recommender import AdsStrategyEngine, SmartInferrer, ReportGenerator, Product

# 智能推断
product = SmartInferrer.infer("蓝牙耳机 Pro", "消费电子", "消费电子")

# 生成策略
engine = AdsStrategyEngine()
card = engine.generate(product)

# 输出
print(ReportGenerator.to_json([card]))
```

## 依赖

- Python 3.8+
- 标准库，无第三方依赖
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*

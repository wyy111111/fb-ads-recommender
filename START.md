---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 306d6d8a0f34c9f1907121b340ed06b5_af16e951737f11f1aabe5254007bceed
    ReservedCode1: sRYQ9wJKsWw3oRqah3iKuis3Fv134xSj9INENEK15LDfSio4sRf96nW2EBJ6Yqb2CJTzo+4dZ7S75LVxRUyY4R1W41/WludD2mMVLxTZPa342aCKhuzADAIUyakMGmOv+qWpQBxMgSD/xLt9n7/8Y3wdBvnpG78dXSXomw4I55+4e/Uh8FiAGOkpRsI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 306d6d8a0f34c9f1907121b340ed06b5_af16e951737f11f1aabe5254007bceed
    ReservedCode2: sRYQ9wJKsWw3oRqah3iKuis3Fv134xSj9INENEK15LDfSio4sRf96nW2EBJ6Yqb2CJTzo+4dZ7S75LVxRUyY4R1W41/WludD2mMVLxTZPa342aCKhuzADAIUyakMGmOv+qWpQBxMgSD/xLt9n7/8Y3wdBvnpG78dXSXomw4I55+4e/Uh8FiAGOkpRsI=
---

# Facebook 投流策略推荐工具 — 启动指南

## 环境要求

- Python 3.8+
- Windows / macOS / Linux

## 一键启动

```bash
# 1. 进入 output 目录
cd output

# 2. 安装依赖（仅首次）
pip install -r requirements.txt

# 3. 启动 Web 界面
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 使用流程

### 1. 添加产品（产品管理页）

两种方式：

- **完整输入**：逐项填写产品名称、类别、客单价、利润率、目标市场、B2B/B2C、生命周期、转化周期
- **智能推断**：只需输入产品名称 + 选择行业，系统自动填充所有参数（基于内置 13 个行业基准数据）

支持添加多个产品，右侧面板可随时删除。

### 2. 生成策略

点击「生成策略」按钮，引擎基于 facebook-ads-analyzer 核心逻辑为每个产品生成差异化投流策略。

### 3. 查看结果（策略结果页）

- **策略卡片模式**：每个产品一张详细卡片，包含广告目标、日预算、出价策略、受众定向、KPI 基准、ROI 预估、综合评分
- **对比表格模式**：所有产品横向对比，评分列有热力渐变

### 4. 导出

支持导出 CSV（Excel 可直接打开）和 JSON 两种格式。

## 命令行版本

如果不想用 Web 界面，也可直接运行命令行交互版本：

```bash
python fb_ads_recommender.py
```

## 文件结构

```
output/
├── app.py                    # Streamlit Web 界面入口
├── fb_ads_recommender.py     # 核心引擎 + CLI 交互版
├── products_config.json      # 产品配置文件
├── requirements.txt          # Python 依赖
├── START.md                  # 本文件
├── strategy_report.json      # 运行后生成的 JSON 报告
└── strategy_report.txt       # 运行后生成的文本报告
```
*（内容由AI生成，仅供参考）*

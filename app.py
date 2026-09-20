import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from test_calculations import (
    calculate_insurance_gap,
    calculate_pension_tax_benefit,
    calculate_real_estate_risk,
    check_liquidity_segregation,
    calculate_behavioral_equity_ceiling,
    calculate_thermometer_signal,
    run_compound_stress_test
)

# ==========================================
# 页面基本配置与浅色专业主题 CSS 注入
# ==========================================
st.set_page_config(
    page_title="家庭资产体检与均衡配置中心",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS，与静态页面保持同一套浅色金融工具视觉语言。
st.markdown("""
<style>
    .stApp {
        background-color: #F7FAFC;
        color: #102033;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1440px;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #DCE7EF;
    }

    section[data-testid="stSidebar"] * {
        color: #102033;
    }

    .card {
        background: #FFFFFF;
        border: 1px solid #DCE7EF;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 18px;
        box-shadow: 0 1px 2px rgba(16, 32, 51, 0.04);
    }

    .card-title {
        font-size: 1rem;
        font-weight: 800;
        color: #10B981;
        margin-bottom: 10px;
        border-left: 3px solid #10B981;
        padding-left: 8px;
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #102033;
        line-height: 1.2;
        font-variant-numeric: tabular-nums;
    }

    .metric-label {
        font-size: 0.78rem;
        color: #8AA0B2;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 700;
    }

    div[data-testid="stTable"] table {
        background-color: #FFFFFF !important;
        color: #102033 !important;
        border-radius: 8px !important;
        border-collapse: collapse;
        width: 100%;
    }

    div[data-testid="stTable"] th {
        background-color: #F2F7FA !important;
        color: #587084 !important;
        font-weight: 800 !important;
    }

    div[data-testid="stTable"] td {
        border-bottom: 1px solid #EAF1F6 !important;
    }

    input, select, textarea {
        background-color: #FFFFFF !important;
        color: #102033 !important;
        border: 1px solid #DCE7EF !important;
        border-radius: 6px !important;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: #FFFFFF !important;
        border-color: #DCE7EF !important;
    }

    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 数据加载与价格反算
# ==========================================
script_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(script_dir, 'assets.json')
live_data_path = os.path.join(script_dir, 'live_data.json')
strategy_presets_path = os.path.join(script_dir, 'strategy_presets.json')

# 加载 assets.json 动态配置
try:
    with open(assets_path, 'r', encoding='utf-8') as f:
        assets_list = json.load(f)
except Exception as e:
    assets_list = []
    assets_load_error = f"assets.json 加载失败：{e}"
else:
    assets_load_error = ""

# 加载实时价格 live_data.json 动态配置
live_data = {}
live_data_timestamp = ""
live_data_status = "fallback"
live_data_quality_alerts = []
if os.path.exists(live_data_path):
    try:
        with open(live_data_path, 'r', encoding='utf-8') as f:
            live_payload = json.load(f)
            if live_payload.get('status') == 'success':
                live_data = live_payload.get('data', {})
                live_data_timestamp = live_payload.get('timestamp', '')
                live_data_status = "cache"
                live_data_quality_alerts = (live_payload.get('data_quality') or {}).get('alerts') or []
    except Exception as e:
        live_data_error = f"live_data.json 加载失败：{e}"
    else:
        live_data_error = ""
else:
    live_data_error = "live_data.json 不存在"

def data_freshness_label():
    if live_data_status == "cache" and live_data_timestamp:
        return f"本地缓存 · {live_data_timestamp}"
    if live_data_status == "cache":
        return "本地缓存"
    return "兜底估算值"

def price_freshness_label():
    return data_freshness_label() if live_data_status == "cache" else "兜底估算值"

def yield_freshness_label():
    return f"近12个月现金分配数据 · {live_data_timestamp}" if live_data_status == "cache" and live_data_timestamp else "配置兜底规划值"

# 组装完整的资产配置参数
ASSETS_CONFIG = {}
if assets_list:
    for item in assets_list:
        code = item['code']
        months_int = {int(k): v for k, v in item['distribution_months'].items()}
        # 读取实时数据
        live_info = live_data.get(code, {})
        price = live_info.get('price', 0.0)
        live_yield = live_info.get('yield')
        dy = live_yield if isinstance(live_yield, (int, float)) else item['estimated_yield']
        live_months = live_info.get('distribution_months')
        if isinstance(live_months, dict) and live_months:
            months_int = {int(k): v for k, v in live_months.items()}
        
        ASSETS_CONFIG[code] = {
            'name': item['name'],
            'type': item['type'],
            'role': item['role'],
            'target_index_code': item.get('target_index_code'),
            'market': item['market'],
            'volatility_level': item['volatility_level'],
            'income_type': item['income_type'],
            'rebalance_band': item.get('rebalance_band', 3),
            'weight': item['weight'],
            'yield': dy,
            'price': price,
            'estimated_yield': item['estimated_yield'],
            'estimated_return': item.get('estimated_return', item['estimated_yield']),
            'yield_method': live_info.get('yield_method') or 'planning_assumption',
            'months': months_int,
            'strategy_note': item.get('strategy_note', ''),
            'risk_note': item.get('risk_note', '')
        }
else:
    # 备用硬编码以防万一
    fallback_raw = json.loads("""[
      {"code": "511880", "name": "银华日利货币 ETF", "type": "ETF", "role": "cash", "target_index_code": null, "market": "CN", "volatility_level": "low", "income_type": "cash_interest", "rebalance_band": 1, "weight": 4.0, "estimated_yield": 1.8, "estimated_return": 1.8, "distribution_months": {"1": 0.083, "2": 0.083, "3": 0.083, "4": 0.083, "5": 0.083, "6": 0.083, "7": 0.083, "8": 0.083, "9": 0.083, "10": 0.083, "11": 0.083, "12": 0.083}, "strategy_note": "现金类底仓，承担日常流动性与避免被迫卖出的缓冲功能", "risk_note": "不构成投资建议；货币市场收益率会随利率下行而下降，不承诺利息或收益"},
      {"code": "511360", "name": "短融 ETF", "type": "ETF", "role": "cash", "target_index_code": null, "market": "CN", "volatility_level": "low", "income_type": "cash_interest", "rebalance_band": 1, "weight": 2.0, "estimated_yield": 2.7, "estimated_return": 2.8, "distribution_months": {"3": 0.25, "6": 0.25, "9": 0.25, "12": 0.25}, "strategy_note": "短债/短融类现金增强，用于提高闲置资金票息但仍服务流动性", "risk_note": "不构成投资建议；短债也存在利率与流动性波动，不承诺分红、票息或收益"},
      {"code": "512890", "name": "中证红利低波 ETF", "type": "ETF", "role": "dividend_income", "target_index_code": "H30269", "market": "CN", "volatility_level": "medium", "income_type": "dividend", "rebalance_band": 3, "weight": 14.0, "estimated_yield": 4.5, "estimated_return": 7.0, "distribution_months": {"7": 0.5, "12": 0.5}, "strategy_note": "红利现金流核心底盘，偏高股息与低波动筛选", "risk_note": "不构成投资建议；分红金额和频率取决于成分股与基金政策，不承诺分红或收益"},
      {"code": "510880", "name": "华泰柏瑞红利 ETF", "type": "ETF", "role": "dividend_income", "target_index_code": "000015", "market": "CN", "volatility_level": "medium", "income_type": "dividend", "rebalance_band": 3, "weight": 6.0, "estimated_yield": 4.0, "estimated_return": 6.5, "distribution_months": {"12": 1.0}, "strategy_note": "上证红利类现金流补充，增加红利策略来源差异", "risk_note": "不构成投资建议；周期行业占比可能较高，分红和净值均会波动"},
      {"code": "561960", "name": "央企股东回报 ETF", "type": "ETF", "role": "dividend_income", "target_index_code": "932039", "market": "CN", "volatility_level": "medium", "income_type": "dividend", "rebalance_band": 3, "weight": 5.0, "estimated_yield": 4.2, "estimated_return": 6.6, "distribution_months": {"6": 0.5, "12": 0.5}, "strategy_note": "央企红利/股东回报方向，分散传统红利行业集中度", "risk_note": "不构成投资建议；央企风格会受政策、行业景气和估值切换影响，不承诺分红"},
      {"code": "513530", "name": "恒生港股通高股息低波 ETF", "type": "ETF", "role": "dividend_income", "target_index_code": "HSHYLV", "market": "HK", "volatility_level": "high", "income_type": "dividend", "rebalance_band": 5, "weight": 10.0, "estimated_yield": 4.8, "estimated_return": 7.5, "distribution_months": {"7": 0.5, "12": 0.5}, "strategy_note": "港股红利资产，补充离岸市场与币种分散下的现金流来源", "risk_note": "不构成投资建议；港股波动、汇率、税费和分红政策均可能影响实际现金流"},
      {"code": "510300", "name": "沪深300 ETF", "type": "ETF", "role": "domestic_beta", "target_index_code": "000300", "market": "CN", "volatility_level": "medium", "income_type": "capital_growth", "rebalance_band": 3, "weight": 8.0, "estimated_yield": 1.5, "estimated_return": 8.0, "distribution_months": {"10": 1.0}, "strategy_note": "国内核心大盘宽基，承担中国经济 beta 暴露", "risk_note": "不构成投资建议；宽基仍有系统性回撤，预期回报不等于承诺收益"},
      {"code": "563360", "name": "中证A500 ETF", "type": "ETF", "role": "domestic_beta", "target_index_code": "000510", "market": "CN", "volatility_level": "medium", "income_type": "capital_growth", "rebalance_band": 3, "weight": 7.0, "estimated_yield": 1.2, "estimated_return": 8.2, "distribution_months": {}, "strategy_note": "A股新一代宽基代表，补充行业覆盖与核心资产广度", "risk_note": "不构成投资建议；指数历史较短，估值数据不足时保持基础计划，不承诺收益"},
      {"code": "510500", "name": "中证500 ETF", "type": "ETF", "role": "domestic_beta", "target_index_code": "000905", "market": "CN", "volatility_level": "high", "income_type": "capital_growth", "rebalance_band": 4, "weight": 5.0, "estimated_yield": 0.8, "estimated_return": 8.8, "distribution_months": {}, "strategy_note": "中盘宽基 beta，补充沪深300以外的经济结构弹性", "risk_note": "不构成投资建议；中盘指数波动高于大盘，回撤和估值波动不可忽视"},
      {"code": "588000", "name": "科创50 ETF", "type": "ETF", "role": "tech_growth", "target_index_code": "000688", "market": "CN", "volatility_level": "high", "income_type": "capital_growth", "rebalance_band": 5, "weight": 7.0, "estimated_yield": 0.2, "estimated_return": 10.0, "distribution_months": {}, "strategy_note": "国内硬科技成长弹性，仅承担组合增长期权，不作为稳定现金流来源", "risk_note": "不构成投资建议；科技资产高波动高回撤，估值和产业周期不确定，不承诺收益"},
      {"code": "513500", "name": "标普500 ETF", "type": "ETF", "role": "overseas_broad", "target_index_code": "SPX", "market": "US", "volatility_level": "medium", "income_type": "capital_growth", "rebalance_band": 5, "weight": 12.0, "estimated_yield": 1.2, "estimated_return": 8.0, "distribution_months": {}, "strategy_note": "海外宽基，承担全球市场 beta 与美元资产分散，不等同于海外科技", "risk_note": "不构成投资建议；存在海外市场、汇率、额度、溢价和税费风险，不承诺收益"},
      {"code": "513100", "name": "纳斯达克100 ETF", "type": "ETF", "role": "overseas_tech", "target_index_code": "NDX", "market": "US", "volatility_level": "high", "income_type": "capital_growth", "rebalance_band": 5, "weight": 5.0, "estimated_yield": 0.5, "estimated_return": 9.5, "distribution_months": {}, "strategy_note": "海外科技成长弹性，明确不等于海外宽基，需控制集中度", "risk_note": "不构成投资建议；美股科技估值、汇率和基金溢价均可能导致大幅波动"},
      {"code": "518880", "name": "黄金 ETF", "type": "ETF", "role": "hedge", "target_index_code": null, "market": "Global", "volatility_level": "medium", "income_type": "hedge", "rebalance_band": 5, "weight": 6.0, "estimated_yield": 0.0, "estimated_return": 4.5, "distribution_months": {}, "strategy_note": "黄金对冲通胀、汇率和极端风险，不提供稳定票息", "risk_note": "不构成投资建议；黄金无分红，价格可能长时间震荡或回撤，不承诺收益"},
      {"code": "511520", "name": "政金债券 ETF", "type": "ETF", "role": "bond_duration", "target_index_code": null, "market": "CN", "volatility_level": "low", "income_type": "cash_interest", "rebalance_band": 2, "weight": 4.0, "estimated_yield": 2.6, "estimated_return": 3.2, "distribution_months": {"6": 0.5, "12": 0.5}, "strategy_note": "中长期政金债/利率债久期资产，承担利率下行和风险事件对冲", "risk_note": "不构成投资建议；久期债会受利率上行影响产生净值回撤，不承诺票息或收益"},
      {"code": "511010", "name": "国债 ETF", "type": "ETF", "role": "bond_duration", "target_index_code": null, "market": "CN", "volatility_level": "low", "income_type": "cash_interest", "rebalance_band": 2, "weight": 3.0, "estimated_yield": 2.3, "estimated_return": 3.0, "distribution_months": {"6": 0.5, "12": 0.5}, "strategy_note": "国债类利率债，和黄金一起承担组合防御与对冲角色", "risk_note": "不构成投资建议；债券基金净值会随利率变化波动，不承诺分红、票息或收益"},
      {"code": "508099", "name": "建信中关村 REIT", "type": "REITs", "role": "cashflow_alt", "target_index_code": null, "market": "CN", "volatility_level": "high", "income_type": "alternative_income", "rebalance_band": 5, "weight": 2.0, "estimated_yield": 4.5, "estimated_return": 6.0, "distribution_months": {"4": 0.25, "7": 0.25, "10": 0.25, "12": 0.25}, "strategy_note": "可选现金流增强观察位，默认低权重，只有在理解底层资产后再小比例使用", "risk_note": "不构成投资建议；REITs 分红和估值高度依赖底层经营与流动性，不计入稳定现金流，不承诺分红或收益"},
      {"code": "512100", "name": "南方中证1000 ETF", "type": "ETF", "role": "small_cap", "target_index_code": "000852", "market": "CN", "volatility_level": "high", "income_type": "capital_growth", "rebalance_band": 5, "weight": 0.0, "estimated_yield": 0.0, "estimated_return": 9.0, "distribution_months": {}, "strategy_note": "中国小盘风险溢价观察位，补足沪深300、中证A500和中证500以下的市值层级；默认0%，仅在现金防线完整且估值数据可核验时从国内权益桶内置换", "risk_note": "不构成投资建议；小盘股对流动性、盈利周期和交易拥挤更敏感，回撤可能显著高于大盘宽基，不因高风险溢价标签自动加仓"},
      {"code": "513180", "name": "华夏恒生科技 ETF", "type": "ETF", "role": "china_offshore_growth", "target_index_code": "HKTECH", "market": "HK", "volatility_level": "high", "income_type": "capital_growth", "rebalance_band": 5, "weight": 0.0, "estimated_yield": 0.0, "estimated_return": 9.0, "distribution_months": {}, "strategy_note": "离岸中国成长风险溢价观察位，与港股高股息形成价值/成长两端覆盖；默认0%，仅从高波动成长桶内置换，不挤占现金缓冲池", "risk_note": "不构成投资建议；存在港股科技高波动、政策与盈利周期、汇率、QDII溢折价和跟踪误差风险，不把低估判断等同于短期上涨"}
    ]""")
    for item in fallback_raw:
        code = item['code']
        months_int = {int(k): v for k, v in item['distribution_months'].items()}
        ASSETS_CONFIG[code] = {
            'name': item['name'],
            'type': item['type'],
            'role': item['role'],
            'target_index_code': item.get('target_index_code'),
            'market': item['market'],
            'volatility_level': item['volatility_level'],
            'income_type': item['income_type'],
            'rebalance_band': item.get('rebalance_band', 3),
            'weight': item['weight'],
            'yield': item['estimated_yield'],
            'price': 0.0,
            'estimated_yield': item['estimated_yield'],
            'estimated_return': item['estimated_return'],
            'months': months_int,
            'strategy_note': item['strategy_note'],
            'risk_note': item['risk_note']
        }

# ==========================================
# 侧边栏：核心交互设置
# ==========================================
st.sidebar.markdown("<h2 style='color:#10B981;text-align:center;margin-bottom:20px;'>💰 功能模块导航</h2>", unsafe_allow_html=True)
if assets_load_error:
    st.sidebar.error(f"{assets_load_error}；当前使用内置兜底资产配置。")
if live_data_error:
    st.sidebar.warning(f"{live_data_error}；行情/收益率使用兜底估算值。")

MENU_OPTIONS = [
    "1. 家庭资产体检与配置建议",
    "2. 资产配置与股息测算看板",
    "3. 现金缓冲池平滑模拟器",
    "4. 估值温度计与测算工具",
    "5. 年度资产再平衡测算",
    "6. 风险压力测试"
]

if 'main_menu' not in st.session_state:
    st.session_state.main_menu = MENU_OPTIONS[0]

menu = st.sidebar.radio(
    "功能模块导航",
    [
        "1. 资产配置与股息看板", 
        "2. 缓冲池与现金流模拟", 
        "3. 估值温度计与建仓建议", 
        "4. 资产记账与年度平衡",
        "5. 目标导向规划 (核心)",
        "6. Markdown 体检报告导出",
        "7. 债务决策对照 (还贷vs投资)"
    ],
    index=4 # 默认高亮展示目标规划
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 资产与收益基准参数")
principal = st.sidebar.number_input("可用总本金 (万元)", min_value=5.0, max_value=5000.0, value=50.0, step=5.0)
target_monthly = st.sidebar.number_input("期望月生活费现金流 (万元)", min_value=0.01, max_value=50.0, value=0.2, step=0.05)
buffer_seed = st.sidebar.number_input("现金缓冲池初始资金 (万元)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
growth_rate_pct = st.sidebar.number_input("增长预期年化收益率 (%)", min_value=1.0, max_value=25.0, value=6.5, step=0.1)
growth_rate = growth_rate_pct / 100.0
money_market_rate = st.sidebar.slider("缓冲池闲置资金年化收益 (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1) / 100

st.sidebar.markdown("### 🩺 家庭资产体检联动")
monthly_income = st.sidebar.number_input("家庭月总收入 (元)", min_value=1000, max_value=500000, value=30000, step=1000)
monthly_expense = st.sidebar.number_input("家庭月常规支出 (元)", min_value=1000, max_value=300000, value=18000, step=1000)
monthly_surplus = st.sidebar.number_input("月可结余 (元)", min_value=0, max_value=200000, value=max(0, monthly_income - monthly_expense), step=500)
bucket_1_3y = st.sidebar.number_input("未来1-3年确定要用的钱 (元)", min_value=0, max_value=5000000, value=150000, step=10000)

st.sidebar.markdown("### 💳 负债结构与债务决策联动")
debt_bracket_options = ['<3.5%', '3.5-4.5%', '4.5-6%', '>6%']
debt_bracket_medians = {'<3.5%': 3.0, '3.5-4.5%': 4.0, '4.5-6%': 5.25, '>6%': 7.2}
debt_bracket = st.sidebar.selectbox("综合贷款利率区间", debt_bracket_options, index=2)
default_median = debt_bracket_medians[debt_bracket]
custom_debt_rate = st.sidebar.number_input("测算基准利率 (%) [支持微调]", min_value=0.0, max_value=30.0, value=float(default_median), step=0.1)
high_interest_balance = st.sidebar.number_input("高息债务余额 (元) [>6%]", min_value=0.0, max_value=10000000.0, value=0.0, step=5000.0)
mortgage_balance = st.sidebar.number_input("房贷余额 (元)", min_value=0.0, max_value=50000000.0, value=1200000.0, step=50000.0)
car_loan_balance = st.sidebar.number_input("车贷余额 (元)", min_value=0.0, max_value=5000000.0, value=0.0, step=10000.0)
consumer_loan_balance = st.sidebar.number_input("消费贷余额 (元)", min_value=0.0, max_value=5000000.0, value=0.0, step=10000.0)
business_loan_balance = st.sidebar.number_input("经营贷余额 (元)", min_value=0.0, max_value=50000000.0, value=0.0, step=50000.0)
monthly_debt_payment = st.sidebar.number_input("每月贷款总还款 (元)", min_value=0.0, max_value=500000.0, value=6500.0, step=500.0)
available_fund_x = st.sidebar.number_input("测算可用资金 X (元)", min_value=10000.0, max_value=10000000.0, value=200000.0, step=50000.0)

st.sidebar.markdown("""
<div style='margin-top:20px; padding:15px; border-radius:8px; background:rgba(255,255,255,0.05); font-size:0.8rem; color:#94A3B8;'>
    <strong>💡 模块联动提示</strong><br>
    「目标导向规划」将复利推演您的【月可结余】与【可用本金】；「债务决策对照」将实时对照贷款利率与组合收益率，测算提前还贷 vs 坚持投资的净资产路径。
</div>
""", unsafe_allow_html=True)

def set_buffer_coverage_months(months):
    target = max(float(st.session_state.get('target_monthly', 0.0)), 0.0)
    principal_value = max(float(st.session_state.get('principal', 0.0)), 0.0)
    st.session_state.buffer_seed = min(target * months, principal_value, 5000.0)


def set_buffer_scenario(mode):
    presets = {
        'baseline': (0, 0, False),
        'standard': (20, 1, False),
        'severe': (40, 3, True)
    }
    drop, delay, pause = presets.get(mode, presets['standard'])
    st.session_state.buffer_stable_income_drop = drop
    st.session_state.buffer_delay_months = delay
    st.session_state.buffer_pause_dividend_year = pause
    st.session_state.buffer_rebalance_harvest_checkbox = False

strategy_console_pages = [
    "2. 资产配置与股息测算看板",
    "3. 现金缓冲池平滑模拟器",
    "4. 估值温度计与测算工具",
    "5. 年度资产再平衡测算",
    "6. 风险压力测试"
]

if menu in strategy_console_pages:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔑 策略控制台")
    st.sidebar.caption("这里是配置看板与缓冲池模拟的唯一参数口径；家庭刚性支出、收入和负债请在“家庭资产体检”中填写。")
    st.sidebar.markdown("### 基本配置参数")

    principal = st.sidebar.number_input("您的可用总本金 (万元)", min_value=10.0, max_value=5000.0, step=10.0, key="principal")

    target_monthly = st.sidebar.number_input("期望月现金流 (万元)", min_value=0.1, max_value=50.0, step=0.5, key="target_monthly")

    buffer_seed = st.sidebar.number_input("现金缓冲池初始资金 (万元)", min_value=0.0, max_value=5000.0, step=1.0, key="buffer_seed", help="不确定时，可在模拟器内一键选择 6、9 或 12 个月目标支取额。")

    money_market_rate = st.sidebar.slider("缓冲池闲置资金年化收益 (%)", min_value=0.5, max_value=5.0, step=0.1, key="money_market_rate")
else:
    principal = st.session_state.principal
    target_monthly = st.session_state.target_monthly
    buffer_seed = st.session_state.buffer_seed
    money_market_rate = st.session_state.money_market_rate

invest_principal = max(principal - buffer_seed, 0.0)

# ==========================================
# 辅助计算函数 (目标终值、三大杠杆反解与提前退休持久性)
# ==========================================
def calculate_goal_projection_py(
    target_year,
    target_amount,
    monthly_surplus_val,
    growth_rate_val,
    current_principal_val,
    reserved_amount_val=0,
    current_year_val=2026,
    safe_rate_val=0.02
):
    import math
    years = max(1, target_year - current_year_val)
    months = years * 12
    monthly_rate = growth_rate_val / 12.0
    
    # 1. 当前本金复利终值
    fv_principal = current_principal_val * ((1.0 + growth_rate_val) ** years)
    
    # 2. 月结余定投复利终值 (期初年金)
    if monthly_rate > 0:
        fv_monthly = monthly_surplus_val * (((1.0 + monthly_rate) ** months - 1.0) / monthly_rate) * (1.0 + monthly_rate)
    else:
        fv_monthly = monthly_surplus_val * months
        
    # 3. 预留金额终值
    fv_reserved = reserved_amount_val * ((1.0 + safe_rate_val) ** years)
    
    fv_total = fv_principal + fv_monthly + fv_reserved
    diff = fv_total - target_amount
    gap = max(0.0, -diff)
    
    levers = None
    if gap > 0:
        # 杠杆 1: 每月需多储蓄
        if monthly_rate > 0:
            annuity_factor = (((1.0 + monthly_rate) ** months - 1.0) / monthly_rate) * (1.0 + monthly_rate)
            extra_monthly = math.ceil(gap / annuity_factor)
        else:
            extra_monthly = math.ceil(gap / months)
            
        # 杠杆 2: 收益率提升
        low = growth_rate_val
        high = 1.0
        r_req = growth_rate_val
        for _ in range(100):
            mid = (low + high) / 2.0
            mid_m_rate = mid / 12.0
            test_p = current_principal_val * ((1.0 + mid) ** years)
            if mid_m_rate > 0:
                test_m = monthly_surplus_val * (((1.0 + mid_m_rate) ** months - 1.0) / mid_m_rate) * (1.0 + mid_m_rate)
            else:
                test_m = monthly_surplus_val * months
            test_tot = test_p + test_m + fv_reserved
            if abs(test_tot - target_amount) < 5.0:
                r_req = mid
                break
            elif test_tot < target_amount:
                low = mid
            else:
                high = mid
            r_req = mid
            
        rate_diff_pct = (r_req - growth_rate_val) * 100.0
        is_rate_safe = (r_req <= 0.08)
        
        # 杠杆 3: 放宽金额或时点延后
        loosen_amount = math.ceil(gap)
        curr_y = years
        while curr_y < 80:
            m = curr_y * 12
            test_p = current_principal_val * ((1.0 + growth_rate_val) ** curr_y)
            if monthly_rate > 0:
                test_m = monthly_surplus_val * (((1.0 + monthly_rate) ** m - 1.0) / monthly_rate) * (1.0 + monthly_rate)
            else:
                test_m = monthly_surplus_val * m
            test_res = reserved_amount_val * ((1.0 + safe_rate_val) ** curr_y)
            if (test_p + test_m + test_res) >= target_amount:
                break
            curr_y += 0.5
        delay_years = round(max(0.0, curr_y - years), 1)
        
        levers = {
            'extra_monthly': extra_monthly,
            'req_rate_pct': round(r_req * 100.0, 2),
            'rate_diff_pct': round(rate_diff_pct, 2),
            'is_rate_safe': is_rate_safe,
            'loosen_amount': loosen_amount,
            'delay_years': delay_years,
            'delayed_target_year': target_year + math.ceil(delay_years)
        }
        
    return {
        'years': years,
        'months': months,
        'fv_principal': fv_principal,
        'fv_monthly': fv_monthly,
        'fv_reserved': fv_reserved,
        'fv_total': fv_total,
        'diff': diff,
        'gap': gap,
        'is_achieved': diff >= 0,
        'levers': levers
    }

def simulate_early_retirement_py(
    retire_age,
    target_amount,
    projected_capital_at_retire,
    monthly_expense_val,
    dividend_yield_val,
    buffer_rate_val=0.02,
    end_age=85
):
    total_years = max(1, end_age - retire_age)
    total_months = total_years * 12
    capital = projected_capital_at_retire if projected_capital_at_retire > 0 else target_amount
    lowest_capital = capital
    most_fragile_month = 1
    depletion_month = None
    depletion_age = None
    
    seasonality = {
        1: 0.02, 2: 0.02, 3: 0.03, 4: 0.05,
        5: 0.15, 6: 0.25, 7: 0.30, 8: 0.10,
        9: 0.03, 10: 0.02, 11: 0.01, 12: 0.02
    }
    
    for m in range(1, total_months + 1):
        cal_month = ((m - 1) % 12) + 1
        curr_age = retire_age + (m - 1) / 12.0
        
        ann_div = max(0.0, capital) * dividend_yield_val
        month_div = ann_div * seasonality[cal_month]
        month_int = max(0.0, capital) * (buffer_rate_val / 12.0)
        
        capital = capital + month_div + month_int - monthly_expense_val
        if capital < lowest_capital:
            lowest_capital = capital
            most_fragile_month = m
            
        if capital <= 0 and depletion_month is None:
            depletion_month = m
            depletion_age = round(curr_age, 1)
            
    return {
        'total_months': total_months,
        'is_sustainable': depletion_month is None,
        'final_capital': capital,
        'depletion_age': depletion_age,
        'depletion_month': depletion_month,
        'lowest_capital': lowest_capital,
        'most_fragile_month': most_fragile_month,
        'most_fragile_age': round(retire_age + (most_fragile_month - 1) / 12.0, 1)
    }

def calculate_debt_decision_metrics_py(
    debt_bracket_val='4.5-6%',
    custom_debt_rate_val=None,
    high_interest_balance_val=0.0,
    growth_rate_pct_val=6.5,
    available_fund_x_val=200000.0
):
    bracket_medians = {
        '<3.5%': 3.0,
        '3.5-4.5%': 4.0,
        '4.5-6%': 5.25,
        '>6%': 7.2
    }
    bracket_median = bracket_medians.get(debt_bracket_val, 5.25)
    effective_debt_rate = custom_debt_rate_val if (custom_debt_rate_val is not None and custom_debt_rate_val > 0) else bracket_median
    conservative_yield = round(growth_rate_pct_val * 0.7, 2)
    
    # 决策矩阵文案判定
    if effective_debt_rate > (conservative_yield + 2.0):
        decision_text = "优先清偿高息债务（相当于获得无风险的利差收益）"
        decision_type = "repay_first"
    elif effective_debt_rate < (conservative_yield - 2.0):
        decision_text = "保持贷款、优先投资，但需确认现金流稳定性"
        decision_type = "invest_first"
    else:
        decision_text = "两者皆可，优先级取决于风险偏好与流动性需求"
        decision_type = "neutral"
        
    has_high_interest_alert = (high_interest_balance_val > 0) or (debt_bracket_val == '>6%') or (effective_debt_rate > 6.0)
    
    r_debt = effective_debt_rate / 100.0
    r_invest = conservative_yield / 100.0
    
    table = []
    for years in [3, 5, 10]:
        fv_repay = available_fund_x_val * ((1.0 + r_debt) ** years)
        fv_invest = available_fund_x_val * ((1.0 + r_invest) ** years)
        diff = fv_repay - fv_invest
        diff_pct = (diff / available_fund_x_val) * 100.0 if available_fund_x_val > 0 else 0.0
        table.append({
            'years': years,
            'fund_x': available_fund_x_val,
            'fv_repay': round(fv_repay, 2),
            'fv_invest': round(fv_invest, 2),
            'diff': round(diff, 2),
            'diff_pct': round(diff_pct, 2),
            'advantage': '提前还贷更优' if diff > 0 else ('坚持投资更优' if diff < 0 else '持平')
        })
        
    return {
        'debt_bracket': debt_bracket_val,
        'bracket_median': bracket_median,
        'effective_debt_rate': effective_debt_rate,
        'conservative_yield': conservative_yield,
        'decision_text': decision_text,
        'decision_type': decision_type,
        'has_high_interest_alert': has_high_interest_alert,
        'fund_x': available_fund_x_val,
        'table': table
    }

# ==========================================
# 模块 1: 资产配置与股息看板
# ==========================================
if 'family_data' not in st.session_state:
    st.session_state.family_data = {
        'f-age': 35,
        'f-members': 3,
        'f-children': 'yes',
        'f-elders': 'no',
        'expense-buyhouse': False,
        'expense-edu': False,
        'expense-med': False,
        'expense-biz': False,
        'expense-city': False,
        'expense-other': False,
        'f-planned-spend-12m': 0.0,
        'f-planned-spend-36m': 0.0,
        'f-monthly-income': 30000.0,
        'f-fixed-expense': 12000.0,
        'f-essential-expense': 9000.0,
        'f-surplus-income': 18000.0,
        'f-income-sources': 2,
        'f-salary-ratio': 80.0,
        'f-bonus-ratio': 20.0,
        'protect-coverage': 'basic',
        'f-stability': 'normal',
        'f-recover-months': 6,
        'ast-cash': 50000.0,
        'ast-mmf': 100000.0,
        'ast-ashare': 150000.0,
        'ast-hk': 50000.0,
        'ast-overseas': 50000.0,
        'ast-gold': 20000.0,
        'ast-house': 2000000.0,
        'ast-insurance': 50000.0,
        'ast-others': 0.0,
        'debt-house': 800000.0,
        'debt-car': 50000.0,
        'debt-consumption': 10000.0,
        'debt-biz': 0.0,
        'debt-monthly-repay': 8500.0,
        'debt-high-interest': 0.0,
        'debt-rate': '4.2',
        'debt-pressure': 'no',
        'inv-drawdown': '20',
        'inv-horizon': '5',
        'inv-drop-action': 'hold',
        'inv-rely': 'low',
        'inv-withdraw-monthly': 'no',
        'goal-cash': False,
        'goal-edu': False,
        'goal-pension': False,
        'goal-house': False,
        'goal-protect': False,
        'goal-growth': False,
        'goal-retire': False
    }

def calculate_family_diagnostics(fd):
    total_assets = (fd['ast-cash'] + fd['ast-mmf'] + fd['ast-ashare'] + fd['ast-hk'] +
                    fd['ast-overseas'] + fd['ast-gold'] + fd['ast-house'] + fd['ast-insurance'] + fd['ast-others'])
    total_liabilities = fd['debt-house'] + fd['debt-car'] + fd['debt-consumption'] + fd['debt-biz']
    net_worth = total_assets - total_liabilities
    leverage = total_liabilities / total_assets if total_assets > 0 else 0.0
    repay_income_ratio = fd['debt-monthly-repay'] / fd['f-monthly-income'] if fd['f-monthly-income'] > 0 else 0.0
    surplus_ratio = fd['f-surplus-income'] / fd['f-monthly-income'] if fd['f-monthly-income'] > 0 else 0.0
    liquid_cash = fd['ast-cash'] + fd['ast-mmf']
    monthly_essential_ex = max(fd.get('f-essential-expense', 0.0), fd['f-fixed-expense'] * 0.7, 1.0)
    monthly_required_outflow = monthly_essential_ex + fd.get('debt-monthly-repay', 0.0)
    cash_coverage_months = liquid_cash / monthly_required_outflow
    investable_assets = fd['ast-cash'] + fd['ast-mmf'] + fd['ast-ashare'] + fd['ast-hk'] + fd['ast-overseas'] + fd['ast-gold'] + fd['ast-others']
    equity_assets = fd['ast-ashare'] + fd['ast-hk'] + fd['ast-overseas']
    equity_invest_ratio = equity_assets / investable_assets if investable_assets > 0 else 0.0
    concentration = max(fd['ast-ashare'], fd['ast-hk'], fd['ast-overseas']) / equity_assets if equity_assets > 0 else 0.0

    vulnerability = 0
    if cash_coverage_months < 3:
        vulnerability += 30
    elif cash_coverage_months < 6:
        vulnerability += 15
    if repay_income_ratio > 0.4:
        vulnerability += 25
    elif repay_income_ratio > 0.25:
        vulnerability += 12
    if fd['f-stability'] == 'volatile':
        vulnerability += 15
    elif fd['f-stability'] == 'normal':
        vulnerability += 7
    if fd['f-income-sources'] == 1:
        vulnerability += 15
    if fd['debt-pressure'] == 'yes':
        vulnerability += 15
    if fd.get('debt-high-interest', 0.0) > 0:
        vulnerability += 10
    if fd.get('protect-coverage') == 'none':
        vulnerability += 10
    elif fd.get('protect-coverage') in ('adequate', 'strong'):
        vulnerability -= 5
    vulnerability = max(0, min(vulnerability, 100))

    aggressiveness = min(round(min(equity_invest_ratio * 50, 50) +
                               {'5': 5, '10': 15, '20': 35, '30': 60, '40': 85}.get(fd['inv-drawdown'], 15) * 0.4 +
                               {'sell': 5, 'stop': 15, 'hold': 40, 'buy': 75}.get(fd['inv-drop-action'], 30) * 0.25), 100)

    res = portfolio_engine.evaluate_family_profile(
        fd, investable_assets, net_worth, total_assets,
        leverage, repay_income_ratio, surplus_ratio, cash_coverage_months,
        [], int(fd['inv-drawdown'])
    )
    return {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_worth': net_worth,
        'leverage': leverage,
        'repay_income_ratio': repay_income_ratio,
        'surplus_ratio': surplus_ratio,
        'cash_coverage_months': cash_coverage_months,
        'investable_assets': investable_assets,
        'equity_invest_ratio': equity_invest_ratio,
        'concentration': concentration,
        'vulnerability': vulnerability,
        'aggressiveness': aggressiveness,
        'res': res
    }

def family_rule_lines(metrics):
    res = metrics['res']
    fd = st.session_state.family_data
    return [
        f"现金覆盖月数 = (活期现金 + 货币/短债基金) / (月必要支出底线或固定支出 70% + 月供)，当前 {metrics['cash_coverage_months']:.1f} 个月；低于 6 个月会阻断积极型配置。",
        f"月供收入比 = 月贷款还款 / 家庭税后月收入，当前 {metrics['repay_income_ratio']*100:.1f}%；超过 35% 会阻断积极型配置。",
        f"结余率 = 月可结余 / 家庭税后月收入，当前 {metrics['surplus_ratio']*100:.1f}%；低于 15% 会阻断积极型配置。",
        f"资产负债率 = 总负债 / 总资产，当前 {metrics['leverage']*100:.1f}%；超过 50% 会提高安全储备权重。",
        f"高息债务余额当前 ¥{fd.get('debt-high-interest', 0.0):,.0f}；有高息债务时优先降风险。",
        f"三桶结果：安全储备 {res['safety']}%、长期成长 {res['longterm']}%、综合对冲 {res['hedge']}%；积极型阻断：{'已触发' if res['isProhibitAggressive'] else '未触发'}。"
    ]

def collect_financial_snapshot(weights, principal, buffer_seed, target_monthly, money_market_rate):
    fd = st.session_state.family_data
    metrics = calculate_family_diagnostics(fd)
    feasibility = portfolio_engine.calculate_cashflow_feasibility(
        36,
        target_monthly * 10000,
        buffer_seed,
        principal,
        weights,
        ASSETS_CONFIG,
        money_market_rate / 100.0,
        datetime.now().month,
        20,
        0,
        False
    )
    return {
        "version": 1,
        "exportedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "wealth-planning-local-snapshot",
        "privacy": "local-json-only-no-upload",
        "metrics": {
            "healthScore": metrics['res'].get('fourMoney', {}).get('score'),
            "safeMonthlyWithdrawWan": feasibility['safeMonthlyWithdrawWan'],
            "recommendedMonthlyExpenseWan": feasibility['recommendedMonthlyExpenseWan'],
            "cashCoverageMonths": metrics['cash_coverage_months'],
            "repayIncomeRatio": metrics['repay_income_ratio'],
            "surplusRatio": metrics['surplus_ratio']
        },
        "assumptions": {
            "principalWan": principal,
            "targetMonthlyWan": target_monthly,
            "bufferSeedWan": buffer_seed,
            "moneyMarketRatePct": money_market_rate,
            "dataSource": data_freshness_label()
        }
    }

# ==========================================
# 策略预设联动逻辑
# ==========================================
PRESET_LABELS = {
    "conservative": "🛡️ 保守型现金流策略",
    "balanced": "⚖️ 均衡型增长配置",
    "aggressive": "🚀 积极型成长突破"
}
try:
    with open(strategy_presets_path, 'r', encoding='utf-8') as f:
        preset_payload = json.load(f)
    PRESETS = {
        PRESET_LABELS[preset_id]: preset['weights']
        for preset_id, preset in preset_payload['presets'].items()
        if preset_id in PRESET_LABELS
    }
except (OSError, KeyError, TypeError, json.JSONDecodeError):
    PRESETS = {}

if 'strategy_preset_option' not in st.session_state:
    st.session_state.strategy_preset_option = "⚖️ 均衡型增长配置"

if 'is_prohibit_aggressive' not in st.session_state:
    st.session_state.is_prohibit_aggressive = False
if 'family_aggressiveness' not in st.session_state:
    st.session_state.family_aggressiveness = 0

# 修改权重时的回调
def on_weight_changed():
    st.session_state.strategy_preset_option = "✍️ 自定义权重配置"

# 在 session_state 中初始化权重
for code, info in ASSETS_CONFIG.items():
    w_key = f"w_{code}"
    if w_key not in st.session_state:
        st.session_state[w_key] = info['weight']

if menu in strategy_console_pages:
    # 策略预设选择器
    preset_option = st.sidebar.selectbox(
        "配置策略预设",
        ["✍️ 自定义权重配置", "🛡️ 保守型现金流策略", "⚖️ 均衡型增长配置", "🚀 积极型成长突破"],
        key="strategy_preset_option"
    )
else:
    preset_option = st.session_state.strategy_preset_option

# 积极型策略阻断警告
if preset_option == "🚀 积极型成长突破" and st.session_state.is_prohibit_aggressive:
    if menu in strategy_console_pages:
        st.sidebar.error("⚠️ 评估警示：当前家庭财务体检结果显示您的财务状况较为脆弱（低备用金、低结余或高负债），系统已阻断积极型成长策略的选择。请先优化家庭财务结构！自动返回均衡配置。")
    st.session_state.strategy_preset_option = "⚖️ 均衡型增长配置"
    preset_option = "⚖️ 均衡型增长配置"
elif preset_option == "🚀 积极型成长突破" and st.session_state.family_aggressiveness < 30:
    if menu in strategy_console_pages:
        st.sidebar.error("⚠️ 风险优先提醒：风险进攻评分低于 30 分，不同时高配科创50和纳指100；已自动返回均衡配置。")
    st.session_state.strategy_preset_option = "⚖️ 均衡型增长配置"
    preset_option = "⚖️ 均衡型增长配置"

# 如果选择了预设，则更新对应的权重
if preset_option in PRESETS:
    for code, w in PRESETS[preset_option].items():
        st.session_state[f"w_{code}"] = w

# 统一获取当前持仓权重数据
weights = {}
for code in ASSETS_CONFIG.keys():
    weights[code] = st.session_state[f"w_{code}"]

with st.sidebar.expander("本地财务快照", expanded=False):
    snapshot = collect_financial_snapshot(weights, principal, buffer_seed, target_monthly, money_market_rate)
    st.download_button(
        "导出财务快照 JSON",
        data=json.dumps(snapshot, ensure_ascii=False, indent=2),
        file_name=f"wealth-planning-snapshot-{snapshot['exportedAt'].replace(':', '-').replace(' ', '-')}.json",
        mime="application/json",
        help="导出为本地 JSON 文件，不联网、不上传。"
    )
    uploaded_snapshot = st.file_uploader("导入历史快照对比", type=["json"], key="snapshot_uploader")
    if uploaded_snapshot is not None:
        try:
            old_snapshot = json.loads(uploaded_snapshot.getvalue().decode("utf-8"))
            old_metrics = old_snapshot.get("metrics", {})
            current_metrics = snapshot.get("metrics", {})
            compare_rows = []
            for label, key, suffix in [
                ("健康分", "healthScore", " 分"),
                ("安全月支取上限", "safeMonthlyWithdrawWan", " 万"),
                ("建议月支取", "recommendedMonthlyExpenseWan", " 万"),
                ("现金覆盖月数", "cashCoverageMonths", " 月")
            ]:
                old_val = old_metrics.get(key)
                new_val = current_metrics.get(key)
                if old_val is None or new_val is None:
                    compare_rows.append({"指标": label, "历史": "--", "当前": "--", "变化": "数据不足"})
                else:
                    diff = float(new_val) - float(old_val)
                    arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
                    compare_rows.append({"指标": label, "历史": f"{float(old_val):.2f}{suffix}", "当前": f"{float(new_val):.2f}{suffix}", "变化": f"{arrow} {diff:.2f}{suffix}"})
            st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)
            st.caption("快照只在本地导入比较，不上传服务器。")
        except Exception:
            st.error("快照 JSON 解析失败，请确认文件来自本工具导出。")

# ==========================================
# 模块 1: 家庭资产体检与配置建议
# ==========================================
if menu == "1. 家庭资产体检与配置建议":
    st.markdown("<h1 style='color:#102033; margin-bottom:10px;'>👤 家庭资产体检与配置建议</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background:rgba(59,130,246,0.05); border:1px solid #3B82F6; border-radius:8px; padding:15px; margin-bottom:20px; font-size:0.9rem;'>
        🔒 <strong>隐私声明：</strong> 本问卷仅在您的浏览器本地运行，所有输入均用于当前页面的计算，<strong>不会上传到服务器，也不会被后台保存</strong>。
    </div>
    """, unsafe_allow_html=True)

    fd = st.session_state.family_data

    col_left, col_right = st.columns([1.2, 1.0])

    with col_left:
        # 1. 家庭基本信息
        with st.expander("👤 1. 家庭基本信息", expanded=True):
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                fd['f-age'] = st.number_input("主要决策人年龄 (岁)", min_value=18, max_value=100, value=int(fd.get('f-age', 35)))
                fd['f-children'] = st.selectbox("是否有子女", ["no", "yes"], format_func=lambda x: "无子女" if x == "no" else "有子女", index=0 if fd.get('f-children') == 'no' else 1)
            with sub_col2:
                fd['f-members'] = st.number_input("家庭成员数量 (人)", min_value=1, max_value=10, value=int(fd.get('f-members', 3)))
                fd['f-elders'] = st.selectbox("是否有赡养老人责任", ["no", "yes"], format_func=lambda x: "无需要赡养的老人" if x == "no" else "需要赡养老人", index=0 if fd.get('f-elders') == 'no' else 1)
            
            st.write("未来 3 年是否有预计大额支出 (可多选)")
            e_cols = st.columns(3)
            fd['expense-buyhouse'] = e_cols[0].checkbox("买房/换房", value=fd.get('expense-buyhouse', False), key="expense_buyhouse_checkbox")
            fd['expense-edu'] = e_cols[1].checkbox("子女教育", value=fd.get('expense-edu', False), key="expense_edu_checkbox")
            fd['expense-med'] = e_cols[2].checkbox("大额医疗", value=fd.get('expense-med', False), key="expense_med_checkbox")
            fd['expense-biz'] = e_cols[0].checkbox("创业资金", value=fd.get('expense-biz', False), key="expense_biz_checkbox")
            fd['expense-city'] = e_cols[1].checkbox("更换城市", value=fd.get('expense-city', False), key="expense_city_checkbox")
            fd['expense-other'] = e_cols[2].checkbox("其他大额支出", value=fd.get('expense-other', False), key="expense_other_checkbox")

            spend_col1, spend_col2 = st.columns(2)
            fd['f-planned-spend-12m'] = spend_col1.number_input("未来 12 个月确定要用的钱 (元)", min_value=0.0, value=float(fd.get('f-planned-spend-12m', 0.0)), step=10000.0)
            fd['f-planned-spend-36m'] = spend_col2.number_input("未来 1-3 年确定要用的钱 (元)", min_value=0.0, value=float(fd.get('f-planned-spend-36m', 0.0)), step=10000.0)

        # 2. 收入与现金流
        with st.expander("💵 2. 收入与月现金流", expanded=True):
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                fd['f-monthly-income'] = st.number_input("家庭税后月收入 (元)", min_value=0.0, value=float(fd.get('f-monthly-income', 30000.0)), step=1000.0)
                fd['f-fixed-expense'] = st.number_input("月固定生活支出 (不含贷款)", min_value=0.0, value=float(fd.get('f-fixed-expense', 12000.0)), step=1000.0)
            with sub_col2:
                fd['f-essential-expense'] = st.number_input("月必要支出底线 (元)", min_value=0.0, value=float(fd.get('f-essential-expense', 9000.0)), step=1000.0)
                # 自动算可结余
                default_surplus = max(fd['f-monthly-income'] - fd['f-fixed-expense'] - fd.get('debt-monthly-repay', 0.0), 0.0)
                fd['f-surplus-income'] = st.number_input("月可结余 (元)", min_value=0.0, value=float(fd.get('f-surplus-income', default_surplus)), step=1000.0)

            sub_col_sources, sub_col_protect = st.columns(2)
            fd['f-income-sources'] = sub_col_sources.number_input("家庭收入来源数量 (个)", min_value=1, max_value=10, value=int(fd.get('f-income-sources', 2)))
            fd['protect-coverage'] = sub_col_protect.selectbox(
                "家庭保障覆盖程度",
                ["none", "basic", "adequate", "strong"],
                format_func=lambda x: {
                    "none": "几乎没有商业保障",
                    "basic": "社保 + 少量基础保障",
                    "adequate": "重疾/医疗/意外基本覆盖",
                    "strong": "家庭主要风险覆盖充分"
                }[x],
                index=["none", "basic", "adequate", "strong"].index(fd.get('protect-coverage', 'basic'))
            )

            sub_col3, sub_col4 = st.columns(2)
            with sub_col3:
                fd['f-salary-ratio'] = st.number_input("工资收入占比 (%)", min_value=0.0, max_value=100.0, value=float(fd.get('f-salary-ratio', 80.0)))
                fd['f-stability'] = st.selectbox("工作行业稳定性", ["stable", "normal", "volatile"], format_func=lambda x: "非常稳定 (体制内)" if x == "stable" else ("一般稳定性" if x == "normal" else "行业波动较大"), index=["stable", "normal", "volatile"].index(fd.get('f-stability', 'normal')))
            with sub_col4:
                fd['f-bonus-ratio'] = st.number_input("奖金/经营提成占比 (%)", min_value=0.0, max_value=100.0, value=float(fd.get('f-bonus-ratio', 20.0)))
                fd['f-recover-months'] = st.number_input("失业后预计收入恢复期限 (月)", min_value=0, max_value=60, value=int(fd.get('f-recover-months', 6)))

        # 3. 家庭资产明细
        with st.expander("🏦 3. 家庭现有资产 (单位：元)", expanded=True):
            a_col1, a_col2, a_col3 = st.columns(3)
            fd['ast-cash'] = a_col1.number_input("活期现金/存款", min_value=0.0, value=float(fd.get('ast-cash', 50000.0)), step=10000.0)
            fd['ast-mmf'] = a_col2.number_input("货币/短债基金", min_value=0.0, value=float(fd.get('ast-mmf', 100000.0)), step=10000.0)
            fd['ast-ashare'] = a_col3.number_input("A股权益被动基金", min_value=0.0, value=float(fd.get('ast-ashare', 150000.0)), step=10000.0)

            fd['ast-hk'] = a_col1.number_input("港股被动基金", min_value=0.0, value=float(fd.get('ast-hk', 50000.0)), step=10000.0)
            fd['ast-overseas'] = a_col2.number_input("海外权益基金", min_value=0.0, value=float(fd.get('ast-overseas', 50000.0)), step=10000.0)
            fd['ast-gold'] = a_col3.number_input("黄金 ETF/被动基金", min_value=0.0, value=float(fd.get('ast-gold', 20000.0)), step=5000.0)

            fd['ast-house'] = a_col1.number_input("房产当前估值", min_value=0.0, value=float(fd.get('ast-house', 2000000.0)), step=100000.0)
            fd['ast-insurance'] = a_col2.number_input("养老金/保险现金价值", min_value=0.0, value=float(fd.get('ast-insurance', 50000.0)), step=10000.0)
            fd['ast-others'] = a_col3.number_input("其他类别资产", min_value=0.0, value=float(fd.get('ast-others', 0.0)), step=10000.0)

        # 4. 家庭债务明细
        with st.expander("💳 4. 家庭债务负担 (单位：元)", expanded=True):
            d_col1, d_col2, d_col3 = st.columns(3)
            fd['debt-house'] = d_col1.number_input("房贷本金余额", min_value=0.0, value=float(fd.get('debt-house', 800000.0)), step=50000.0)
            fd['debt-car'] = d_col2.number_input("车贷余额", min_value=0.0, value=float(fd.get('debt-car', 50000.0)), step=10000.0)
            fd['debt-consumption'] = d_col3.number_input("消费贷/信用卡余额", min_value=0.0, value=float(fd.get('debt-consumption', 10000.0)), step=5000.0)

            fd['debt-biz'] = d_col1.number_input("经营贷/周转贷余额", min_value=0.0, value=float(fd.get('debt-biz', 0.0)), step=10000.0)
            fd['debt-monthly-repay'] = d_col2.number_input("每月贷款还款总额 (元)", min_value=0.0, value=float(fd.get('debt-monthly-repay', 8500.0)), step=500.0)
            fd['debt-rate'] = d_col3.selectbox("贷款综合利率区间", ["3.5", "4.2", "5.5", "7.5"], format_func=lambda x: "低于 3.5% (低息)" if x == "3.5" else ("3.5% - 4.5% (常态)" if x == "4.2" else ("4.5% - 6.0% (偏高)" if x == "5.5" else "大于 6.0% (高息)")), index=["3.5", "4.2", "5.5", "7.5"].index(fd.get('debt-rate', '4.2')))
            
            fd['debt-pressure'] = st.selectbox("短期是否有还款断流压力", ["no", "yes"], format_func=lambda x: "无，资金链安全滚动" if x == "no" else "有周转压力", index=0 if fd.get('debt-pressure') == 'no' else 1)
            fd['debt-high-interest'] = st.number_input("其中高息债务余额 (元)", min_value=0.0, value=float(fd.get('debt-high-interest', 0.0)), step=5000.0)

        # 5. 投资性格与理财目标
        with st.expander("🚦 5. 投资性格与理财目标", expanded=True):
            i_col1, i_col2 = st.columns(2)
            with i_col1:
                fd['inv-drawdown'] = st.selectbox("可忍受最大本金回撤", ["5", "10", "20", "30", "40"], format_func=lambda x: "小于 5% (极度保守)" if x == "5" else ("5% - 10% (偏保守)" if x == "10" else ("10% - 20% (中度防线)" if x == "20" else ("20% - 30% (适度进取)" if x == "30" else "30%以上 (极强承受)"))), index=["5", "10", "20", "30", "40"].index(fd.get('inv-drawdown', '20')))
                fd['inv-drop-action'] = st.selectbox("如果基金下跌 20% 您的第一反应", ["sell", "stop", "hold", "buy"], format_func=lambda x: "恐慌割肉卖出" if x == "sell" else ("暂停投入持仓观望" if x == "stop" else ("坚定持有等待回暖" if x == "hold" else "低位打折积极补仓")), index=["sell", "stop", "hold", "buy"].index(fd.get('inv-drop-action', 'hold')))
            with i_col2:
                fd['inv-horizon'] = st.selectbox("该组合预计投资期限", ["1", "3", "5", "10"], format_func=lambda x: "1年以内 (超短期)" if x == "1" else ("1 - 3年 (中期配置)" if x == "3" else ("3 - 5年 (中长期)" if x == "5" else "5年以上 (跨周期)")), index=["1", "3", "5", "10"].index(fd.get('inv-horizon', '5')))
                fd['inv-rely'] = st.selectbox("生活费对投资收益依赖度", ["low", "mid", "high"], format_func=lambda x: "低" if x == "low" else ("中" if x == "mid" else "高"), index=["low", "mid", "high"].index(fd.get('inv-rely', 'low')))

            fd['inv-withdraw-monthly'] = st.selectbox("是否需要每月从该投资中固定提取生活费", ["no", "yes"], format_func=lambda x: "否，分红再投资累计复利" if x == "no" else "是，需要每月固定提取生活金", index=0 if fd.get('inv-withdraw-monthly') == 'no' else 1)

            st.write("主要投资核心目标 (可多选)")
            g_cols = st.columns(4)
            fd['goal-cash'] = g_cols[0].checkbox("现金流补充", value=fd.get('goal-cash', False), key="goal_cash_checkbox")
            fd['goal-edu'] = g_cols[1].checkbox("子女教育金", value=fd.get('goal-edu', False), key="goal_edu_checkbox")
            fd['goal-pension'] = g_cols[2].checkbox("养老储备", value=fd.get('goal-pension', False), key="goal_pension_checkbox")
            fd['goal-house'] = g_cols[3].checkbox("买房/换房", value=fd.get('goal-house', False), key="goal_house_checkbox")
            fd['goal-protect'] = g_cols[0].checkbox("财富保值", value=fd.get('goal-protect', False), key="goal_protect_checkbox")
            fd['goal-growth'] = g_cols[1].checkbox("资产增值", value=fd.get('goal-growth', False), key="goal_growth_checkbox")
            fd['goal-retire'] = g_cols[2].checkbox("提前退休", value=fd.get('goal-retire', False), key="goal_retire_checkbox")

        # 保存更新
        st.session_state.family_data = fd

    with col_right:
        # 指标计算逻辑
        total_assets = (fd['ast-cash'] + fd['ast-mmf'] + fd['ast-ashare'] + fd['ast-hk'] + 
                        fd['ast-overseas'] + fd['ast-gold'] + fd['ast-house'] + fd['ast-insurance'] + fd['ast-others'])
        
        total_liabilities = fd['debt-house'] + fd['debt-car'] + fd['debt-consumption'] + fd['debt-biz']
        net_worth = total_assets - total_liabilities
        
        leverage = total_liabilities / total_assets if total_assets > 0 else 0.0
        repay_income_ratio = fd['debt-monthly-repay'] / fd['f-monthly-income'] if fd['f-monthly-income'] > 0 else 0.0
        surplus_ratio = fd['f-surplus-income'] / fd['f-monthly-income'] if fd['f-monthly-income'] > 0 else 0.0
        
        liquid_cash = fd['ast-cash'] + fd['ast-mmf']
        monthly_essential_ex = max(fd.get('f-essential-expense', 0.0), fd['f-fixed-expense'] * 0.7, 1.0)
        monthly_required_outflow = monthly_essential_ex + fd.get('debt-monthly-repay', 0.0)
        cash_coverage_months = liquid_cash / monthly_required_outflow
        
        investable_assets = fd['ast-cash'] + fd['ast-mmf'] + fd['ast-ashare'] + fd['ast-hk'] + fd['ast-overseas'] + fd['ast-gold'] + fd['ast-others']
        equity_assets = fd['ast-ashare'] + fd['ast-hk'] + fd['ast-overseas']
        equity_invest_ratio = equity_assets / investable_assets if investable_assets > 0 else 0.0
        
        # 集中度
        concentration = 0.0
        if equity_assets > 0:
            concentration = max(fd['ast-ashare'], fd['ast-hk'], fd['ast-overseas']) / equity_assets

        # 脆弱度
        vulnerability = 0
        if cash_coverage_months < 3: vulnerability += 30
        elif cash_coverage_months < 6: vulnerability += 15
        if repay_income_ratio > 0.4: vulnerability += 25
        elif repay_income_ratio > 0.25: vulnerability += 12
        if fd['f-stability'] == 'volatile': vulnerability += 15
        elif fd['f-stability'] == 'normal': vulnerability += 7
        if fd['f-income-sources'] == 1: vulnerability += 15
        if fd['debt-pressure'] == 'yes': vulnerability += 15
        if fd.get('debt-high-interest', 0.0) > 0: vulnerability += 10
        if fd.get('protect-coverage') == 'none': vulnerability += 10
        elif fd.get('protect-coverage') in ('adequate', 'strong'): vulnerability -= 5
        vulnerability = max(0, min(vulnerability, 100))

        aggressiveness = 0
        aggressiveness += min(round(equity_invest_ratio * 50), 50)
        drawdown_scores = {'5': 5, '10': 15, '20': 35, '30': 60, '40': 85}
        aggressiveness += drawdown_scores.get(fd['inv-drawdown'], 15) * 0.4
        action_scores = {'sell': 5, 'stop': 15, 'hold': 40, 'buy': 75}
        aggressiveness += action_scores.get(fd['inv-drop-action'], 30) * 0.25
        aggressiveness = min(round(aggressiveness), 100)

        # 运行配置诊断
        res = portfolio_engine.evaluate_family_profile(
            fd, investable_assets, net_worth, total_assets,
            leverage, repay_income_ratio, surplus_ratio, cash_coverage_months,
            [], int(fd['inv-drawdown'])
        )

        # 同步阻断状态
        st.session_state.is_prohibit_aggressive = res['isProhibitAggressive']
        st.session_state.family_aggressiveness = aggressiveness

        # UI呈现
        color_hex = "#EF4444" if "🚨" in res['profileTitle'] or "⚠️" in res['profileTitle'] else ("#10B981" if "💎" in res['profileTitle'] else "#3B82F6")
        st.markdown(f"""
        <div class='card' style='border: 1px solid {color_hex};'>
            <div class='card-title' style='color:{color_hex}; border-left-color:{color_hex};'>📊 家庭财务健康诊断</div>
            <h3 style='margin-top:0; color:#102033;'>{res['profileTitle']}</h3>
            <p style='font-size:0.92rem; line-height:1.4;'>{res['profileDiag']}</p>
            <blockquote style='font-style:italic; font-size:0.85rem; color:#587084; border-left:2px solid #DCE7EF; padding-left:10px;'>{res['quote']}</blockquote>
        </div>
        """, unsafe_allow_html=True)

        # 四类钱配置合理性分析
        four_money = res.get('fourMoney')
        if four_money:
            color_map = {
                "var(--accent-red)": "#EF4444",
                "var(--accent-orange)": "#F59E0B",
                "var(--accent-emerald)": "#10B981",
                "var(--accent-blue)": "#3B82F6",
                "var(--text-secondary)": "#587084",
            }

            def css_color(value):
                return color_map.get(value, value)

            def fmt_amount(value):
                amount = float(value or 0)
                if amount >= 100000000:
                    return f"{amount / 100000000:.2f} 亿元"
                return f"{amount / 10000:.1f} 万元"

            cards = []
            for item in four_money.get('buckets', []):
                item_color = css_color(item.get('color', '#587084'))
                cards.append(
                    f"<div style='background:#FBFDFE; border:1px solid #DCE7EF; border-left:4px solid {item_color}; border-radius:8px; padding:12px;'>"
                    f"<div style='display:flex; justify-content:space-between; gap:10px; align-items:flex-start; margin-bottom:8px;'>"
                    f"<div><div style='font-size:0.92rem; font-weight:700; color:#102033;'>{item['title']}</div>"
                    f"<div style='font-size:0.72rem; color:#587084; line-height:1.35; margin-top:2px;'>{item['subtitle']}</div></div>"
                    f"<span style='font-size:0.72rem; font-weight:700; color:{item_color}; background:rgba(16,32,51,0.05); padding:3px 8px; border-radius:999px;'>{item['status']}</span>"
                    f"</div>"
                    f"<div style='font-size:1.05rem; font-weight:700; color:#102033; margin-bottom:4px;'>{fmt_amount(item['amount'])} "
                    f"<span style='font-size:0.76rem; color:#587084; font-weight:500;'>占总资产 {item['ratio'] * 100:.1f}%</span></div>"
                    f"<div style='font-size:0.72rem; line-height:1.45; color:#587084;'>"
                    f"<div>建议区间：{item['targetText']}</div><div>资产口径：{item['components']}</div>"
                    f"<div style='margin-top:5px; color:{item_color};'>{item['advice']}</div>"
                    f"</div></div>"
                )
            cards_html = "".join(cards)

            st.markdown(f"""
            <div class='card'>
                <div class='card-title'>🧭 四类钱配置合理性分析</div>
                <div style='font-size:0.8rem; color:#587084; margin-bottom:12px; line-height:1.4;'>
                    按家庭用途拆分为“要花的钱、保命的钱、生钱的钱、保本升值的钱”，优先判断基础防线是否足够，再判断增长配置是否过度。
                </div>
                <div style='background:#FBFDFE; border:1px dashed #DCE7EF; border-radius:6px; padding:10px 12px; font-size:0.82rem; line-height:1.45; margin-bottom:12px;'>
                    <strong style='color:{css_color(four_money.get('overallColor', '#587084'))};'>{four_money['overallStatus']} · {four_money['score']} 分</strong>
                    <span style='color:#587084; margin-left:8px;'>{four_money['summary']}</span>
                </div>
                <div style='display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px;'>
                    {cards_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("为什么是这个数", expanded=False):
            explain_metrics = calculate_family_diagnostics(fd)
            for line in family_rule_lines(explain_metrics):
                st.write(f"- {line}")
            st.caption("以上仅解释体检规则，不构成投资建议，不承诺分红或收益。")

        # 三桶可视化展示
        st.markdown(f"""
        <div class='card'>
            <div class='card-title'>🪣 三桶资产防御防线配置建议</div>
            <div style='font-size: 0.8rem; color:#587084; margin-bottom:15px;'>
                配置建议：安全储备 {res['safety']}% | 权益增长 {res['longterm']}% | 综合对冲 {res['hedge']}%
            </div>
        """, unsafe_allow_html=True)
        # 用堆叠条形图表达三桶比例
        fig_buckets = go.Figure()
        fig_buckets.add_trace(go.Bar(
            y=['配置比例'], x=[res['safety']], name='安全防御桶 (现金/短债)', orientation='h', marker_color='#10B981'
        ))
        fig_buckets.add_trace(go.Bar(
            y=['配置比例'], x=[res['longterm']], name='长期权益桶 (红利/宽基/成长)', orientation='h', marker_color='#3B82F6'
        ))
        fig_buckets.add_trace(go.Bar(
            y=['配置比例'], x=[res['hedge']], name='综合对冲桶 (黄金/债券对冲)', orientation='h', marker_color='#F59E0B'
        ))
        fig_buckets.update_layout(
            barmode='stack', height=130, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#102033', margin=dict(t=10, b=10, l=10, r=10), showlegend=True, legend=dict(orientation='h', y=-0.5)
        )
        st.plotly_chart(fig_buckets, use_container_width=True)
        
        st.markdown(f"""
            <div style='font-size: 0.85rem; margin-top: 15px;'>
                <strong>🤔 为什么这么配？（资产配置结构原理解析）</strong>
                <p style='color:#587084; line-height:1.4; background: #FBFDFE; padding: 8px; border-radius: 4px; border: 1px dashed #DCE7EF;'>{res['reason']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 指标诊断值
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>刚性支出现金覆盖月数</div>
            <div class='metric-value'>{cash_coverage_months:.1f} 个月</div>
            <hr style='border:0; border-top:1px solid #DCE7EF; margin:10px 0;'>
            <table style='font-size:0.85rem; width:100%; border-collapse:collapse; color:#587084;'>
                <tr><td>家庭资产负债率 (LTV)</td><td style='text-align:right; font-weight:600; color:#102033;'>{leverage*100:.1f}%</td></tr>
                <tr><td>月贷款还本付息比 (DSR)</td><td style='text-align:right; font-weight:600; color:#102033;'>{repay_income_ratio*100:.1f}%</td></tr>
                <tr><td>月可支配储蓄结余率</td><td style='text-align:right; font-weight:600; color:#102033;'>{surplus_ratio*100:.1f}%</td></tr>
                <tr><td>理财市场集中度风险 (HHI)</td><td style='text-align:right; font-weight:600; color:#102033;'>{concentration*100:.1f}%</td></tr>
                <tr style='color:#EF4444;'><td>家庭财务脆弱度评分</td><td style='text-align:right; font-weight:600;'>{vulnerability} 分</td></tr>
                <tr style='color:#3B82F6;'><td>风险进攻偏好指数</td><td style='text-align:right; font-weight:600;'>{aggressiveness} 分</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        # 饼图绘制
        st.markdown("### 📊 资产与负债结构图表")
        fig_assets = px.pie(
            names=['安全现金储备', 'A股被动权益', '港股红利被动', '海外被动基金', '黄金避险对冲', '房产非流动性', '养老寿险保障', '其他大类'],
            values=[fd['ast-cash'] + fd['ast-mmf'], fd['ast-ashare'], fd['ast-hk'], fd['ast-overseas'], fd['ast-gold'], fd['ast-house'], fd['ast-insurance'], fd['ast-others']],
            title="家庭资产占比",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_assets.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#102033', height=240, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_assets, use_container_width=True)

# ==========================================
# 模块 2: 资产配置与股息测算看板
# ==========================================
elif menu == "2. 资产配置与股息测算看板":
    st.markdown("<h1 style='color:#102033; margin-bottom:10px;'>📊 资产配置与股息测算看板</h1>", unsafe_allow_html=True)
    st.write(f"当前可用总本金 **{principal:.1f}** 万元，其中已调拨 **{buffer_seed:.1f}** 万元进入初始缓冲池，实际进入组合配置的可投资本金为 **{invest_principal:.1f}** 万元。")
    st.info("口径与免责：本看板仅用于 ETF/指数基金/大类资产配置测算，不构成投资建议，不推荐单只股票，不承诺任何分红、票息或收益。成长资产、黄金和 REITs 备选不计入稳定现金流。")
    st.markdown("""
    <div class='card' style='border-left:4px solid #F59E0B;'>
        <div class='card-title-text'>中国风险溢价覆盖检查</div>
        <div style='font-size:0.86rem;color:#334155;line-height:1.75;margin-top:10px;'>
            <strong>已覆盖：</strong>现金/短债 → 利率债 → 红利低波 → 大盘/中盘宽基 → 国内科技 → 黄金/REITs。<br>
            <strong>本次补全：</strong>中证1000（512100）补小盘层级，恒生科技（513180）补离岸中国成长层级；两者默认均为 <strong>0% 观察位</strong>。<br>
            <strong>正确使用：</strong>风险溢价是长期补偿和估值检查工具，不是短线买入信号。先确保现金缓冲与确定性支出隔离；启用时从“国内权益桶”或“高波动成长桶”内部置换，不从缓冲池加钱，也不要同时把两项都拉到高权重。
        </div>
    </div>
    """, unsafe_allow_html=True)
    current_family_metrics = calculate_family_diagnostics(st.session_state.family_data)
    current_health_score = current_family_metrics['res'].get('fourMoney', {}).get('score')
    if current_health_score is not None:
        st.markdown(f"""
        <div class='card' style='border-left:4px solid #587084;'>
            <div class='metric-label'>家庭基础健康分</div>
            <div class='metric-value' style='color:#587084;'>{current_health_score} 分</div>
            <div style='font-size:0.82rem;color:#587084;'>仅随家庭收支、资产负债与保障信息变化；ETF 权重调整不会改写该分数。</div>
        </div>
        """, unsafe_allow_html=True)
    st.caption(f"行情/股息率数据来源：{data_freshness_label()}")
    
    st.markdown("### 🛠️ 组合权重与股息率调整")
    
    cols = st.columns(4)
    weights = {}
    yields = {}
    
    idx = 0
    for code, info in ASSETS_CONFIG.items():
        col = cols[idx % 4]
        with col:
            st.markdown(f"""
            <div class='card' style='padding: 12px; margin-bottom: 5px; border-radius:8px;'>
                <div style='font-weight:600; color:#102033; font-size:0.85rem;'>{info['name']}</div>
                <div style='color:#587084; font-size:0.7rem; margin-bottom:5px;'>
                    代码: {code} | 角色: <span style='color:#10B981;'>{info['role']}</span>
                </div>
                <div style='display:inline-block;font-size:0.68rem;color:#3B82F6;background:#EFF6FF;border:1px solid #BFDBFE;border-radius:999px;padding:2px 8px;'>价格：{price_freshness_label()}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 使用 SessionState 联动的 Slider
            weight = st.slider(
                f"权重 (%) - {code}", 
                min_value=0.0, 
                max_value=50.0, 
                value=float(st.session_state[f"w_{code}"]), 
                step=0.5, 
                key=f"w_{code}_slider",
                on_change=on_weight_changed
            )
            # 同步回状态
            st.session_state[f"w_{code}"] = weight
            
            # 股息率只读，在线抓取展示
            st.write(f"当前测算收益率: **{info['yield']:.2f}%**")
            st.caption(f"收益率口径：{yield_freshness_label()}；不承诺分红或收益。")
            
            weights[code] = weight
            yields[code] = info['yield']
        idx += 1

    # 调用计算引擎进行核心核算
    res = portfolio_engine.calculate_portfolio(
        weights,
        ASSETS_CONFIG,
        principal,
        buffer_seed,
        money_market_rate
    )
    fit = portfolio_engine.evaluate_portfolio_fit(
        weights, ASSETS_CONFIG, current_family_metrics['res'].get('isProhibitAggressive', False)
    )
    if fit['isMatched']:
        st.success("组合适配反馈：当前权重未触发现有集中度或家庭风险阻断规则。")
    else:
        st.warning("组合适配反馈：" + "；".join(fit['messages']))

    # 验证权重是否满100%
    total_weight = res['totalWeight']
    if not np.isclose(total_weight, 100.0):
        st.error(f"⚠️ 当前配置的总权重之和为 **{total_weight:.1f}%**，配置权重之和必须正好等于 **100.0%** 测算数值方才可信。")
    else:
        st.success("✅ 组合总权重等于 100%，配置方案就绪！")

    # 组合预期产出卡片
    st.markdown("### 🎯 组合预期产出看板")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>加权现金流收益率</div>
            <div class='metric-value' style='color:#10B981;'>{res['blendedCashYield']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>增长预期收益率</div>
            <div class='metric-value' style='color:#A78BFA;'>{res['blendedGrowthReturn']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        net_annual = res.get('expectedAnnualDividendAfterCost', res['expectedAnnualDividend']) or res['expectedAnnualDividend']
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>预期年税后分红/利息 (扣费扣税后)</div>
            <div class='metric-value'>¥{net_annual:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        net_monthly = res.get('expectedMonthlyDividendAfterCost', res['expectedMonthlyDividend']) or res['expectedMonthlyDividend']
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>折合月均现金流 (扣费扣税后)</div>
            <div class='metric-value'>¥{net_monthly:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col5:
        gap = (target_monthly * 10000) - res['expectedMonthlyDividend']
        color = "#10B981" if gap <= 0 else "#EF4444"
        gap_text = f"-¥{-gap:,.0f} (超额)" if gap <= 0 else f"¥{gap:,.0f} (缺口)"
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>期望月现金流缺口</div>
            <div class='metric-value' style='color:{color}; font-size:1.6rem;'>{gap_text}</div>
        </div>
        """, unsafe_allow_html=True)
    st.caption(
        f"{res.get('costNote', '')} 毛分红 ¥{res['expectedAnnualDividend']:,.0f}（年），"
        f"月均 ¥{res['expectedMonthlyDividend']:,.0f}。"
    )

    # 饼图与明细表格
    st.markdown("### 📋 投资明细与比重分布")

    # 数据质量告警：声明为稳定现金流但近12个月无真实分红记录的资产必须显式提示。
    dq_warnings = [a for a in live_data_quality_alerts if a.get('severity') == 'warning']
    dq_errors = [a for a in live_data_quality_alerts if a.get('severity') == 'error']
    if dq_warnings or dq_errors:
        warn_list = "、".join(f"{a.get('name', '')}({a.get('code', '')})" for a in dq_warnings)
        err_list = "、".join(f"{a.get('name', '')}({a.get('code', '')})" for a in dq_errors)
        err_text = f"；分红数据源抓取失败：{err_list}" if err_list else ""
        st.warning(
            "以下标记为稳定现金流的资产近12个月在数据源中无真实现金分配记录，"
            "其收益率与现金流为规划假设而非可核验分红，请谨慎参考："
            f"{warn_list if warn_list else '（无）'}{err_text}"
        )
    
    def cashflow_attribute(detail):
        if detail.get('role') == 'hedge' or detail.get('income_type') == 'hedge':
            return '对冲资产'
        if detail.get('stableCashflow'):
            yield_method = ASSETS_CONFIG.get(detail['code'], {}).get('yield_method')
            if yield_method == 'trailing_12m_cash_distributions':
                return '稳定现金流 · 真实分红'
            return '稳定现金流 · 规划假设'
        return '非稳定现金流'

    # 资产角色/市场的分布统计
    role_weights = {}
    market_weights = {}
    tech_weight = 0.0
    dividend_weight = 0.0
    for detail in res['assetDetails']:
        role = detail['role']
        role_weights[role] = role_weights.get(role, 0.0) + detail['weight']
        market = detail['market']
        market_weights[market] = market_weights.get(market, 0.0) + detail['weight']
        if role in ['tech_growth', 'overseas_tech', 'china_offshore_growth']:
            tech_weight += detail['weight']
        if role == 'dividend_income':
            dividend_weight += detail['weight']

    concentration_msgs = []
    for role, weight in role_weights.items():
        if weight > 45:
            concentration_msgs.append(f"单一角色 {role} 已达 {weight:.1f}%，建议降低角色集中度。")
    for market, weight in market_weights.items():
        if weight > 70:
            concentration_msgs.append(f"单一市场 {market} 已达 {weight:.1f}%，建议增加市场和币种分散。")
    if tech_weight > 25:
        concentration_msgs.append(f"科技相关资产已达 {tech_weight:.1f}%，高波动仓位需要受家庭体检风险约束。")
    if dividend_weight > 45:
        concentration_msgs.append(f"红利类资产已达 {dividend_weight:.1f}%，现金流底盘过厚，增长弹性不足。")

    if concentration_msgs:
        st.warning("集中度提示：" + "；".join(concentration_msgs) + "。所有提示仅作配置风险边界参考，不构成投资建议，不承诺分红或收益。")
    else:
        st.success("分散度检查：当前组合未触发角色、市场、科技或红利集中度阈值。测算不构成投资建议，不承诺分红或收益。")

    pie_view = st.radio("饼图视图", ["按资产角色", "按市场"], horizontal=True)
    pie_weights = role_weights if pie_view == "按资产角色" else market_weights
    
    fig_role = px.pie(
        names=list(pie_weights.keys()),
        values=list(pie_weights.values()),
        title="组合资产角色分布" if pie_view == "按资产角色" else "组合市场分布",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_role.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#102033', height=280)
    st.plotly_chart(fig_role, use_container_width=True)

    # 标的资产表格明细
    table_rows = []
    for d in res['assetDetails']:
        table_rows.append({
            '代码': d['code'],
            '标的名称': d['name'],
            '配置角色': d['role'],
            '市场/波动': f"{d['market']} / {d['volatility_level']}",
            '现金流属性': cashflow_attribute(d),
            '权重 (%)': f"{d['weight']:.1f}%",
            '分配金额': f"{d['allocatedAmt']:.2f} 万元",
            '股息/预期回报': f"{d['yield']:.2f}% / {d['estimated_return']:.2f}%",
            '价格来源': price_freshness_label(),
            '收益率口径': yield_freshness_label(),
            '预计年分红/利息': f"¥{d['expectedAnnualDiv']:,.0f}" if d['stableCashflow'] else "不计入",
            '定位与主要风险': f"🎯 {d['strategy_note']}  ⚠️ {d['risk_note']}"
        })
    st.table(pd.DataFrame(table_rows))

# ==========================================
# 模块 3: 现金缓冲池平滑模拟器
# ==========================================
elif menu == "2. 缓冲池与现金流模拟":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>⏱️ 现金缓冲池平滑模拟器</h1>", unsafe_allow_html=True)
    st.write(f"大多数分红在 5-8 月密集派发。本模拟器展示了分红按真实月份归集到缓冲池，并每月固定流出 {target_monthly:.2f} 万元生活费的 36 个月动态过程。")
    
    # 1. 整理各资产分红月份和比例
    # weights, yields 重新取自默认或直接读侧边栏以确保一致
    weights = {code: info['weight']/100 for code, info in DEFAULT_ASSETS.items()}
    yields = {code: info['yield']/100 for code, info in DEFAULT_ASSETS.items()}
    
    # 2. 模拟 36 个月的现金流
    months_range = 36
    monthly_withdraw = target_monthly * 10000
    
    buffer_balance = [buffer_seed * 10000] # 起始资金（元）
    monthly_dividends_history = []
    interest_earned_history = []
    
    # 构造日历月份
    # 假设从 1 月开始模拟
    for t in range(1, months_range + 1):
        c_month = ((t - 1) % 12) + 1
        
        # 计算当月收到的总分红
        month_dividend = 0.0
        for code, info in DEFAULT_ASSETS.items():
            month_dist_ratio = info['months'].get(c_month, 0.0)
            if month_dist_ratio > 0.0:
                asset_value = invest_principal * weights[code] * 10000 # 元
                dividend_income = asset_value * yields[code] * month_dist_ratio
                month_dividend += dividend_income
                
        # 缓冲池当期利息计算 (期初余额计算当月利息)
        current_interest = buffer_balance[-1] * (money_market_rate / 12.0)
        
        # 缓冲池期末余额 = 期初余额 + 当月分红 + 利息 - 当月提取金额
        next_balance = buffer_balance[-1] + month_dividend + current_interest - monthly_withdraw
        
        # 存储结果
        monthly_dividends_history.append(month_dividend)
        interest_earned_history.append(current_interest)
        buffer_balance.append(next_balance)
        
    # 去除最后一个多余的期末余额，保留 36 个月的变动
    buffer_history = buffer_balance[:-1]
    
    # 创建 DataFrame
    timeline_df = pd.DataFrame({
        '模拟月份': [f"第 {t} 个月 (阴历 {((t-1)%12)+1}月)" for t in range(1, months_range + 1)],
        '当月收到分红 (元)': monthly_dividends_history,
        '当月利息收益 (元)': interest_earned_history,
        '缓冲池余额 (元)': buffer_history,
        '固定生活费流出 (元)': [monthly_withdraw] * months_range
    })
    
    # 极低余额警告
    min_buffer = min(buffer_history)
    st.markdown("### 🔍 缓冲池安全性体检")
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>初始缓冲池预留</div>
            <div class='metric-value'>¥{buffer_seed*10000:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with b_col2:
        status_color = "#10B981" if min_buffer > 0 else "#EF4444"
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>缓冲池最低水位</div>
            <div class='metric-value' style='color:{status_color};'>¥{min_buffer:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with b_col3:
        tot_div_sum = sum(monthly_dividends_history)
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>3年预计累计红利</div>
            <div class='metric-value'>¥{tot_div_sum:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
    if min_buffer <= 0:
        st.error("⚠️ **缓冲池水位警报**：模拟显示缓冲池资金在部分月份会出现**亏空（余额为负数）**！说明您的“初始缓冲池储备”不足以支持分红发放前的日常支出，或者整体资产股息率相对于月消费过低。建议调高初始储备或增加本金。")
    else:
        st.success("✅ **缓冲池平滑成功**：在 36 个月的模拟周期内，缓冲池余额始终大于 0。您的日常生活现金流将完全不受分红淡旺季影响！")
        
    # 可视化图表
    st.markdown("### 📈 36个月缓冲池水位与红利到账图")
    fig = go.Figure()
    
    # 缓冲池余额柱状图
    fig.add_trace(go.Scatter(
        x=timeline_df['模拟月份'], 
        y=timeline_df['缓冲池余额 (元)'],
        mode='lines+markers',
        name='缓冲池期初余额 (元)',
        line=dict(color='#10B981', width=3),
        marker=dict(size=6)
    ))
    fig_buffer.add_trace(go.Bar(
        x=timeline_months,
        y=sim['dividendIncomeHistory'],
        name='红利收入 (元)',
        marker_color='#3B82F6',
        opacity=0.8
    ))
    fig_buffer.add_trace(go.Bar(
        x=timeline_months,
        y=sim['cashInterestIncomeHistory'],
        name='票息/货基收入 (元)',
        marker_color='#10B981',
        opacity=0.8
    ))
    if rebalance_harvest:
        fig_buffer.add_trace(go.Bar(
            x=timeline_months,
            y=sim['harvestHistory'],
            name='非稳定卖出补流 (元)',
            marker_color='#A78BFA',
            opacity=0.8
        ))
    if min_buffer <= 0:
        idx = weakest_month - 1
        fig_buffer.add_hline(y=0, line_dash="dot", line_color="#EF4444")
        fig_buffer.add_trace(go.Scatter(
            x=[timeline_months[idx]],
            y=[min_buffer],
            mode='markers+text',
            text=['最低点'],
            textposition='top center',
            name='压力最低点',
            marker=dict(color='#EF4444', size=11, symbol='diamond')
        ))
    
    fig_buffer.update_layout(
        title="36个月缓冲池水位与稳定现金流动态趋势图",
        xaxis_title="模拟时间线",
        yaxis_title="水位/金额 (元)",
        barmode='stack',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#102033',
        hovermode="x unified"
    )
    st.plotly_chart(fig_buffer, use_container_width=True)

    # 导出明细数据
    with st.expander("📂 查看36个月现金流流转明细表格"):
        timeline_df = pd.DataFrame({
            '模拟月份': timeline_months,
            '红利收入 (元)': sim['dividendIncomeHistory'],
            '票息/货基收入 (元)': sim['cashInterestIncomeHistory'],
            '缓冲池利息 (元)': sim['bufferInterestHistory'],
            '非稳定卖出补流 (元)': sim['harvestHistory'],
            '期末缓冲池余额 (元)': sim['bufferHistory']
        })
        st.dataframe(timeline_df.style.format({
            '红利收入 (元)': '¥{:,.0f}',
            '票息/货基收入 (元)': '¥{:,.0f}',
            '缓冲池利息 (元)': '¥{:,.2f}',
            '非稳定卖出补流 (元)': '¥{:,.0f}',
            '期末缓冲池余额 (元)': '¥{:,.0f}'
        }))

# ==========================================
# 模块 4: 估值温度计与测算工具
# ==========================================
elif menu == "3. 估值温度计与建仓建议":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>🌡️ 估值温度计与建仓智能助手</h1>", unsafe_allow_html=True)
    st.write("红利策略的核心法则：**在股息率高（估值便宜）时加大买入，在股息率低（估值昂贵）时减少或暂停买入**。本模块监控红利指数温度，并动态生成建仓额度建议。")
    
    # 模拟数据：红利低波指数的历史股息率波动 (例如 3.8% ~ 6.2%)
    np.random.seed(42)
    history_dates = pd.date_range(end="2026-05-27", periods=200, freq="W")
    # 生成平滑的历史股息率序列
    noise = np.random.normal(0, 0.08, 200)
    base_yield = 4.8 + np.sin(np.linspace(0, 10, 200)) * 0.8 + noise
    
    # 最后一期作为当前股息率
    current_idx_yield = round(base_yield[-1], 2)
    
    # 计算当前历史百分位
    percentile = round((base_yield < current_idx_yield).mean() * 100, 1)
    
    # 估值分级与定投比例因子
    if percentile >= 70.0:
        valuation_zone = "极具性价比（股息率高，估值便宜）"
        factor = 1.3
        color = "#10B981" # 绿色
        tips = "建议：市场目前股息回报极为丰厚，建议加大配置买入额度！"
    elif percentile >= 30.0:
        valuation_zone = "估值合理（股息率适中）"
        factor = 1.0
        color = "#F59E0B" # 黄色
        tips = "建议：估值处于正常水平，建议保持既定的定投节奏买入。"
    else:
        valuation_zone = "估值偏贵（股息率较低）"
        factor = 0.5
        color = "#EF4444" # 红色
        tips = "建议：指数估值过热，股息吸引力下降，建议减少或暂停定投建仓，资金暂留货币基金。"
        
    st.markdown("### 📊 指数估值温度仪")
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>中证红利低波当前股息率</div>
            <div class='metric-value' style='color:#3B82F6;'>{current_idx_yield:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col2:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>历史股息率百分位</div>
            <div class='metric-value' style='color:{color};'>{percentile}%</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col3:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>动态定投调节因子</div>
            <div class='metric-value'>{factor}x</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.03); border:1px solid {color}; border-radius:8px; padding:15px; margin-bottom:20px;'>
        <h4 style='color:{color};margin-top:0;'>🏷️ 估值评级：{valuation_zone}</h4>
        <p style='color:#E2E8F0;font-size:0.95rem;margin-bottom:0;'>{tips}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 建仓金额建议
    st.markdown("### 🎯 动态定投建仓方案生成")
    base_dca = st.number_input("您的基础月定投金额 (万元)", min_value=0.5, max_value=200.0, value=5.0, step=0.5)
    adjusted_dca = base_dca * factor
    
    st.markdown(f"基于动态调节因子 **{factor}x**，本月推荐建仓总金额为 **{adjusted_dca:.2f}** 万元。")
    
    # 推荐明细表
    rec_data = []
    for code, info in DEFAULT_ASSETS.items():
        rec_amt = adjusted_dca * (info['weight']/100.0)
        rec_data.append({
            '证券代码': code,
            '证券名称': info['name'],
            '配置占比': f"{info['weight']}%",
            '本月买入推荐金额 (元)': f"¥{rec_amt * 10000:,.0f}"
        })

    def index_role(index_code_value):
        for asset_info in ASSETS_CONFIG.values():
            if asset_target_index(asset_info) == index_code_value:
                return asset_info.get('role')
        return valuation_meta(index_code_value)['role']

    def valuation_data_status(info, target_index, asset_res, no_timing_role):
        if no_timing_role:
            return "不做估值择时，按基础比例"
        meta = valuation_meta(target_index, info.get('role'))
        if asset_res.get('hasHistory'):
            return f"有历史数据：按{meta['metric']}校准"
        role = info.get('role')
        if role in ('overseas_broad', 'overseas_tech', 'china_offshore_growth'):
            return f"缺{meta['metric']}历史：1.0x，关注汇率/QDII溢价"
        if role == 'dividend_income':
            return f"缺{meta['metric']}历史：1.0x，不判断高股息低估"
        if role in ('tech_growth', 'small_cap'):
            return f"缺{meta['metric']}历史：1.0x，高波动不放大"
        return f"缺{meta['metric']}历史：1.0x 基础计划"

    valuation_index_set = {item.get('index_code') for item in history_data if item.get('index_code')}
    target_index_set = {asset_target_index(info) for info in ASSETS_CONFIG.values() if asset_target_index(info)}
    missing_indexes = sorted(target_index_set - valuation_index_set)
    covered_indexes = sorted(valuation_index_set)
    has_any_valuation_history = len(covered_indexes) > 0

    st.markdown("### 🧭 估值数据覆盖面板")
    cover_col1, cover_col2 = st.columns(2)
    with cover_col1:
        st.info("valuation_history.json 已覆盖：" + ("、".join(covered_indexes) if covered_indexes else "暂无"))
    with cover_col2:
        missing_detail = []
        for idx in missing_indexes:
            linked_assets = [
                f"{info.get('name')}｜{info.get('role')}｜缺{valuation_meta(idx, info.get('role'))['metric']}"
                for info in ASSETS_CONFIG.values()
                if asset_target_index(info) == idx
            ]
            missing_detail.append(f"{idx}: " + "；".join(linked_assets))
        st.warning("资产池缺少估值数据：" + ("；".join(missing_detail) if missing_detail else "无"))

    index_order = ["H30269", "000015", "932039", "HSHYLV", "000300", "000510", "000905", "000852", "000688", "HKTECH", "SPX", "NDX"]
    index_options = [
        f"{code} ({valuation_meta(code)['name']})" + ("" if code in valuation_index_set else " [无历史数据]")
        for code in index_order
    ]
    index_code = st.selectbox("请选择要进行定投校准的指数标的", index_options, index=0)
    index_clean = index_code.split(" ")[0]
    role_to_use = index_role(index_clean)
    selected_meta = valuation_meta(index_clean, role_to_use)

    default_sim = portfolio_engine.simulate_cashflow(
        36,
        target_monthly * 10000.0,
        buffer_seed,
        invest_principal,
        weights,
        ASSETS_CONFIG,
        money_market_rate / 100.0,
        False,
        'neutral',
        datetime.now().month,
        0,
        0,
        False
    )
    dca_context = {
        'dividendWeight': sum(float(weights.get(code, 0.0)) for code, info in ASSETS_CONFIG.items() if info.get('role') == 'dividend_income'),
        'cashflowFeasible': default_sim.get('minBuffer', 0.0) > 0
    }

    res = portfolio_engine.get_dca_adjustment(history_data, index_clean, role_to_use, dca_context)
    has_selected_valuation_history = bool(res.get('hasHistory'))

    st.markdown(f"### 📊 {index_code} 指数温度计指标板")
    is_dividend_role = role_to_use == 'dividend_income'

    def percentile_text(value):
        return "--" if value in (None, "--") else f"{float(value):.1f}%"

    decision_label = "股息率百分位" if is_dividend_role else ("PE/PB较高百分位" if role_to_use == 'domestic_beta' else "PE百分位")
    decision_value = f"{res['percentile']:.1f}%" if has_selected_valuation_history else "--"
    metric_row1 = st.columns(4)
    metric_row1[0].metric("当前 PE（市盈率）", res['pe'])
    metric_row1[1].metric("PE 三年百分位", percentile_text(res.get('pePercentile')))
    metric_row1[2].metric("当前 PB（市净率）", res['pb'])
    metric_row1[3].metric("PB 三年百分位", percentile_text(res.get('pbPercentile')))
    metric_row2 = st.columns(4)
    metric_row2[0].metric("当前指数股息率", res['dividend_yield'])
    metric_row2[1].metric("股息率三年百分位", percentile_text(res.get('dividendYieldPercentile')))
    metric_row2[2].metric(f"定投判断：{decision_label}", decision_value)
    metric_row2[3].metric("定投调节系数", f"{res['factor']:.1f}x")

    if has_selected_valuation_history:
        window_label = "近三年" if res.get('percentileWindow') == '3y' else res.get('percentileWindow', '本地历史')
        source_label = "已验证指数基本面" if res.get('valuationSource') == 'verified_index_fundamentals' else "本地估值历史"
        stale_note = ""
        as_of_raw = res.get('asOf')
        if as_of_raw and as_of_raw != '--':
            try:
                as_of_ms = datetime.strptime(as_of_raw, "%Y-%m-%d")
                market_ms = datetime.strptime(live_data_timestamp[:10], "%Y-%m-%d") if live_data_timestamp else datetime.now()
                diff_days = (market_ms - as_of_ms).days
                if diff_days > 21:
                    stale_note = f"｜⚠️ 估值数据滞后 {diff_days} 天（晚于行情快照），百分位窗口 {window_label}，请留意新鲜度"
                elif diff_days > 7:
                    stale_note = f"｜估值数据滞后 {diff_days} 天"
            except (TypeError, ValueError):
                stale_note = ""
        st.caption(f"数据日期：{as_of_raw or '--'}｜百分位窗口：{window_label}｜口径：市值加权｜来源：{source_label}{stale_note}")
    else:
        st.caption("当前指数缺少可验证估值历史，因此不展示 PE/PB 百分位，也不生成估值判断。")

    # 诊断横幅
    color_banner = "#10B981" if res['factor'] > 1.1 else ("#EF4444" if res['factor'] < 0.9 else "#3B82F6")
    if has_selected_valuation_history:
        st.markdown(f"""
        <div style='background:#FBFDFE; border:1px solid {color_banner}; border-radius:8px; padding:15px; margin-bottom:20px;'>
            <h4 style='color:{color_banner};margin-top:0;'>🏷️ 估值校准结论：{res['valuationZone']}</h4>
            <p style='color:#102033;font-size:0.95rem;margin-bottom:0;'>{res['tips']} 估值温度计只用于调整定投节奏，不构成买卖建议。</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        missing_metric = "股息率历史" if selected_meta['metric'] == '股息率' else "PE/PB 估值历史"
        overseas_tip = " 海外资产还需额外关注汇率、QDII 溢价与跟踪误差风险。" if role_to_use.startswith('overseas') else ""
        st.info(f"{selected_meta['name']}暂无{missing_metric}，DCA 保持 1.0x；不生成低估/高估判断，不构成投资建议。{overseas_tip}")

    # 绘制估值线图
    if has_selected_valuation_history:
        filtered_history = [item for item in history_data if item['index_code'] == index_clean]
        dates = [item['date'] for item in filtered_history]
        y_vals = [float(item['dividend_yield']) if is_dividend_role else float(item['pe']) for item in filtered_history]
        pe_vals = [float(item['pe']) for item in filtered_history]
        pb_vals = [float(item['pb']) for item in filtered_history]
        dy_vals = [float(item.get('dividend_yield') or 0.0) for item in filtered_history]

        fig_val = go.Figure()
        fig_val.add_trace(go.Scatter(
            x=dates,
            y=y_vals,
            mode='lines',
            name='历史股息率' if is_dividend_role else '历史 PE',
            line=dict(color='#3B82F6', width=2),
            customdata=np.stack((pe_vals, pb_vals, dy_vals), axis=-1),
            hovertemplate="日期: %{x}<br>股息率: %{customdata[2]:.2f}%<br>PE: %{customdata[0]:.2f}<br>PB: %{customdata[1]:.2f}<extra></extra>" if is_dividend_role else "日期: %{x}<br>PE: %{customdata[0]:.2f}<br>PB: %{customdata[1]:.2f}<br>股息率: %{customdata[2]:.2f}%<extra></extra>"
        ))

        # 当前水平虚线
        curr_val = float(res['dividend_yield'].replace('%','')) if is_dividend_role else float(res['pe'])
        fig_val.add_trace(go.Scatter(
            x=[dates[0], dates[-1]],
            y=[curr_val, curr_val],
            mode='lines',
            name='当前股息率' if is_dividend_role else '当前 PE',
            line=dict(color=color_banner, dash='dash')
        ))

        fig_val.update_layout(
            title=f"{index_code} 指数历史走势图",
            xaxis_title="日期",
            yaxis_title="股息率 (%)" if is_dividend_role else "PE (市盈率)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#102033',
            height=300
        )
        st.plotly_chart(fig_val, use_container_width=True)
    else:
        missing_metric = "股息率历史" if selected_meta['metric'] == '股息率' else "PE/PB 估值历史"
        st.info(f"{selected_meta['name']}暂无{missing_metric}，图表已清空，DCA 保持 1.0x。")

    # 动态定投测算：放在历史走势图下方，保证明细表有完整横向空间。
    st.markdown("### 🎯 本月测算额度调节生成器")
    dca_col1, dca_col2 = st.columns([1.0, 1.4])
    with dca_col1:
        base_dca = st.number_input("基础月定投预算 (万元)", min_value=1.0, max_value=200.0, value=32.3, step=1.0)
    with dca_col2:
        dca_mode = st.radio(
            "定投校准模式",
            ["预算固定模式（默认）：总额不变，只调整分配", "估值放大/缩小模式：总额随 factor 变化"],
            index=0,
            horizontal=True
        )
    fixed_budget_mode = dca_mode.startswith("预算固定")

    st.markdown("上方指数仅用于查看温度计。下方组合定投按每个资产自己的 `target_index_code` 和 `role` 分别计算；预算固定模式下总额不放大。")

    timing_excluded_roles = {'cash', 'hedge', 'bond_duration'}
    calc_rows = []
    for code, info in ASSETS_CONFIG.items():
        target_index = asset_target_index(info)
        role = info.get('role')
        original_weight = float(weights.get(code, 0.0))
        no_timing_role = role in timing_excluded_roles or not target_index
        if no_timing_role:
            asset_res = {
                'hasHistory': False,
                'percentile': 50.0,
                'factor': 1.0,
                'pe': '--',
                'pb': '--',
                'dividend_yield': '--',
                'pePercentile': '--',
                'pbPercentile': '--',
                'dividendYieldPercentile': '--',
                'valuationZone': '不做估值择时，按基础比例',
                'tips': ''
            }
        else:
            asset_res = portfolio_engine.get_dca_adjustment(history_data, target_index, role, dca_context)
        raw_score = original_weight * float(asset_res['factor'])
        data_status = valuation_data_status(info, target_index, asset_res, no_timing_role)
        calc_rows.append({
            'code': code,
            'info': info,
            'target_index': target_index,
            'asset_res': asset_res,
            'original_weight': original_weight,
            'raw_score': raw_score,
            'data_status': data_status,
            'no_timing_role': no_timing_role
        })

    raw_score_sum = sum(row['raw_score'] for row in calc_rows) or 1.0
    rec_data = []
    total_adjusted_dca = 0.0
    for row in calc_rows:
        asset_res = row['asset_res']
        if fixed_budget_mode:
            adjusted_pct = row['raw_score'] / raw_score_sum
            rec_amt = base_dca * adjusted_pct
        else:
            adjusted_pct = row['original_weight'] / 100.0
            rec_amt = base_dca * adjusted_pct * float(asset_res['factor'])
        total_adjusted_dca += rec_amt
        if asset_res.get('hasHistory'):
            valuation_metrics = (
                f"PE {asset_res.get('pe', '--')}（{percentile_text(asset_res.get('pePercentile'))}） / "
                f"PB {asset_res.get('pb', '--')}（{percentile_text(asset_res.get('pbPercentile'))}） / "
                f"股息率百分位 {percentile_text(asset_res.get('dividendYieldPercentile'))}"
            )
        else:
            valuation_metrics = "不适用" if row['no_timing_role'] else "数据缺失"
        rec_data.append({
            '基金代码': row['code'],
            '基金名称': row['info']['name'],
            'Role / Market': f"{row['info'].get('role', '--')} / {row['info'].get('market', '--')}",
            '目标指数': row['target_index'] or '--',
            '数据状态': row['data_status'],
            'PE/PB 及各自百分位': valuation_metrics,
            '估值状态': asset_res['valuationZone'],
            '原始权重': f"{row['original_weight']:.1f}%",
            'Factor': f"{asset_res['factor']:.1f}x",
            '调整后定投占比': f"{adjusted_pct * 100:.1f}%",
            '本期买入金额': f"{rec_amt:.2f} 万"
        })
    mode_note = "预算固定模式：总额未放大，只调整分配。" if fixed_budget_mode else "估值放大/缩小模式：总额会随 factor 变化，仅作主动情景测算。"
    st.markdown(f"基础预算 **{base_dca:.2f} 万元**；调整后总买入 **{total_adjusted_dca:.2f} 万元**。{mode_note}")
    st.dataframe(pd.DataFrame(rec_data), use_container_width=True, hide_index=True)
    if not has_any_valuation_history:
        st.warning("当前 valuation_history.json 暂无任何估值历史，所有 DCA factor 降级为 1.0x。")
    if any(info.get('role', '').startswith('overseas') for info in ASSETS_CONFIG.values()):
        st.info("海外资产估值校准需额外关注汇率、QDII 溢价与跟踪误差风险；无本地估值历史时固定 1.0x。")

# ==========================================
# 模块 5: 年度资产再平衡测算
# ==========================================
elif menu == "5. 年度资产再平衡测算":
    st.markdown("<h1 style='color:#102033; margin-bottom:10px;'>⚖️ 持仓账本与资产再平衡测算</h1>", unsafe_allow_html=True)
    st.write("为了保持资产组合符合预设比例，通常建议于每年底检查持仓并做再平衡测算。")

    st.markdown("### 📝 输入每只配置资产的当期市值 (万元)")
    
    cols_hold = st.columns(4)
    user_holdings = {}
    idx = 0
    # 为了演示方便，提供一组预设的偏离持仓市值
    mock_values = {
        '512890': 9.0,
        '515450': 6.0,  # 偏低
        '513530': 7.5,  # 偏高
        '600941': 5.0,  # 偏高
        '600900': 3.5,  # 偏低
        '601398': 4.5,
        '601088': 5.0,  # 偏高
        '601668': 4.0
    }
    
    for code, info in DEFAULT_ASSETS.items():
        col = cols_ledger[idx % 4]
        with col:
            # 默认填充一个带有偏离的现值用于演示
            default_val = round(invest_principal * (weights[code] / 100.0) * 0.8, 1)
            val = st.number_input(
                f"{info['name']} ({code})",
                min_value=0.0,
                max_value=1000.0,
                value=float(st.session_state.get(f"hold_{code}", default_val)),
                step=1.0,
                key=f"hold_{code}_input"
            )
            st.session_state[f"hold_{code}"] = val
            user_holdings[code] = val
        idx += 1

    total_hold_val = sum(user_holdings.values())
    if total_hold_val <= 0:
        st.warning("请在上方输入实际持仓市值数据以开启再平衡核算。")
    else:
        st.markdown(f"### 📊 年度再平衡提示方案")
        st.write(f"当前投资组合总市值为 **{total_hold_val:.2f}** 万元 (不含外部缓冲池)。")
        incremental_mode = st.checkbox("增量资金再平衡优先", value=True, key="rebalance_incremental_mode_checkbox")
        new_cash = st.number_input("本期可用于再平衡的新增资金 (万元)", min_value=0.0, max_value=1000.0, value=10.0, step=1.0, disabled=not incremental_mode)

        plan_rows = []
        for code, info in ASSETS_CONFIG.items():
            target_pct = weights[code]
            actual_pct = (user_holdings[code] / total_hold_val) * 100.0
            diff_pct = actual_pct - target_pct
            band = float(info.get('rebalance_band', 3))

            ideal_value = total_hold_val * (target_pct / 100.0)
            adjust_value = ideal_value - user_holdings[code] # positive: buy, negative: sell
            plan_rows.append({
                'code': code,
                'info': info,
                'target_pct': target_pct,
                'actual_pct': actual_pct,
                'diff_pct': diff_pct,
                'band': band,
                'ideal_value': ideal_value,
                'adjust_value': adjust_value,
                'is_over_band': abs(diff_pct) > band,
                'incremental_buy': 0.0
            })
            
        rebalance_df = pd.DataFrame(rebalance_rows)
        st.table(rebalance_df)
        
        st.info("💡 **小贴士**：再平衡不仅可以通过卖出昂贵资产买入便宜资产来实现，如果您后续有新增本金，也可以通过**‘增量资金再平衡’**的方式——即将新申购的资金全部用于买入当前低于目标比例的标的，从而省去卖出资产的摩擦成本和潜在税费。")

# ==========================================
# 模块 5: 目标导向规划 (核心)
# ==========================================
elif menu == "5. 目标导向规划 (核心)":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>🎯 目标导向规划与多维推演工作台</h1>", unsafe_allow_html=True)
    st.write("基于家庭可用总本金与月可结余，按看板预期收益率进行复利终值推演。当目标存在缺口时，自动反解**三大可调杠杆**（储蓄端/收益端/目标端），并针对提前退休目标展开85岁全周期持久性检验。")
    
    # 初始化 session_state 中的目标数据
    if 'goals' not in st.session_state:
        st.session_state.goals = [
            {
                'id': 'goal-1',
                'name': '2035 年子女教育金',
                'type': '子女教育金',
                'amount': 1000000.0,
                'year': 2035,
                'priority': '刚性',
                'reserved': 0.0,
                'link_bucket': False,
                'retire_age': 50,
                'retire_monthly_expense': 10000.0
            },
            {
                'id': 'goal-2',
                'name': '2040 提前退休储备',
                'type': '提前退休',
                'amount': 2500000.0,
                'year': 2040,
                'priority': '弹性',
                'reserved': 150000.0,
                'link_bucket': True,
                'retire_age': 50,
                'retire_monthly_expense': 12000.0
            }
        ]
        
    # 看板股息率计算
    weights_map = {code: info['weight']/100 for code, info in DEFAULT_ASSETS.items()}
    yields_map = {code: info['yield']/100 for code, info in DEFAULT_ASSETS.items()}
    blended_div_yield = sum(weights_map[c] * yields_map[c] for c in DEFAULT_ASSETS.keys())
    
    current_principal_yuan = principal * 10000.0
    
    # 顶部指标卡
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>规划目标总数</div>
            <div class='metric-value' style='color:#38BDF8;'>{len(st.session_state.goals)} 个</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>月度可结余 (体检输入)</div>
            <div class='metric-value'>¥{monthly_surplus:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>增长预期年化收益率</div>
            <div class='metric-value' style='color:#10B981;'>{growth_rate_pct:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        tot_target_amt = sum(g['amount'] for g in st.session_state.goals)
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>目标资金总需求</div>
            <div class='metric-value'>¥{tot_target_amt/10000:.0f} 万元</div>
        </div>
        """, unsafe_allow_html=True)

    # 快捷操作栏
    st.markdown("### 🛠️ 目标操作面板")
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("⚡ 一键载入验收示例 (2035 年子女教育金 100 万)"):
            new_id = f"goal-{len(st.session_state.goals)+1}"
            st.session_state.goals.insert(0, {
                'id': new_id,
                'name': '2035 年子女教育金 (验收用例)',
                'type': '子女教育金',
                'amount': 1000000.0,
                'year': 2035,
                'priority': '刚性',
                'reserved': 0.0,
                'link_bucket': False,
                'retire_age': 50,
                'retire_monthly_expense': 10000.0
            })
            st.success("已成功添加验收示例目标！")
            st.rerun()

    # 新增目标折叠窗
    with st.expander("➕ 添加新财务规划目标", expanded=False):
        with st.form("add_goal_form"):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                g_name = st.text_input("目标名称", value="子女高等教育金")
                g_type = st.selectbox("目标类型", ["子女教育金", "养老储备", "买房首付", "提前退休", "自定义"])
                g_priority = st.selectbox("优先级", ["刚性", "弹性"])
            with f_col2:
                g_amount = st.number_input("目标金额 (元)", min_value=10000.0, max_value=100000000.0, value=1000000.0, step=50000.0)
                g_year = st.number_input("目标时点 (年份)", min_value=2026, max_value=2070, value=2035, step=1)
                g_link = st.checkbox("一键关联“未来1-3年确定要用的钱”(自动同步体检数据)", value=False)
                g_reserved = st.number_input("已单独预留金额 (元)", min_value=0.0, max_value=10000000.0, value=bucket_1_3y if g_link else 0.0, step=10000.0)
                
            g_retire_age = 50
            g_retire_exp = 10000.0
            if g_type == "提前退休":
                st.markdown("##### 🌴 提前退休生命周期检验参数")
                r_c1, r_c2 = st.columns(2)
                with r_c1:
                    g_retire_age = st.number_input("计划退休年龄", min_value=40, max_value=75, value=50, step=1)
                with r_c2:
                    g_retire_exp = st.number_input("退休后期望月生活费 (元)", min_value=2000.0, max_value=200000.0, value=10000.0, step=1000.0)
                    
            submitted = st.form_submit_button("确认创建目标")
            if submitted:
                st.session_state.goals.append({
                    'id': f"goal-{len(st.session_state.goals)+1}",
                    'name': g_name,
                    'type': g_type,
                    'amount': g_amount,
                    'year': int(g_year),
                    'priority': g_priority,
                    'reserved': bucket_1_3y if g_link else g_reserved,
                    'link_bucket': g_link,
                    'retire_age': int(g_retire_age),
                    'retire_monthly_expense': g_retire_exp
                })
                st.success(f"目标【{g_name}】创建成功！")
                st.rerun()

    # 目标列表与测算结果
    st.markdown("### 📋 目标推演与达成杠杆分析")
    
    if len(st.session_state.goals) == 0:
        st.info("当前暂无规划目标，请点击上方按钮新增目标。")
    else:
        for idx, g in enumerate(st.session_state.goals):
            res_amt = bucket_1_3y if g.get('link_bucket', False) else g.get('reserved', 0.0)
            proj = calculate_goal_projection_py(
                target_year=g['year'],
                target_amount=g['amount'],
                monthly_surplus_val=monthly_surplus,
                growth_rate_val=growth_rate,
                current_principal_val=current_principal_yuan,
                reserved_amount_val=res_amt
            )
            
            with st.container():
                st.markdown(f"""
                <div class='card' style='border-left: 5px solid {"#10B981" if proj["is_achieved"] else "#EF4444"};'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <span style='font-size:1.25rem; font-weight:700; color:#FFFFFF;'>{g['name']}</span>
                            <span style='margin-left:10px; background:rgba(255,255,255,0.1); padding:2px 8px; border-radius:4px; font-size:0.8rem;'>{g['type']}</span>
                            <span style='margin-left:6px; background:{"rgba(239,68,68,0.2)" if g["priority"]=="刚性" else "rgba(56,189,248,0.2)"}; color:{"#F87171" if g["priority"]=="刚性" else "#38BDF8"}; padding:2px 8px; border-radius:4px; font-size:0.8rem;'>{g['priority']}优先级</span>
                            {f"<span style='margin-left:6px; color:#38BDF8; font-size:0.75rem;'>🔗 已关联1-3年确定性资金 (¥{bucket_1_3y:,.0f})</span>" if g.get('link_bucket') else ""}
                        </div>
                        <div style='font-size:1.1rem; font-weight:700; color:{"#10B981" if proj["is_achieved"] else "#EF4444"};'>
                            {"🟢 预计富余 +¥" + f"{proj['diff']:,.0f}" if proj['is_achieved'] else "🔴 预计缺口 -¥" + f"{proj['gap']:,.0f}"}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 指标 4 栏
                col_g1, col_g2, col_g3, col_g4 = st.columns(4)
                with col_g1:
                    st.metric("目标金额", f"¥{g['amount']:,.0f}", f"目标时点: {g['year']}年 (还剩{proj['years']}年)")
                with col_g2:
                    st.metric("简化推演终值", f"¥{proj['fv_total']:,.0f}", f"达成率: {proj['fv_total']/g['amount']*100:.1f}%")
                with col_g3:
                    st.metric("月结余定投贡献", f"¥{proj['fv_monthly']:,.0f}", f"¥{monthly_surplus:,.0f}/月 × {proj['months']}期")
                with col_g4:
                    st.metric("本金复利贡献", f"¥{proj['fv_principal']:,.0f}", f"含单独预留: ¥{proj['fv_reserved']:,.0f}")
                    
                # 缺口场景反解三大杠杆
                if not proj['is_achieved'] and proj['levers']:
                    lev = proj['levers']
                    st.markdown(f"""
                    <div style='background:rgba(239, 68, 68, 0.08); border:1px solid rgba(239, 68, 68, 0.3); border-radius:8px; padding:15px; margin-top:10px; margin-bottom:15px;'>
                        <h5 style='color:#FCA5A5; margin-top:0;'>⚠️ 目标存在缺口 ¥{proj['gap']:,.0f} 元，系统反解三大可调杠杆：</h5>
                        <div style='display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size:0.9rem;'>
                            <div style='background:rgba(0,0,0,0.25); padding:10px; border-radius:6px;'>
                                <div style='color:#94A3B8; font-size:0.8rem;'>杠杆 1：储蓄端</div>
                                <div style='color:#38BDF8; font-weight:700; font-size:1.1rem;'>每月需多储蓄 +¥{lev['extra_monthly']:,} 元</div>
                                <div style='color:#CBD5E1; font-size:0.75rem; margin-top:4px;'>需将月结余增至 ¥{(monthly_surplus + lev['extra_monthly']):, } 元</div>
                            </div>
                            <div style='background:rgba(0,0,0,0.25); padding:10px; border-radius:6px;'>
                                <div style='color:#94A3B8; font-size:0.8rem;'>杠杆 2：收益端</div>
                                <div style='color:#FFF; font-weight:700; font-size:1.1rem;'>需提升 {lev['rate_diff_pct']:.2f}% 至 {lev['req_rate_pct']:.2f}%</div>
                                <div style='color:{"#34D399" if lev["is_rate_safe"] else "#F87171"}; font-size:0.75rem; margin-top:4px;'>
                                    {"🟢 处于家庭稳健区间 (≤8.0%)" if lev["is_rate_safe"] else "⚠️ 超出稳健上限 (8.0%)，存在本金大幅波动风险"}
                                </div>
                            </div>
                            <div style='background:rgba(0,0,0,0.25); padding:10px; border-radius:6px;'>
                                <div style='color:#94A3B8; font-size:0.8rem;'>杠杆 3：目标端</div>
                                <div style='color:#FBBF24; font-weight:700; font-size:1.1rem;'>放宽或延后 {lev['delay_years']} 年</div>
                                <div style='color:#CBD5E1; font-size:0.75rem; margin-top:4px;'>金额下调至 ¥{(g['amount'] - lev['loosen_amount']):,.0f} 或延至 {lev['delayed_target_year']} 年</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                # 提前退休专属持久性检验
                if g['type'] == '提前退休':
                    ret_sim = simulate_early_retirement_py(
                        retire_age=g.get('retire_age', 50),
                        target_amount=g['amount'],
                        projected_capital_at_retire=proj['fv_total'],
                        monthly_expense_val=g.get('retire_monthly_expense', 10000.0),
                        dividend_yield_val=blended_div_yield,
                        buffer_rate_val=money_market_rate,
                        end_age=85
                    )
                    st.markdown(f"""
                    <div style='background:rgba(30, 41, 59, 0.7); border:1px solid rgba(56, 189, 248, 0.3); border-radius:8px; padding:15px; margin-top:8px;'>
                        <h5 style='color:#38BDF8; margin-top:0;'>🌴 提前退休模式：85 岁全生命周期持久性检验</h5>
                        <div style='display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;'>
                            <div>
                                <span style='color:#94A3B8; font-size:0.8rem;'>退休期初推演资本</span>
                                <div style='font-size:1.1rem; font-weight:700; color:#FFF;'>¥{proj['fv_total']:,.0f} 元</div>
                                <div style='font-size:0.75rem; color:#94A3B8;'>月生活费: ¥{g.get('retire_monthly_expense', 10000.0):,.0f}</div>
                            </div>
                            <div>
                                <span style='color:#94A3B8; font-size:0.8rem;'>最脆弱月份 (资金最低谷)</span>
                                <div style='font-size:1.1rem; font-weight:700; color:{"#38BDF8" if ret_sim["lowest_capital"]>0 else "#EF4444"};'>
                                    第 {ret_sim['mostFragileMonth']} 个月 (约 {ret_sim['mostFragileAge']} 岁)
                                </div>
                                <div style='font-size:0.75rem; color:#94A3B8;'>该期最低水位: ¥{ret_sim['lowest_capital']:,.0f}</div>
                            </div>
                            <div>
                                <span style='color:#94A3B8; font-size:0.8rem;'>85 岁最终财务评估</span>
                                <div style='font-size:1.1rem; font-weight:700; color:{"#10B981" if ret_sim["is_sustainable"] else "#EF4444"};'>
                                    {"✅ 资本永续安全" if ret_sim["is_sustainable"] else f"⚠️ {ret_sim['depletion_age']} 岁耗尽"}
                                </div>
                                <div style='font-size:0.75rem; color:#94A3B8;'>
                                    {f"85岁预计剩余遗产: ¥{ret_sim['final_capital']:,.0f}" if ret_sim["is_sustainable"] else f"于退休后第 {ret_sim['depletion_month']} 个月耗尽"}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # 删除单条目标
                if st.button(f"🗑️ 删除目标「{g['name']}」", key=f"del_{g['id']}"):
                    st.session_state.goals.pop(idx)
                    st.success(f"已删除目标【{g['name']}】！")
                    st.rerun()

                st.markdown("---")

    st.markdown("""
    <div style='margin-top:30px; padding:12px 18px; border-radius:8px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); font-size:0.8rem; color:#94A3B8;'>
        🛡️ <strong>免责声明</strong>：所有财务推演与测算模型均基于用户输入的数据及假设性年化收益率，不代表任何历史业绩或未来投资收益承诺。市场有风险，投资决策需审慎。
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 模块 6: Markdown 体检报告导出
# ==========================================
elif menu == "6. Markdown 体检报告导出":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>📋 家庭财富规划体检报告 (Markdown 导出)</h1>", unsafe_allow_html=True)
    st.write("系统已整合您的资产配置、现金流看板、缓冲池安全诊断，以及最新的**「目标达成总览」**表格，自动编译为专业 Markdown 体检报告。")

    # 计算全局指标
    weights_map = {code: info['weight']/100 for code, info in DEFAULT_ASSETS.items()}
    yields_map = {code: info['yield']/100 for code, info in DEFAULT_ASSETS.items()}
    blended_div_yield = sum(weights_map[c] * yields_map[c] for c in DEFAULT_ASSETS.keys())
    exp_ann_div = invest_principal * blended_div_yield * 10000.0
    exp_m_avg = exp_ann_div / 12.0
    
    # 编译目标总览表格
    goal_table_rows = []
    goals_list = st.session_state.get('goals', [])
    for idx, g in enumerate(goals_list):
        res_amt = bucket_1_3y if g.get('link_bucket', False) else g.get('reserved', 0.0)
        proj = calculate_goal_projection_py(
            target_year=g['year'],
            target_amount=g['amount'],
            monthly_surplus_val=monthly_surplus,
            growth_rate_val=growth_rate,
            current_principal_val=principal * 10000.0,
            reserved_amount_val=res_amt
        )
        status_txt = f"🟢 预计富余 ¥{proj['diff']:,.0f}" if proj['is_achieved'] else f"🔴 预计缺口 ¥{proj['gap']:,.0f}"
        if proj['is_achieved'] or not proj['levers']:
            lever_txt = "已达成，无需调控"
        else:
            lev = proj['levers']
            r_safe = "稳健区间内" if lev['is_rate_safe'] else "⚠️超稳健上限8%"
            lever_txt = f"①每月多储 ¥{lev['extra_monthly']:,} <br>②收益率提至 {lev['req_rate_pct']}% (+{lev['rate_diff_pct']}%, {r_safe}) <br>③降目标至 ¥{(g['amount']-lev['loosen_amount']):,.0f} 或延至 {lev['delayed_target_year']}年 (+{lev['delay_years']}年)"
            
        goal_table_rows.append(f"| {idx+1} | {g['name']} | {g['type']} | {g['priority']} | {g['year']}年 | ¥{g['amount']:,.0f} | ¥{proj['fv_total']:,.0f} | {status_txt} | {lever_txt} |")

    goal_table_str = "\n".join(goal_table_rows) if goal_table_rows else "| 暂无目标 | - | - | - | - | - | - | - | - |"

    # 债务决策测算
    debt_res = calculate_debt_decision_metrics_py(
        debt_bracket_val=debt_bracket,
        custom_debt_rate_val=custom_debt_rate,
        high_interest_balance_val=high_interest_balance,
        growth_rate_pct_val=growth_rate_pct,
        available_fund_x_val=available_fund_x
    )

    high_debt_alert_md = ""
    if debt_res['has_high_interest_alert']:
        high_debt_alert_md = f"""> [!CAUTION]
> **🚨 【高息债务警报】**：检测到家庭当前存在年化 >6.0% 的高息借贷或自报高息债务余额 ¥{high_interest_balance:,.0f} 元！高息借贷利息损耗极大，严重侵蚀净资产积累，建议将其列为优先偿还关注事项。

---
"""

    debt_table_rows = []
    for row in debt_res['table']:
        diff_str = f"+¥{row['diff']:,.2f}" if row['diff'] > 0 else f"-¥{abs(row['diff']):,.2f}"
        debt_table_rows.append(f"| {row['years']} 年期 | ¥{row['fund_x']:,.0f} | ¥{row['fv_repay']:,.0f} | ¥{row['fv_invest']:,.0f} | {diff_str} | **{row['advantage']}** |")
    debt_table_str = "\n".join(debt_table_rows)

    total_debt_val = mortgage_balance + car_loan_balance + consumer_loan_balance + business_loan_balance

    md_content = f"""# 📋 家庭财富规划与目标达成综合体检报告

**生成时间**：2026年9月20日  
**规划模型**：红利低波现金流配置 + 缓冲池平滑 + 目标导向多维推演 + 债务决策对照

---

{high_debt_alert_md}## 一、 家庭收支与资产体检总览
- **家庭月总收入**：¥{monthly_income:,.0f} 元
- **家庭月常规支出**：¥{monthly_expense:,.0f} 元
- **月度可支配净结余**：**¥{monthly_surplus:,.0f} 元**（储蓄率：{(monthly_surplus/monthly_income*100):.1f}%）
- **未来1-3年确定要用的钱**：¥{bucket_1_3y:,.0f} 元（已作为目标预留联动备用）

### 债务结构与「债务决策对照」
- **家庭负债总额**：¥{total_debt_val:,.0f} 元（房贷: ¥{mortgage_balance:,.0f}, 车贷: ¥{car_loan_balance:,.0f}, 消费贷: ¥{consumer_loan_balance:,.0f}, 经营贷: ¥{business_loan_balance:,.0f}）
- **每月贷款总还款**：¥{monthly_debt_payment:,.0f} 元
- **综合贷款利率档位**：**{debt_res['debt_bracket']}** (测算利率: **{debt_res['effective_debt_rate']:.2f}%**，按档位中值估算，请以实际合同利率为准)
- **组合保守预期收益率**：**{debt_res['conservative_yield']:.2f}%** (取增长预期年化收益率 {growth_rate_pct:.2f}% 的 70% 作为保守口径)
- **决策矩阵研判结论**：**{debt_res['decision_text']}**

#### 路径模拟对比（可用资金 X = ¥{debt_res['fund_x']:,.0f} 元，提前还贷 vs 组合投资）
| 模拟周期 | 模拟资金本金 | 路径A: 提前还贷终值效应 | 路径B: 坚持投资推演终值 | 净资产差额 (A - B) | 策略对比建议 |
| :--- | :--- | :--- | :--- | :--- | :--- |
{debt_table_str}

*注：按档位中值估算，请以实际合同利率为准。文案旨在提供量化工具对照参考，不构成强制性提前还款建议。*

---

## 二、 资产配置与股息测算看板
- **投资可用总本金**：¥{principal*10000:,.0f} 元（含缓冲池种子金 ¥{buffer_seed*10000:,.0f} 元）
- **实际红利资产配置本金**：¥{invest_principal*10000:,.0f} 元
- **加权税后现金流收益率**：**{blended_div_yield*100:.2f}%**
- **长期增长预期年化收益率**：**{growth_rate_pct:.2f}%**
- **预期年税后分红总额**：¥{exp_ann_div:,.0f} 元
- **折合月均被动现金流**：**¥{exp_m_avg:,.0f} 元**
- **目标月生活费要求**：¥{target_monthly*10000:,.0f} 元

---

## 三、 🎯 目标达成总览明细表

| 序号 | 目标名称 | 目标类型 | 优先级 | 目标年份 | 目标金额 | 简化推演终值 | 达成状态 | 缺口调控对策 (三大可调杠杆) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
{goal_table_str}

---

## 四、 规划工程师专业建议
1. **刚性目标必须闭环**：标记为刚性的目标建议优先使用【杠杆1：每月多储蓄】进行填补；
2. **严防超额收益幻想**：若反解所需收益率超过 **8.0%**，必须警惕超额市场风险，切勿盲目以高风险资产博取达标；
3. **提前退休支取安全**：退休后应维持缓冲池防御机制，确保淡旺季平滑过渡，防范老年期本金过早耗尽；
4. **债务与投资权衡审慎**：综合贷款利率高于保守投资收益率时提前还贷确定性更优，反之利差为正时可保持贷款但须严控流动性安全边界。

---

> [!NOTE]
> **免责声明**：所有推演基于用户输入与假设收益率，按档位中值估算，请以实际合同利率为准，不构成收益承诺。市场有风险，投资需谨慎。
"""

    st.download_button(
        label="📥 下载完整 Markdown 报告 (.md)",
        data=md_content,
        file_name="家庭财富规划体检报告_2026.md",
        mime="text/markdown"
    )

    st.markdown("### 📝 报告在线实时预览")
    st.markdown(md_content)

# ==========================================
# 模块 7: 债务决策对照 (还贷vs投资)
# ==========================================
elif menu == "7. 债务决策对照 (还贷vs投资)":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>⚖️ 债务决策对照：提前还贷 vs 组合投资路径模拟</h1>", unsafe_allow_html=True)
    st.caption("按档位中值估算，请以实际合同利率为准。基于客观利差量化测算，协助家庭理性权衡提前还贷与坚持投资。")

    debt_res = calculate_debt_decision_metrics_py(
        debt_bracket_val=debt_bracket,
        custom_debt_rate_val=custom_debt_rate,
        high_interest_balance_val=high_interest_balance,
        growth_rate_pct_val=growth_rate_pct,
        available_fund_x_val=available_fund_x
    )

    # 1. 置顶高息债务警报卡片
    if debt_res['has_high_interest_alert']:
        st.markdown(f"""
        <div style='background:rgba(239,68,68,0.15); border:2px solid #EF4444; border-radius:12px; padding:18px 22px; margin-bottom:24px;'>
            <div style='color:#F87171; font-weight:700; font-size:1.1rem; margin-bottom:6px;'>
                🚨 【置顶健康警报】检测到家庭存在高息债务风险！
            </div>
            <div style='color:#FECACA; font-size:0.9rem; line-height:1.6;'>
                当前自报高息债务余额 <strong>¥{high_interest_balance:,.0f} 元</strong>，或综合贷款利率处于 <strong>&gt;6.0%</strong> 档位（当前测算利率 {debt_res['effective_debt_rate']:.2f}%）。高息借贷利息支出具有极高刚性损耗，严重侵蚀家庭净资产，建议将其列为最高优先级偿还与化解事项！
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. 利率与预期收益对比指标卡
    m_col1, m_col2, m_col3 = st.columns(3)
    rate_diff = debt_res['effective_debt_rate'] - debt_res['conservative_yield']
    with m_col1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>当前综合贷款利率 (档位中值)</div>
            <div class='metric-value' style='color:#FBBF24;'>{debt_res['effective_debt_rate']:.2f}%</div>
            <div style='color:#94A3B8; font-size:0.75rem; margin-top:4px;'>当前档位: {debt_res['debt_bracket']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>组合加权预期收益率 (保守口径)</div>
            <div class='metric-value' style='color:#10B981;'>{debt_res['conservative_yield']:.2f}%</div>
            <div style='color:#94A3B8; font-size:0.75rem; margin-top:4px;'>取看板增长预期 {growth_rate_pct:.1f}% 的 70% 作为保守口径</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        diff_color = "#FB7185" if rate_diff > 0 else "#34D399"
        diff_sign = "+" if rate_diff >= 0 else ""
        diff_label = "负利差 (贷款成本高于保守收益)" if rate_diff > 0 else "正利差 (投资回报高于贷款成本)"
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>利差对比 (贷款利率 − 保守收益率)</div>
            <div class='metric-value' style='color:{diff_color};'>{diff_sign}{rate_diff:.2f}%</div>
            <div style='color:#94A3B8; font-size:0.75rem; margin-top:4px;'>{diff_label}</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. 决策矩阵文案提示框 (中立、量化)
    matrix_bg = 'rgba(239,68,68,0.12)' if debt_res['decision_type'] == 'repay_first' else ('rgba(16,185,129,0.12)' if debt_res['decision_type'] == 'invest_first' else 'rgba(56,189,248,0.12)')
    matrix_border = '#EF4444' if debt_res['decision_type'] == 'repay_first' else ('#10B981' if debt_res['decision_type'] == 'invest_first' else '#38BDF8')
    matrix_color = '#F87171' if debt_res['decision_type'] == 'repay_first' else ('#34D399' if debt_res['decision_type'] == 'invest_first' else '#38BDF8')
    
    desc_analysis = ""
    if debt_res['decision_type'] == 'repay_first':
        desc_analysis = "分析提示：当综合贷款利率高出投资保守预期 2 个百分点以上时，提前清偿债务能产生确定的无风险节息回报，优于承担本金波动风险的投资。"
    elif debt_res['decision_type'] == 'invest_first':
        desc_analysis = "分析提示：当综合贷款利率低出投资保守预期 2 个百分点以上时，低息债务具备正向财务杠杆价值，但投资前请确认现金流稳定性与应急备用金充足度。"
    else:
        desc_analysis = "分析提示：贷款成本与组合保守回报利差处于 ±2% 的中间平衡区间，两者从纯数学推演差异有限，决策核心在于您对负债的心理耐受度、职业收入确定性及流动性需求。"

    st.markdown(f"""
    <div style='background:{matrix_bg}; border:1px solid {matrix_border}; border-radius:10px; padding:18px; margin:20px 0;'>
        <div style='font-size:1.05rem; font-weight:700; color:#FFF; margin-bottom:8px;'>
            💡 决策矩阵研判结论：<span style='color:{matrix_color};'>{debt_res['decision_text']}</span>
        </div>
        <div style='font-size:0.85rem; color:#CBD5E1; line-height:1.6;'>
            {desc_analysis}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 路径模拟对比 (可用资金 X 在 3/5/10 年的净资产差额对比表)
    st.markdown("### 📊 可用资金 X 路径模拟推演 (3年 / 5年 / 10年)")
    st.write(f"当前模拟可用资金 **¥{debt_res['fund_x']:,.0f} 元**（可在左侧侧边栏微调输入）。")

    comp_df = pd.DataFrame([
        {
            '模拟周期': f"{r['years']} 年期",
            '投入本金': f"¥{r['fund_x']:,.0f}",
            '路径A: 提前还贷累计效应 (终值)': f"¥{r['fv_repay']:,.0f}",
            '路径B: 坚持投资推演终值': f"¥{r['fv_invest']:,.0f}",
            '净资产差额 (A − B)': f"{'+' if r['diff']>0 else ''}¥{r['diff']:,.0f}",
            '策略对比建议': r['advantage']
        }
        for r in debt_res['table']
    ])
    st.table(comp_df)

    st.markdown("""
    <div style='margin-top:20px; padding:12px 18px; border-radius:8px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); font-size:0.8rem; color:#94A3B8;'>
        ⚖️ <strong>提示与说明</strong>：测算基于“按档位中值估算，请以实际合同利率为准”原则。两路径模型公式分别为：提前还贷 $X \\times (1 + r_{\\text{debt}})^T$ vs 投资 $X \\times (1 + r_{\\text{invest}})^T$。建议文案保持中立与工具化，辅助自主财务决策。
    </div>
    """, unsafe_allow_html=True)



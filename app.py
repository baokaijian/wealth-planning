import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os
import json
import random
from datetime import datetime

# 导入计算引擎
import portfolio_engine

# ==========================================
# 页面基本配置与现代暗黑主题 CSS 注入
# ==========================================
st.set_page_config(
    page_title="家庭资产体检与均衡配置中心",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS 以强化视觉美感（玻璃幕墙与暗黑科技风）
st.markdown("""
<style>
    /* 全局背景色与字体 */
    .stApp {
        background-color: #0E1117;
        color: #E2E8F0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #1A1F2C !important;
        border-right: 1px solid #2D3748;
    }
    
    /* 玻璃幕墙卡片效果 */
    .card {
        background: rgba(26, 31, 44, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #10B981;
        margin-bottom: 12px;
        border-left: 4px solid #10B981;
        padding-left: 8px;
    }
    
    /* 突出数值面板 */
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.2;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* 数据表美化 */
    div[data-testid="stTable"] table {
        background-color: #1A1F2C !important;
        color: #E2E8F0 !important;
        border-radius: 8px;
        border-collapse: collapse;
        width: 100%;
    }
    
    /* 调整输入框背景 */
    input, select, textarea {
        background-color: #2D3748 !important;
        color: #FFFFFF !important;
        border: 1px solid #4A5568 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 数据加载与价格反算
# ==========================================
script_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(script_dir, 'assets.json')
live_data_path = os.path.join(script_dir, 'live_data.json')

# 加载 assets.json 动态配置
try:
    with open(assets_path, 'r', encoding='utf-8') as f:
        assets_list = json.load(f)
except Exception as e:
    assets_list = []

# 加载实时价格 live_data.json 动态配置
live_data = {}
if os.path.exists(live_data_path):
    try:
        with open(live_data_path, 'r', encoding='utf-8') as f:
            live_payload = json.load(f)
            if live_payload.get('status') == 'success':
                live_data = live_payload.get('data', {})
    except Exception as e:
        pass

# 组装完整的资产配置参数
ASSETS_CONFIG = {}
if assets_list:
    for item in assets_list:
        code = item['code']
        months_int = {int(k): v for k, v in item['distribution_months'].items()}
        # 读取实时数据
        live_info = live_data.get(code, {})
        price = live_info.get('price', 0.0)
        dy = live_info.get('yield', item['estimated_yield'])
        
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
            'months': months_int,
            'strategy_note': item.get('strategy_note', ''),
            'risk_note': item.get('risk_note', '')
        }
else:
    # 备用硬编码以防万一
    fallback_raw = [
        {"code": "511880", "name": "银华日利货币 ETF", "type": "ETF", "role": "cash", "market": "CN", "volatility_level": "low", "income_type": "cash_interest", "weight": 5.0, "estimated_yield": 1.8, "estimated_return": 1.8, "distribution_months": {"1":0.083, "2":0.083, "3":0.083, "4":0.083, "5":0.083, "6":0.083, "7":0.083, "8":0.083, "9":0.083, "10":0.083, "11":0.083, "12":0.083}, "strategy_note": "场内高流动性货币基金，等同现金，平滑日常支取", "risk_note": "收益率随市场降息下行风险"},
        {"code": "512890", "name": "中证红利低波 ETF", "type": "ETF", "role": "dividend_income", "market": "CN", "volatility_level": "medium", "income_type": "dividend", "weight": 20.0, "estimated_yield": 4.5, "estimated_return": 7.0, "distribution_months": {"7":0.5, "12":0.5}, "strategy_note": "精选高股息低波红利股，适合核心现金流防御", "risk_note": "A股市场波动风险及分红不及预期风险"},
        {"code": "515450", "name": "标普大盘红利低波 ETF", "type": "ETF", "role": "dividend_income", "market": "CN", "volatility_level": "medium", "income_type": "dividend", "weight": 10.0, "estimated_yield": 4.2, "estimated_return": 6.8, "distribution_months": {"7":1.0}, "strategy_note": "标普红利低波筛选，大盘蓝筹红利代表", "risk_note": "红利税变动及标的股分红变动风险"},
        {"code": "510880", "name": "华泰柏瑞红利 ETF", "type": "ETF", "role": "dividend_income", "market": "CN", "volatility_level": "medium", "income_type": "dividend", "weight": 10.0, "estimated_yield": 4.0, "estimated_return": 6.5, "distribution_months": {"12":1.0}, "strategy_note": "上证红利老牌ETF，周期红利代表", "risk_note": "行业集中度偏高，钢铁煤炭等周期股占比波动"},
        {"code": "513530", "name": "恒生红利低波 ETF", "type": "ETF", "role": "dividend_income", "market": "HK", "volatility_level": "high", "income_type": "dividend", "weight": 10.0, "estimated_yield": 4.8, "estimated_return": 7.5, "distribution_months": {"7":0.5, "12":0.5}, "strategy_note": "获取港股低估值红利，离岸派息配置", "risk_note": "港股通红利税（20%）扣减及汇率波动风险"},
        {"code": "510300", "name": "华泰柏瑞沪深300 ETF", "type": "ETF", "role": "domestic_beta", "market": "CN", "volatility_level": "medium", "income_type": "capital_growth", "weight": 15.0, "estimated_yield": 1.5, "estimated_return": 8.0, "distribution_months": {"10":1.0}, "strategy_note": "获取中国经济长期核心Beta增值", "risk_note": "国内宏观经济系统性下行风险"},
        {"code": "588000", "name": "华夏科创50 ETF", "type": "ETF", "role": "tech_growth", "market": "CN", "volatility_level": "high", "income_type": "capital_growth", "weight": 10.0, "estimated_yield": 0.2, "estimated_return": 10.0, "distribution_months": {"12":1.0}, "strategy_note": "聚焦国内硬科技成长标的，获取弹性成长溢价", "risk_note": "科技股高估值回撤及高波动风险"},
        {"code": "513100", "name": "易方达纳斯达克100 ETF", "type": "ETF", "role": "overseas_tech", "target_index_code": "NDX", "market": "US", "volatility_level": "high", "income_type": "capital_growth", "rebalance_band": 5, "weight": 10.0, "estimated_yield": 0.5, "estimated_return": 9.5, "distribution_months": {"12":1.0}, "strategy_note": "海外科技成长资产，不等同海外宽基", "risk_note": "海外估值高位回撤及汇率波动风险"},
        {"code": "518880", "name": "华安黄金 ETF", "type": "ETF", "role": "hedge", "market": "Global", "volatility_level": "medium", "income_type": "hedge", "weight": 5.0, "estimated_yield": 0.0, "estimated_return": 4.5, "distribution_months": {}, "strategy_note": "避险商品，对抗通胀及地缘极端危机", "risk_note": "黄金无利息且金价高位价格波动风险"},
        {"code": "511360", "name": "中债信用债 ETF", "type": "ETF", "role": "hedge", "market": "CN", "volatility_level": "low", "income_type": "cash_interest", "weight": 5.0, "estimated_yield": 2.5, "estimated_return": 3.5, "distribution_months": {"6":0.5, "12":0.5}, "strategy_note": "低波动债基，提供平稳票息收入和防御防线", "risk_note": "信用利差走阔及市场降息波动风险"}
    ]
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
st.sidebar.markdown("<h2 style='color:#10B981;text-align:center;margin-bottom:20px;'>💰 策略控制台</h2>", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "功能模块导航",
    [
        "1. 家庭资产体检与配置建议",
        "2. 资产配置与股息测算看板",
        "3. 现金缓冲池平滑模拟器",
        "4. 估值温度计与测算工具",
        "5. 年度资产再平衡测算",
        "6. 风险压力测试",
        "7. 人生财富游戏"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 基本配置参数")

# 在 session_state 中初始化基本参数以保证全局一致性
if 'principal' not in st.session_state:
    st.session_state.principal = 400.0
if 'target_monthly' not in st.session_state:
    st.session_state.target_monthly = 2.0
if 'buffer_seed' not in st.session_state:
    st.session_state.buffer_seed = 12.0
if 'money_market_rate' not in st.session_state:
    st.session_state.money_market_rate = 2.0

principal = st.sidebar.number_input("您的可用总本金 (万元)", min_value=10.0, max_value=5000.0, value=st.session_state.principal, step=10.0)
st.session_state.principal = principal

target_monthly = st.sidebar.number_input("期望月现金流 (万元)", min_value=0.1, max_value=50.0, value=st.session_state.target_monthly, step=0.5)
st.session_state.target_monthly = target_monthly

buffer_seed = st.sidebar.number_input("现金缓冲池初始资金 (万元)", min_value=0.0, max_value=100.0, value=st.session_state.buffer_seed, step=1.0)
st.session_state.buffer_seed = buffer_seed

money_market_rate = st.sidebar.slider("缓冲池闲置资金年化收益 (%)", min_value=0.5, max_value=5.0, value=st.session_state.money_market_rate, step=0.1)
st.session_state.money_market_rate = money_market_rate

invest_principal = max(principal - buffer_seed, 0.0)

# ==========================================
# 初始化家庭问卷的默认数据
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
        'f-monthly-income': 30000.0,
        'f-fixed-expense': 12000.0,
        'f-surplus-income': 18000.0,
        'f-income-sources': 2,
        'f-salary-ratio': 80.0,
        'f-bonus-ratio': 20.0,
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

# ==========================================
# 策略预设联动逻辑
# ==========================================
PRESETS = {
    "🛡️ 保守型现金流策略": {
        '511880': 15.0,
        '512890': 30.0,
        '515450': 15.0,
        '510880': 10.0,
        '513530': 10.0,
        '510300': 5.0,
        '588000': 0.0,
        '513100': 0.0,
        '518880': 5.0,
        '511360': 10.0
    },
    "⚖️ 均衡型增长配置": {
        '511880': 5.0,
        '512890': 20.0,
        '515450': 10.0,
        '510880': 10.0,
        '513530': 10.0,
        '510300': 15.0,
        '588000': 10.0,
        '513100': 10.0,
        '518880': 5.0,
        '511360': 5.0
    },
    "🚀 积极型成长突破": {
        '511880': 0.0,
        '512890': 10.0,
        '515450': 5.0,
        '510880': 5.0,
        '513530': 5.0,
        '510300': 20.0,
        '588000': 20.0,
        '513100': 20.0,
        '518880': 10.0,
        '511360': 5.0
    }
}

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

# 策略预设选择器
preset_option = st.sidebar.selectbox(
    "配置策略预设",
    ["✍️ 自定义权重配置", "🛡️ 保守型现金流策略", "⚖️ 均衡型增长配置", "🚀 积极型成长突破"],
    key="strategy_preset_option"
)

# 积极型策略阻断警告
if preset_option == "🚀 积极型成长突破" and st.session_state.is_prohibit_aggressive:
    st.sidebar.error("⚠️ 评估警示：当前家庭财务体检结果显示您的财务状况较为脆弱（低备用金、低结余或高负债），系统已阻断积极型成长策略的选择。请先优化家庭财务结构！自动返回均衡配置。")
    st.session_state.strategy_preset_option = "⚖️ 均衡型增长配置"
    preset_option = "⚖️ 均衡型增长配置"
elif preset_option == "🚀 积极型成长突破" and st.session_state.family_aggressiveness < 30:
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

# ==========================================
# 模块 1: 家庭资产体检与配置建议
# ==========================================
if menu == "1. 家庭资产体检与配置建议":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>👤 家庭资产体检与配置建议</h1>", unsafe_allow_html=True)
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
            fd['expense-buyhouse'] = e_cols[0].checkbox("买房/换房", value=fd.get('expense-buyhouse', False))
            fd['expense-edu'] = e_cols[1].checkbox("子女教育", value=fd.get('expense-edu', False))
            fd['expense-med'] = e_cols[2].checkbox("大额医疗", value=fd.get('expense-med', False))
            fd['expense-biz'] = e_cols[0].checkbox("创业资金", value=fd.get('expense-biz', False))
            fd['expense-city'] = e_cols[1].checkbox("更换城市", value=fd.get('expense-city', False))
            fd['expense-other'] = e_cols[2].checkbox("其他大额支出", value=fd.get('expense-other', False))

        # 2. 收入与现金流
        with st.expander("💵 2. 收入与月现金流", expanded=True):
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                fd['f-monthly-income'] = st.number_input("家庭税后月收入 (元)", min_value=0.0, value=float(fd.get('f-monthly-income', 30000.0)), step=1000.0)
                fd['f-fixed-expense'] = st.number_input("月固定生活支出 (元)", min_value=0.0, value=float(fd.get('f-fixed-expense', 12000.0)), step=1000.0)
            with sub_col2:
                fd['f-income-sources'] = st.number_input("家庭收入来源数量 (个)", min_value=1, max_value=10, value=int(fd.get('f-income-sources', 2)))
                # 自动算可结余
                default_surplus = max(fd['f-monthly-income'] - fd['f-fixed-expense'] - fd.get('debt-monthly-repay', 0.0), 0.0)
                fd['f-surplus-income'] = st.number_input("月可结余 (元)", min_value=0.0, value=float(fd.get('f-surplus-income', default_surplus)), step=1000.0)

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
            fd['goal-cash'] = g_cols[0].checkbox("现金流补充", value=fd.get('goal-cash', False))
            fd['goal-edu'] = g_cols[1].checkbox("子女教育金", value=fd.get('goal-edu', False))
            fd['goal-pension'] = g_cols[2].checkbox("养老储备", value=fd.get('goal-pension', False))
            fd['goal-house'] = g_cols[3].checkbox("买房/换房", value=fd.get('goal-house', False))
            fd['goal-protect'] = g_cols[0].checkbox("财富保值", value=fd.get('goal-protect', False))
            fd['goal-growth'] = g_cols[1].checkbox("资产增值", value=fd.get('goal-growth', False))
            fd['goal-retire'] = g_cols[2].checkbox("提前退休", value=fd.get('goal-retire', False))

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
        monthly_fixed_ex = fd['f-fixed-expense'] if fd['f-fixed-expense'] > 0 else 1.0
        cash_coverage_months = liquid_cash / monthly_fixed_ex
        
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
        vulnerability = min(vulnerability, 100)

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
            <h3 style='margin-top:0; color:#FFFFFF;'>{res['profileTitle']}</h3>
            <p style='font-size:0.92rem; line-height:1.4;'>{res['profileDiag']}</p>
            <blockquote style='font-style:italic; font-size:0.85rem; color:#94A3B8; border-left:2px solid #4A5568; padding-left:10px;'>{res['quote']}</blockquote>
        </div>
        """, unsafe_allow_html=True)

        # 三桶可视化展示
        st.markdown(f"""
        <div class='card'>
            <div class='card-title'>🪣 三桶资产防御防线配置建议</div>
            <div style='font-size: 0.8rem; color:#94A3B8; margin-bottom:15px;'>
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
            font_color='#E2E8F0', margin=dict(t=10, b=10, l=10, r=10), showlegend=True, legend=dict(orientation='h', y=-0.5)
        )
        st.plotly_chart(fig_buckets, use_container_width=True)
        
        st.markdown(f"""
            <div style='font-size: 0.85rem; margin-top: 15px;'>
                <strong>🤔 为什么这么配？（资产配置结构原理解析）</strong>
                <p style='color:#94A3B8; line-height:1.4; background: rgba(255,255,255,0.02); padding: 8px; border-radius: 4px; border: 1px dashed rgba(255,255,255,0.1);'>{res['reason']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 指标诊断值
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>流动资产应急现金覆盖月数</div>
            <div class='metric-value'>{cash_coverage_months:.1f} 个月</div>
            <hr style='border:0; border-top:1px solid rgba(255,255,255,0.08); margin:10px 0;'>
            <table style='font-size:0.85rem; width:100%; border-collapse:collapse; color:#94A3B8;'>
                <tr><td>家庭资产负债率 (LTV)</td><td style='text-align:right; font-weight:600; color:#FFFFFF;'>{leverage*100:.1f}%</td></tr>
                <tr><td>月贷款还本付息比 (DSR)</td><td style='text-align:right; font-weight:600; color:#FFFFFF;'>{repay_income_ratio*100:.1f}%</td></tr>
                <tr><td>月可支配储蓄结余率</td><td style='text-align:right; font-weight:600; color:#FFFFFF;'>{surplus_ratio*100:.1f}%</td></tr>
                <tr><td>理财市场集中度风险 (HHI)</td><td style='text-align:right; font-weight:600; color:#FFFFFF;'>{concentration*100:.1f}%</td></tr>
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
        fig_assets.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0', height=240, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_assets, use_container_width=True)

# ==========================================
# 模块 2: 资产配置与股息测算看板
# ==========================================
elif menu == "2. 资产配置与股息测算看板":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>📊 资产配置与股息测算看板</h1>", unsafe_allow_html=True)
    st.write(f"当前可用总本金 **{principal:.1f}** 万元，其中已调拨 **{buffer_seed:.1f}** 万元进入初始缓冲池，实际进入组合配置的可投资本金为 **{invest_principal:.1f}** 万元。")
    
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
                <div style='font-weight:600; color:#FFFFFF; font-size:0.85rem;'>{info['name']}</div>
                <div style='color:#94A3B8; font-size:0.7rem; margin-bottom:5px;'>
                    代码: {code} | 角色: <span style='color:#10B981;'>{info['role']}</span>
                </div>
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
            st.write(f"当前最新在线股息率: **{info['yield']:.2f}%**")
            
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
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>预期年税后分红/利息</div>
            <div class='metric-value'>¥{res['expectedAnnualDividend']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>折合月均现金流</div>
            <div class='metric-value'>¥{res['expectedMonthlyDividend']:,.0f}</div>
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

    # 饼图与明细表格
    st.markdown("### 📋 投资明细与比重分布")
    
    # 资产角色的分布统计
    role_weights = {}
    for detail in res['assetDetails']:
        role = detail['role']
        role_weights[role] = role_weights.get(role, 0.0) + detail['weight']
    
    fig_role = px.pie(
        names=list(role_weights.keys()),
        values=list(role_weights.values()),
        title="组合资产角色分布",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_role.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0', height=280)
    st.plotly_chart(fig_role, use_container_width=True)

    # 标的资产表格明细
    table_rows = []
    for d in res['assetDetails']:
        table_rows.append({
            '代码': d['code'],
            '标的名称': d['name'],
            '配置角色': d['role'],
            '市场/波动': f"{d['market']} / {d['volatility_level']}",
            '权重 (%)': f"{d['weight']:.1f}%",
            '分配金额': f"{d['allocatedAmt']:.2f} 万元",
            '股息/预期回报': f"{d['yield']:.2f}% / {d['estimated_return']:.2f}%",
            '预计年分红/利息': f"¥{d['expectedAnnualDiv']:,.0f}",
            '定位与主要风险': f"🎯 {d['strategy_note']}  ⚠️ {d['risk_note']}"
        })
    st.table(pd.DataFrame(table_rows))

# ==========================================
# 模块 3: 现金缓冲池平滑模拟器
# ==========================================
elif menu == "3. 现金缓冲池平滑模拟器":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>⏱️ 现金缓冲池平滑模拟器</h1>", unsafe_allow_html=True)
    st.write("大多数红利资产的分红在少数月份集中派发。默认安全结论只基于分红、票息、现金利息和缓冲池，不把成长资产上涨当成稳定现金流。")

    rebalance_harvest = st.checkbox("乐观情景：卖出成长资产补充现金流", value=False, help="仅作为附加情景，不计入默认现金流安全结论")
    harvest_scenario = st.selectbox(
        "卖出成长资产补流情景",
        ["conservative", "neutral", "optimistic"],
        index=1,
        format_func=lambda x: {"conservative": "保守：-20% 至 0%", "neutral": "中性：0% 至 5%", "optimistic": "乐观：按预期收益率"}[x],
        disabled=not rebalance_harvest
    )

    # 默认安全结论不纳入卖出成长资产
    base_sim = portfolio_engine.simulate_cashflow(
        36,
        target_monthly * 10000.0,
        buffer_seed,
        invest_principal,
        weights,
        ASSETS_CONFIG,
        money_market_rate / 100.0,
        False,
        'neutral'
    )
    sim = portfolio_engine.simulate_cashflow(
        36,
        target_monthly * 10000.0,
        buffer_seed,
        invest_principal,
        weights,
        ASSETS_CONFIG,
        money_market_rate / 100.0,
        rebalance_harvest,
        harvest_scenario
    ) if rebalance_harvest else base_sim
    feasibility = portfolio_engine.calculate_cashflow_feasibility(
        36,
        target_monthly * 10000.0,
        buffer_seed,
        principal,
        weights,
        ASSETS_CONFIG,
        money_market_rate / 100.0
    )

    # 关键指标体检
    min_buffer = base_sim['minBuffer']
    tot_div_sum = sum(base_sim['dividendsHistory'])
    tot_harvest_sum = sum(sim['harvestHistory'])

    st.markdown("### 🔍 缓冲池安全性体检")
    b_col1, b_col2, b_col3, b_col4, b_col5, b_col6 = st.columns(6)
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
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>3年预计累计红利</div>
            <div class='metric-value'>¥{tot_div_sum:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with b_col4:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>建议每月支出不超过</div>
            <div class='metric-value'>{feasibility['recommendedMonthlyExpenseWan']:.2f} 万</div>
        </div>
        """, unsafe_allow_html=True)
    with b_col5:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>理论安全月支取上限</div>
            <div class='metric-value'>{feasibility['safeMonthlyWithdrawWan']:.2f} 万</div>
        </div>
        """, unsafe_allow_html=True)
    with b_col6:
        buffer_months_text = "仅加缓冲不足" if feasibility['minBufferMonths'] is None else f"{feasibility['minBufferMonths']:.1f}个月"
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>目标所需缓冲月数</div>
            <div class='metric-value'>{buffer_months_text}</div>
        </div>
        """, unsafe_allow_html=True)

    if min_buffer <= 0:
        min_principal = feasibility['minPrincipalWan']
        min_principal_text = "超过测算上限" if min_principal is None else f"{min_principal:.1f} 万元"
        msg = f"⚠️ **缓冲池期中击穿警报**：不计卖出成长资产时，缓冲池最低水位为 ¥{min_buffer:,.0f}。建议每月支出不超过 **{feasibility['recommendedMonthlyExpenseWan']:.2f} 万元**（理论临界上限约 {feasibility['safeMonthlyWithdrawWan']:.2f} 万元，已预留 5% 安全余量）。若默认 400 万本金、12 万缓冲池、月取 2 万无法通过，原因是稳定分红/票息/现金利息不足以覆盖持续支取；解决路径是降低支取、增加本金（测算最低约 {min_principal_text}）或增加缓冲，而不是提高科技仓位。"
        if rebalance_harvest and sim['minBuffer'] > 0:
            msg += " 当前附加情景依赖卖出成长资产才能维持现金流。"
        st.error(msg)
    else:
        st.success(f"✅ **缓冲池平滑成功**：不计卖出成长资产时，36 个月内缓冲池余额始终大于 0。建议每月支出不超过 **{feasibility['recommendedMonthlyExpenseWan']:.2f} 万元**，理论临界上限约 {feasibility['safeMonthlyWithdrawWan']:.2f} 万元。")
    if rebalance_harvest:
        st.info(f"附加情景：3年卖出成长资产补流合计 ¥{tot_harvest_sum:,.0f}。该项仅表示依赖变现资产补充现金流，不视为稳定现金流。")

    # 可视化折线/柱状混合图表
    timeline_months = [f"第 {t} 个月 (阴历 {((t-1)%12)+1}月)" for t in range(1, 37)]
    fig_buffer = go.Figure()
    fig_buffer.add_trace(go.Scatter(
        x=timeline_months,
        y=sim['bufferHistory'],
        mode='lines+markers',
        name='缓冲池水位 (元)',
        line=dict(color='#10B981', width=3),
        marker=dict(size=6)
    ))
    fig_buffer.add_trace(go.Bar(
        x=timeline_months,
        y=sim['dividendsHistory'],
        name='当月分红/票息到账 (元)',
        marker_color='#3B82F6',
        opacity=0.8
    ))
    if rebalance_harvest:
        fig_buffer.add_trace(go.Bar(
            x=timeline_months,
            y=sim['harvestHistory'],
            name='资本超额增长变现 (元)',
            marker_color='#A78BFA',
            opacity=0.8
        ))
    
    fig_buffer.update_layout(
        title="36个月缓冲池水位与红利分配动态趋势图",
        xaxis_title="模拟时间线",
        yaxis_title="水位/金额 (元)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#E2E8F0',
        hovermode="x unified"
    )
    st.plotly_chart(fig_buffer, use_container_width=True)

    # 导出明细数据
    with st.expander("📂 查看36个月现金流流转明细表格"):
        timeline_df = pd.DataFrame({
            '模拟月份': timeline_months,
            '当月收到分红/票息 (元)': sim['dividendsHistory'],
            '当月利息收益 (元)': sim['interestEarnedHistory'],
            '情景卖出资产补流 (元)': sim['harvestHistory'],
            '期末缓冲池余额 (元)': sim['bufferHistory']
        })
        st.dataframe(timeline_df.style.format({
            '当月收到分红/票息 (元)': '¥{:,.0f}',
            '当月利息收益 (元)': '¥{:,.2f}',
            '情景卖出资产补流 (元)': '¥{:,.0f}',
            '期末缓冲池余额 (元)': '¥{:,.0f}'
        }))

# ==========================================
# 模块 4: 估值温度计与测算工具
# ==========================================
elif menu == "4. 估值温度计与测算工具":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>🌡️ 估值温度计与测算助手</h1>", unsafe_allow_html=True)
    st.write("根据估值高低动态调整每期定投比例：低位高性价比多买，高位低性价比少买。")

    # 估值指数切换
    index_code = st.selectbox(
        "请选择要进行定投校准的指数标的",
        ["H30269 (中证红利低波)", "000300 (沪深300)"],
        index=0
    )
    index_clean = index_code.split(" ")[0]
    role_to_use = 'dividend_income' if index_clean == 'H30269' else 'domestic_beta'

    # 加载估值历史
    history_file = "valuation_history.json"
    history_data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        except:
            pass

    # 计算定投调节因子
    res = portfolio_engine.get_dca_adjustment(history_data, index_clean, role_to_use)

    st.markdown(f"### 📊 {index_code} 指数温度计指标板")
    t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns(5)
    with t_col1:
        lbl = "最新估值股息率" if index_clean == 'H30269' else "最新市盈率 (PE)"
        val = res['dividend_yield'] if index_clean == 'H30269' else res['pe']
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>{lbl}</div>
            <div class='metric-value' style='color:#3B82F6;'>{val}</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col2:
        lbl = "历史股息率百分位" if index_clean == 'H30269' else "历史 PE 百分位"
        color = "#10B981" if (res['percentile'] >= 70 if index_clean == 'H30269' else res['percentile'] <= 30) else ("#EF4444" if (res['percentile'] <= 30 if index_clean == 'H30269' else res['percentile'] >= 70) else "#F59E0B")
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>{lbl}</div>
            <div class='metric-value' style='color:{color};'>{res['percentile']}%</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col3:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>市盈率 (PE)</div>
            <div class='metric-value'>{res['pe']}</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col4:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>市净率 (PB)</div>
            <div class='metric-value'>{res['pb']}</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col5:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>定投调节系数</div>
            <div class='metric-value' style='color:#10B981;'>{res['factor']}x</div>
        </div>
        """, unsafe_allow_html=True)

    # 诊断横幅
    color_banner = "#10B981" if res['factor'] > 1.1 else ("#EF4444" if res['factor'] < 0.9 else "#3B82F6")
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.03); border:1px solid {color_banner}; border-radius:8px; padding:15px; margin-bottom:20px;'>
        <h4 style='color:{color_banner};margin-top:0;'>🏷️ 估值评级诊断：{res['valuationZone']}</h4>
        <p style='color:#E2E8F0;font-size:0.95rem;margin-bottom:0;'>{res['tips']}</p>
    </div>
    """, unsafe_allow_html=True)

    # 动态定投测算
    st.markdown("### 🎯 动态定投额度调节方案")
    base_dca = st.number_input("请输入您计划的基础定投总额 (万元)", min_value=1.0, max_value=200.0, value=32.3, step=1.0)
    adjusted_dca = base_dca * res['factor']
    
    st.markdown(f"上方指数仅用于查看温度计。下方组合定投按每个资产自己的 `target_index_code` 和 `role` 分别计算，不再用单一指数因子套全组合。")

    # 配置细表
    def default_target_index(role):
        return {
            'dividend_income': 'H30269',
            'domestic_beta': '000300',
            'tech_growth': '588000',
            'overseas_tech': 'NDX'
        }.get(role)

    rec_data = []
    total_adjusted_dca = 0.0
    for code, info in ASSETS_CONFIG.items():
        target_index = info.get('target_index_code') if info.get('target_index_code') is not None else default_target_index(info.get('role'))
        if target_index:
            asset_res = portfolio_engine.get_dca_adjustment(history_data, target_index, info.get('role'))
        else:
            asset_res = {
                'factor': 1.0,
                'valuationZone': '现金/对冲资产不做估值择时'
            }
        rec_amt = base_dca * (weights[code] / 100.0) * asset_res['factor']
        total_adjusted_dca += rec_amt
        rec_data.append({
            '基金代码': code,
            '基金名称': info['name'],
            '配置占比': f"{weights[code]:.1f}%",
            '目标指数': target_index or '--',
            '估值状态': asset_res['valuationZone'],
            'Factor': f"{asset_res['factor']:.1f}x",
            '本期定投应申购买入额度 (元)': f"¥{rec_amt * 10000:,.0f}"
        })
    st.markdown(f"基于逐资产估值因子，本月组合测算实缴总额为：**{total_adjusted_dca:.2f} 万元**。")
    st.table(pd.DataFrame(rec_data))

    # 绘制估值线图
    if res['hasHistory']:
        filtered_history = [item for item in history_data if item['index_code'] == index_clean]
        dates = [item['date'] for item in filtered_history]
        y_vals = [float(item['dividend_yield']) if index_clean == 'H30269' else float(item['pe']) for item in filtered_history]
        pe_vals = [float(item['pe']) for item in filtered_history]
        pb_vals = [float(item['pb']) for item in filtered_history]

        fig_val = go.Figure()
        fig_val.add_trace(go.Scatter(
            x=dates,
            y=y_vals,
            mode='lines',
            name='历史估值趋势',
            line=dict(color='#3B82F6', width=2),
            customdata=np.stack((pe_vals, pb_vals), axis=-1),
            hovertemplate="日期: %{x}<br>当前估值指标: %{y:.2f}<br>PE: %{customdata[0]:.2f}<br>PB: %{customdata[1]:.2f}<extra></extra>"
        ))
        
        # 当前水平虚线
        curr_val = float(res['dividend_yield'].replace('%','')) if index_clean == 'H30269' else float(res['pe'])
        fig_val.add_trace(go.Scatter(
            x=[dates[0], dates[-1]],
            y=[curr_val, curr_val],
            mode='lines',
            name='当前估值位置',
            line=dict(color=color_banner, dash='dash')
        ))

        fig_val.update_layout(
            title=f"{index_code} 指数历史走势图",
            xaxis_title="日期",
            yaxis_title="股息率 (%)" if index_clean == 'H30269' else "市盈率 (PE)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E2E8F0',
            height=300
        )
        st.plotly_chart(fig_val, use_container_width=True)
    else:
        st.info("该标的未找到足够历史数据，已采用常规计划。")

# ==========================================
# 模块 5: 年度资产再平衡测算
# ==========================================
elif menu == "5. 年度资产再平衡测算":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>⚖️ 持仓账本与资产再平衡测算</h1>", unsafe_allow_html=True)
    st.write("为了保持资产组合符合预设比例，通常建议于每年底检查持仓并做再平衡测算。")

    st.markdown("### 📝 输入每只配置资产的当期市值 (万元)")
    
    cols_hold = st.columns(4)
    user_holdings = {}
    idx = 0
    for code, info in ASSETS_CONFIG.items():
        col = cols_hold[idx % 4]
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
        incremental_mode = st.checkbox("增量资金再平衡优先", value=True)
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

        if incremental_mode:
            remaining_cash = new_cash
            for row in sorted([r for r in plan_rows if r['adjust_value'] > 0.5 and r['is_over_band']], key=lambda r: r['adjust_value'], reverse=True):
                row['incremental_buy'] = min(row['adjust_value'], remaining_cash)
                remaining_cash -= row['incremental_buy']

        rebalance_rows = []
        for row in plan_rows:
            adjust_value = row['adjust_value']
            if not row['is_over_band']:
                action = "阈值内观察"
            elif row['incremental_buy'] > 0:
                residual = adjust_value - row['incremental_buy']
                action = f"🟢 新增资金买入 {row['incremental_buy']:.2f} 万元"
                if residual > 0.5:
                    action += f"；仍低配 {residual:.2f} 万元，后续增量继续补足"
            elif adjust_value > 0.5:
                action = f"🟢 建议买入/入金补足 {adjust_value:.2f} 万元"
            elif adjust_value < -0.5:
                action = f"🔴 建议卖出变现 {-adjust_value:.2f} 万元"
            else:
                action = "无需变动 (配比平衡)"

            rebalance_rows.append({
                '标的代码': row['code'],
                '标的名称': row['info']['name'],
                '目标设定比例': f"{row['target_pct']:.1f}%",
                '当期实际比例': f"{row['actual_pct']:.1f}%",
                '比重偏离度': f"{row['diff_pct']:+.1f}%",
                '资产阈值': f"±{row['band']:.1f}%",
                '理想健康持仓': f"{row['ideal_value']:.2f} 万元",
                '年度再平衡动作': action
            })

        st.table(pd.DataFrame(rebalance_rows))
        st.info("💡 **小贴士**：年度再平衡除买高卖低外，更优的实践是利用增量资金买入占比过低的标的（即“增量资金再平衡”），能有效避免卖出摩擦费率。")

# ==========================================
# 模块 6: 风险压力测试
# ==========================================
elif menu == "6. 风险压力测试":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>⚡ 组合极端市场压力测试</h1>", unsafe_allow_html=True)
    st.warning("⚠️ **重要风险提示：** 极端市场压力测试仅作为弹性分析工具，分红率和净值表现不代表收益承诺。")

    st.markdown("### 🛠️ 压力测试极端行情模拟参数")
    col1, col2 = st.columns(2)
    
    with col1:
        stress_drawdown_cash = st.slider("现金类资产价格波动回撤 (%)", min_value=0, max_value=10, value=0)
        stress_drawdown_dividend = st.slider("红利类大底回撤比例 (%)", min_value=0, max_value=60, value=30)
        stress_drawdown_domestic = st.slider("国内宽基指数大跌回撤 (%)", min_value=0, max_value=60, value=35)
    
    with col2:
        stress_drawdown_tech = st.slider("科技成长类极端回撤 (%)", min_value=0, max_value=80, value=50)
        stress_drawdown_overseas = st.slider("海外权益/科技类回撤折算 (%)", min_value=0, max_value=70, value=40)
        stress_drawdown_hedge = st.slider("对冲资产(黄金/中债)回撤 (%)", min_value=0, max_value=40, value=15)

    stress_div_drop = st.slider("企业降息与派息率被动折损 (%)", min_value=0, max_value=100, value=25)
    default_stress_months = int(round(buffer_seed / target_monthly)) if target_monthly > 0 else 0
    stress_buffer_months = st.slider(
        "压力测试缓冲池覆盖月数（月）",
        min_value=0,
        max_value=60,
        value=max(0, min(default_stress_months, 60)),
        step=1,
        help=f"当前缓冲池金额为 {buffer_seed:.1f} 万元；按目标月支取 {target_monthly:.1f} 万元折算约 {default_stress_months} 个月。"
    )
    st.caption(f"缓冲池金额：{buffer_seed:.1f} 万元；压力测试使用覆盖月数：{stress_buffer_months} 个月。")

    # 整合参数包
    stress_params = {
        'drawdown': {
            'cash': stress_drawdown_cash,
            'dividend_income': stress_drawdown_dividend,
            'domestic_beta': stress_drawdown_domestic,
            'tech_growth': stress_drawdown_tech,
            'overseas_beta': stress_drawdown_overseas,
            'overseas_broad': stress_drawdown_overseas,
            'overseas_tech': stress_drawdown_overseas,
            'hedge': stress_drawdown_hedge
        },
        'dividendDrop': {
            'cash': 0.0,
            'dividend_income': stress_div_drop,
            'domestic_beta': 0.0,
            'tech_growth': 0.0,
            'overseas_beta': 0.0,
            'overseas_broad': 0.0,
            'overseas_tech': 0.0,
            'hedge': 0.0
        }
    }

    # 调用引擎压力核算
    res = portfolio_engine.run_stress_test(
        weights,
        ASSETS_CONFIG,
        invest_principal,
        target_monthly * 10000.0,
        stress_buffer_months,
        money_market_rate / 100.0,
        stress_params
    )

    st.markdown("### 🔍 极端市况抗震诊断结论")
    r_col1, r_col2, r_col3 = st.columns(3)
    
    # 构建 12 / 24 / 36 个月抗压卡片
    def show_streamlit_breach_card(period, history_sliced, limit_month):
        is_breached = any(v < 0 for v in history_sliced)
        if is_breached:
            breach_idx = next(i for i, v in enumerate(history_sliced) if v < 0) + 1
            status = "🔴 已击穿"
            color = "#EF4444"
            desc = f"在第 {breach_idx} 个月耗尽"
        else:
            status = "🟢 安全"
            color = "#10B981"
            desc = f"最低水位: ¥{min(history_sliced):,.0f}"

        st.markdown(f"""
        <div class='card' style='border: 1px solid {color};'>
            <div class='metric-label'>{period}个月内现金流防线</div>
            <div class='metric-value' style='color:{color}; font-size:1.6rem;'>{status}</div>
            <div style='font-size:0.78rem; color:#94A3B8; margin-top:5px;'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    with r_col1:
        show_streamlit_breach_card("12", res['stressedBufferHistory'][:12], res['breachedAtMonth'])
    with r_col2:
        show_streamlit_breach_card("24", res['stressedBufferHistory'][:24], res['breachedAtMonth'])
    with r_col3:
        show_streamlit_breach_card("36", res['stressedBufferHistory'][:36], res['breachedAtMonth'])

    # 本金回撤与承受度匹配核对
    st.markdown("### 🛡️ 本金最大回撤与承受力匹配")
    user_tolerance = float(st.session_state.family_data.get('inv-drawdown', 20.0))
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>极端行情预估组合最大本金折算回撤</div>
            <div class='metric-value' style='color:#EF4444;'>{res['maxNetWorthDrawdown']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with p_col2:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>您体检卡片中填写的风险回撤承受上限</div>
            <div class='metric-value'>{user_tolerance:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    if res['maxNetWorthDrawdown'] > user_tolerance:
        st.error(f"⚠️ **组合回撤超标警报**：压力测试下，本投资方案最大市值预期回撤 **{res['maxNetWorthDrawdown']:.2f}%** 已超越了您的回撤忍受极限（**{user_tolerance:.0f}%**）。为了防御本金风险，建议您减少成长/科技大类资产配置比例，调高防御性红利或现金等比重。")
    else:
        st.success(f"✅ **组合风险匹配良好**：压力回撤在您的风险接受范围内，配比健康！")

    # 绘制波动折线图
    months_labels = [f"第 {t} 个月" for t in range(1, 37)]
    fig_stress = go.Figure()
    fig_stress.add_trace(go.Scatter(
        x=months_labels,
        y=res['stressedBufferHistory'],
        mode='lines+markers',
        name='极端压力下缓冲池余额',
        line=dict(color='#EF4444' if res['isBreached'] else '#3B82F6', width=2.5)
    ))
    fig_stress.add_trace(go.Scatter(
        x=months_labels,
        y=[0] * 36,
        mode='lines',
        name='零点破产线',
        line=dict(color='#94A3B8', dash='dash')
    ))
    fig_stress.update_layout(
        title="压力测试下 36 个月缓冲池水位投影趋势",
        xaxis_title="模拟时间线 (月)",
        yaxis_title="余额 (元)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#E2E8F0',
        height=320
    )
    st.plotly_chart(fig_stress, use_container_width=True)

# ==========================================
# 模块 7: 人生财富游戏
# ==========================================
elif menu == "7. 人生财富游戏":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>🎮 人生财富游戏</h1>", unsafe_allow_html=True)
    st.info("本模块是中国家庭财富教育模拟，不复制任何现有桌游规则。每回合代表 1 年，覆盖 22 岁大学毕业到 60 岁退休的过程。开局身份与城市随机生成，不允许手动选择；成长资产浮盈不计入稳定现金流，只有分红、票息、租金、利息和副业净流入计入被动现金流。")

    WEALTH_GAME_START_AGE = 22
    WEALTH_GAME_RETIREMENT_AGE = 60

    career_profiles = {
        "white_collar": {"label": "普通白领", "base_salary": 9500, "base_expense": 4200, "tax_rate": 0.15, "cash": 30000, "stage": "单身", "city_income_sensitivity": 0.9, "income_volatility": 1.0},
        "public_sector": {"label": "体制内", "base_salary": 8200, "base_expense": 3800, "tax_rate": 0.12, "cash": 45000, "stage": "单身", "city_income_sensitivity": 0.55, "income_volatility": 0.55},
        "internet": {"label": "互联网从业者", "base_salary": 16500, "base_expense": 5400, "tax_rate": 0.23, "cash": 52000, "stage": "单身", "city_income_sensitivity": 1.35, "income_volatility": 1.35},
        "manufacturing": {"label": "制造业技术岗", "base_salary": 7800, "base_expense": 3600, "tax_rate": 0.12, "cash": 26000, "stage": "单身", "city_income_sensitivity": 0.75, "income_volatility": 0.9},
        "finance": {"label": "金融从业者", "base_salary": 15500, "base_expense": 5600, "tax_rate": 0.25, "cash": 60000, "stage": "单身", "city_income_sensitivity": 1.25, "income_volatility": 1.25},
        "freelancer": {"label": "自由职业者", "base_salary": 11000, "base_expense": 4500, "tax_rate": 0.10, "cash": 35000, "stage": "单身", "city_income_sensitivity": 0.9, "income_volatility": 1.45},
        "small_business": {"label": "小微经营者", "base_salary": 13500, "base_expense": 5200, "tax_rate": 0.10, "cash": 65000, "stage": "已婚", "city_income_sensitivity": 0.85, "income_volatility": 1.6}
    }

    city_profiles = {
        "first_tier": {"label": "一线城市", "income_factor": 1.28, "expense_factor": 1.35, "housing": 5800, "cash_factor": 1.25},
        "new_tier1": {"label": "新一线城市", "income_factor": 1.10, "expense_factor": 1.14, "housing": 3200, "cash_factor": 1.05},
        "second_tier": {"label": "二线城市", "income_factor": 0.95, "expense_factor": 0.96, "housing": 2200, "cash_factor": 0.92},
        "third_tier": {"label": "三线城市", "income_factor": 0.78, "expense_factor": 0.80, "housing": 1400, "cash_factor": 0.78},
        "county": {"label": "县城/低线城市", "income_factor": 0.62, "expense_factor": 0.66, "housing": 900, "cash_factor": 0.65}
    }

    legacy_profiles = {
        "white_collar": {"identity_key": "white_collar", "city_key": "new_tier1"},
        "public_sector": {"identity_key": "public_sector", "city_key": "second_tier"},
        "internet": {"identity_key": "internet", "city_key": "first_tier"},
        "freelancer": {"identity_key": "freelancer", "city_key": "new_tier1"},
        "small_business": {"identity_key": "small_business", "city_key": "third_tier"}
    }

    profile_options = [
        {"identity_key": "internet", "city_key": "first_tier", "note": "高收入高支出，高波动"},
        {"identity_key": "finance", "city_key": "first_tier", "note": "高收入高税费，职业周期敏感"},
        {"identity_key": "white_collar", "city_key": "new_tier1", "note": "典型城市白领现金流"},
        {"identity_key": "freelancer", "city_key": "new_tier1", "note": "收入弹性高，稳定性较弱"},
        {"identity_key": "public_sector", "city_key": "second_tier", "note": "收入较稳，支出适中"},
        {"identity_key": "manufacturing", "city_key": "second_tier", "note": "技术岗收入稳健，弹性有限"},
        {"identity_key": "white_collar", "city_key": "second_tier", "note": "收入支出相对均衡"},
        {"identity_key": "small_business", "city_key": "third_tier", "note": "经营现金流波动较大"},
        {"identity_key": "public_sector", "city_key": "county", "note": "低线稳定型，收入和支出都低"}
    ]

    def build_wealth_profile(identity_key="white_collar", city_key="new_tier1"):
        identity = career_profiles.get(identity_key, career_profiles["white_collar"])
        city = city_profiles.get(city_key, city_profiles["new_tier1"])
        adjusted_income_factor = 1 + ((city["income_factor"] - 1) * identity["city_income_sensitivity"])
        return {
            "identity_key": identity_key,
            "city_key": city_key,
            "label": identity["label"],
            "city": city["label"],
            "salary": round(identity["base_salary"] * adjusted_income_factor / 100) * 100,
            "expense": round(identity["base_expense"] * city["expense_factor"] / 100) * 100,
            "tax_rate": identity["tax_rate"],
            "housing": city["housing"],
            "cash": round(identity["cash"] * city["cash_factor"] / 1000) * 1000,
            "stage": identity["stage"],
            "income_volatility": identity["income_volatility"]
        }

    def create_random_wealth_game():
        option = random.choice(profile_options)
        return create_wealth_game(
            option["identity_key"],
            option["city_key"]
        )

    def is_profile_option(game):
        return any(
            option["identity_key"] == game.get("identity_key") and option["city_key"] == game.get("city_key")
            for option in profile_options
        )

    game_events = [
        {"name": "行业奖金到账", "cash": 20000, "text": "全年项目奖金到账，现金增加。", "weight": 8},
        {"name": "家电维修", "cash": -8000, "text": "家庭大件维修，必要支出上升。", "weight": 8},
        {"name": "父母体检与药费", "cash": -12000, "debt_type": "consumer_loan", "text": "赡养老人支出出现，现金流韧性被检验。", "weight": 7},
        {"name": "本人住院治疗", "cash": -42000, "debt_type": "consumer_loan", "text": "突发疾病产生医疗支出；现金不足会自动转为消费贷并按月付息。", "weight": 5},
        {"name": "家庭意外支出", "cash": -55000, "debt_type": "consumer_loan", "text": "家庭成员遭遇意外，需要立刻动用现金；不足部分转为贷款。", "weight": 4},
        {"name": "子女教育大额缴费", "cash": -22000, "debt_type": "credit_card", "text": "教育缴费集中发生，若现金不足会形成信用卡/短债压力。", "weight": 5},
        {"name": "车辆维修与保险", "cash": -12000, "debt_type": "credit_card", "text": "车辆维修、保险或交通罚款集中支出，考验现金缓冲。", "weight": 4},
        {"name": "结婚与组建家庭", "family_event": "marriage", "text": "进入结婚阶段，将发生婚礼、搬家和家庭共同生活支出。", "weight": 4},
        {"name": "孩子出生", "family_event": "childbirth", "text": "家庭迎来孩子，将发生生产、月嫂/育儿和长期教育支出。", "weight": 4},
        {"name": "家庭购房计划", "purchase": "house", "text": "家庭进入购房节点，将根据所在城市触发首付、房贷和住房支出变化。", "weight": 2},
        {"name": "通勤购车需求", "purchase": "car", "text": "工作通勤或家庭出行需要买车，将产生首付、车贷和养车支出。", "weight": 3},
        {"name": "旅行娱乐消费", "purchase": "leisure", "text": "本年发生旅行、娱乐或大额消费体验支出，现金不足会转为信用卡债务。", "weight": 5},
        {"name": "技能证书通过", "salary_boost": 0.02, "text": "技能提升带来工资小幅增长。", "weight": 6},
        {"name": "裁员风险", "income_shock": -0.18, "cash": -8000, "debt_type": "credit_card", "text": "行业波动导致全年收入下降。", "weight": 5},
        {"name": "A股回撤", "asset_shock": {"stock": -0.08, "dividend": -0.04, "overseas_tech": -0.06}, "text": "权益市场回撤，浮动市值下降，但不计入稳定现金流。", "weight": 7},
        {"name": "红利分红季", "bonus_passive": 6000, "text": "红利资产年度分红到账，计入被动现金流。", "weight": 6},
        {"name": "黄金上涨", "asset_shock": {"gold": 0.05}, "text": "避险资产上涨，对冲组合波动。", "weight": 4},
        {"name": "创业试错", "business_shock": 0.04, "cash": -20000, "debt_type": "business_loan", "text": "副业/小生意年度投入带来未来现金流可能性，也消耗现金。", "weight": 4},
        {"name": "平稳年份", "text": "没有重大事件，纪律比运气更重要。", "weight": 16}
    ]

    def create_wealth_game(profile_key="white_collar", city_key=None):
        legacy_profile = legacy_profiles.get(profile_key)
        identity_key = legacy_profile["identity_key"] if legacy_profile else profile_key
        resolved_city_key = city_key or (legacy_profile["city_key"] if legacy_profile else "new_tier1")
        p = build_wealth_profile(identity_key, resolved_city_key)
        game = {
            "profile_key": identity_key,
            "identity_key": identity_key,
            "city_key": resolved_city_key,
            "career": p["label"],
            "city": p["city"],
            "age": WEALTH_GAME_START_AGE,
            "year": 1,
            "retirement_age": WEALTH_GAME_RETIREMENT_AGE,
            "family_stage": p["stage"],
            "salary": p["salary"],
            "tax_rate": p["tax_rate"],
            "income_volatility": p["income_volatility"],
            "base_living_expense": p["expense"],
            "housing_expense": p["housing"],
            "essential_base": p["expense"] + p["housing"],
            "insurance_premium": 300,
            "education_expense": 0,
            "elder_expense": 0,
            "negative_cashflow_streak": 0,
            "freedom_streak": 0,
            "current_year_actions": [],
            "year_decision_log": [],
            "status": "进行中",
            "last_event": {"name": "开局", "text": "从第一份稳定现金流开始，先活下来，再谈增长。"},
            "last_decision": {"name": "开局", "text": "尚未做出年度决策。"},
            "assets": {"cash": p["cash"], "money_market": 0, "bond": 0, "stock": 0, "dividend": 0, "overseas_tech": 0, "gold": 0, "house": 0, "car": 0, "reit": 0, "side_business": 0},
            "debts": {"mortgage": 0, "car_loan": 0, "consumer_loan": 0, "credit_card": 0, "business_loan": 0},
            "history": []
        }
        record_wealth_year(game, calculate_wealth_metrics(game, {}), game["last_event"], game["last_decision"])
        return game

    def choose_wealth_event():
        pool = []
        for event in game_events:
            pool.extend([event] * event["weight"])
        return dict(random.choice(pool))

    def calculate_wealth_metrics(game, event):
        assets = game["assets"]
        debts = game["debts"]
        income_shock = event.get("income_shock", 0) * game.get("income_volatility", 1)
        active_income = max(0, game["salary"] * 12 * (1 - game["tax_rate"]) * (1 + income_shock))
        passive_income = (
            assets["money_market"] * 0.018 +
            assets["bond"] * 0.026 +
            assets["dividend"] * 0.036 +
            assets["reit"] * 0.042 +
            assets["house"] * 0.022 +
            assets["side_business"] * 0.12 +
            event.get("bonus_passive", 0)
        )
        debt_payment = debts.get("mortgage", 0) * 0.048 + debts.get("car_loan", 0) * 0.12 + debts.get("consumer_loan", 0) * 0.30 + debts.get("credit_card", 0) * 0.60 + debts.get("business_loan", 0) * 0.216
        base_living_expense = game.get("base_living_expense", game.get("essential_base", 0))
        housing_expense = game.get("housing_expense", 0)
        monthly_essential_expense = base_living_expense + housing_expense + game["insurance_premium"] + game["education_expense"] + game["elder_expense"]
        essential_expense = monthly_essential_expense * 12
        annual_cashflow = active_income + passive_income - essential_expense - debt_payment
        total_assets = sum(assets.values())
        total_debts = sum(debts.values())
        net_worth = total_assets - total_debts
        debt_ratio = total_debts / total_assets if total_assets > 0 else 0
        emergency_months = max(0, (assets["cash"] + assets["money_market"]) / monthly_essential_expense) if monthly_essential_expense > 0 else 0
        stress_score = min(100, round(debt_ratio * 55 + max(0, 12 - emergency_months) * 3 + (20 if annual_cashflow < 0 else 0)))
        return {
            "active_income": active_income,
            "passive_income": passive_income,
            "debt_payment": debt_payment,
            "essential_expense": essential_expense,
            "annual_cashflow": annual_cashflow,
            "monthly_cashflow": annual_cashflow,
            "total_assets": total_assets,
            "total_debts": total_debts,
            "net_worth": net_worth,
            "debt_ratio": debt_ratio,
            "emergency_months": emergency_months,
            "stress_score": stress_score
        }

    def record_wealth_year(game, metrics, event=None, decision=None):
        event = event or {}
        decision = decision or {}
        game["history"].append({
            "year": game["year"],
            "age": game["age"],
            "status": game["status"],
            "event_name": event.get("name", "开局"),
            "decision_name": decision.get("name", "开局"),
            "cashflow": metrics["annual_cashflow"],
            "passive_income": metrics["passive_income"],
            "essential_expense": metrics["essential_expense"],
            "emergency_months": metrics["emergency_months"],
            "total_assets": metrics["total_assets"],
            "total_debts": metrics["total_debts"],
            "net_worth": metrics["net_worth"],
            "debt_ratio": metrics["debt_ratio"],
            "stress_score": metrics["stress_score"]
        })
        game["history"] = game["history"][-40:]

    def finance_cash_cost(game, amount, debt_type="consumer_loan"):
        cost = max(0, amount)
        assets = game["assets"]
        debts = game["debts"]
        available = max(0, assets.get("cash", 0))
        paid_by_cash = min(available, cost)
        shortfall = cost - paid_by_cash
        assets["cash"] = available - paid_by_cash
        if shortfall > 0:
            debts[debt_type] = debts.get(debt_type, 0) + shortfall
        return shortfall

    def apply_house_purchase(game):
        assets = game["assets"]
        debts = game["debts"]
        if assets.get("house", 0) > 0:
            repair_cost = max(15000, game.get("housing_expense", 0) * 6)
            shortfall = finance_cash_cost(game, repair_cost, "consumer_loan")
            suffix = f"，现金不足新增消费贷 ¥{shortfall:,.0f}" if shortfall > 0 else ""
            return f"已有房产，本年发生装修/维修 ¥{repair_cost:,.0f}{suffix}。"
        monthly_housing = game.get("housing_expense", max(1200, game.get("essential_base", 0) * 0.3))
        house_price = round(max(300000, monthly_housing * 360) / 10000) * 10000
        down_payment = round(house_price * 0.3 / 10000) * 10000
        shortfall = finance_cash_cost(game, down_payment, "consumer_loan")
        assets["house"] += house_price
        debts["mortgage"] = debts.get("mortgage", 0) + (house_price - down_payment)
        game["housing_expense"] = round(monthly_housing * 0.25)
        suffix = f"；首付不足部分转消费贷 ¥{shortfall:,.0f}" if shortfall > 0 else ""
        return f"购入房产 ¥{house_price:,.0f}，首付 ¥{down_payment:,.0f}，新增房贷 ¥{house_price - down_payment:,.0f}{suffix}。"

    def apply_car_purchase(game):
        assets = game["assets"]
        debts = game["debts"]
        if assets.get("car", 0) > 0:
            upkeep_cost = 12000
            shortfall = finance_cash_cost(game, upkeep_cost, "credit_card")
            suffix = f"，现金不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
            return f"已有车辆，本年车辆保养、保险和停车支出 ¥{upkeep_cost:,.0f}{suffix}。"
        car_price = round(max(80000, game["salary"] * 8) / 1000) * 1000
        down_payment = round(car_price * 0.3 / 1000) * 1000
        shortfall = finance_cash_cost(game, down_payment, "credit_card")
        assets["car"] = assets.get("car", 0) + round(car_price * 0.85)
        debts["car_loan"] = debts.get("car_loan", 0) + (car_price - down_payment)
        game["base_living_expense"] = game.get("base_living_expense", game.get("essential_base", 0)) + 1200
        suffix = f"，首付不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
        return f"购车 ¥{car_price:,.0f}，首付 ¥{down_payment:,.0f}，新增车贷 ¥{car_price - down_payment:,.0f}；每月养车支出增加约 ¥1,200{suffix}。"

    def apply_leisure_expense(game):
        leisure_cost = round(max(8000, game["salary"] * 1.2) / 1000) * 1000
        shortfall = finance_cash_cost(game, leisure_cost, "credit_card")
        suffix = f"；现金不足新增信用卡债务 ¥{shortfall:,.0f}，后续按月付息" if shortfall > 0 else ""
        return f"旅行、娱乐和消费体验支出 ¥{leisure_cost:,.0f}{suffix}。"

    def apply_family_event(game, family_event):
        if family_event == "marriage":
            if game["family_stage"] != "单身":
                family_support_cost = round(max(10000, game["salary"] * 0.8) / 1000) * 1000
                shortfall = finance_cash_cost(game, family_support_cost, "credit_card")
                suffix = f"，现金不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
                return f"已进入家庭阶段，本年发生亲友礼金、家庭聚会或搬家支出 ¥{family_support_cost:,.0f}{suffix}。"
            wedding_cost = round(max(60000, game["salary"] * 6) / 10000) * 10000
            shortfall = finance_cash_cost(game, wedding_cost, "consumer_loan")
            game["family_stage"] = "已婚"
            game["base_living_expense"] = game.get("base_living_expense", game.get("essential_base", 0)) + 2500
            game["insurance_premium"] += 180
            suffix = f"；现金不足新增消费贷 ¥{shortfall:,.0f}" if shortfall > 0 else ""
            return f"结婚支出 ¥{wedding_cost:,.0f}，家庭共同生活每月支出增加约 ¥2,500，保障预算增加约 ¥180/月{suffix}。"
        if family_event == "childbirth":
            if game["family_stage"] == "单身":
                game["family_stage"] = "已婚"
                game["base_living_expense"] = game.get("base_living_expense", game.get("essential_base", 0)) + 1800
            birth_cost = round(max(40000, game["salary"] * 4) / 10000) * 10000
            shortfall = finance_cash_cost(game, birth_cost, "consumer_loan")
            game["family_stage"] = game["family_stage"] if "育儿" in game["family_stage"] else f"{game['family_stage']}育儿"
            game["base_living_expense"] = game.get("base_living_expense", game.get("essential_base", 0)) + 2200
            game["education_expense"] += 1800
            game["insurance_premium"] += 160
            suffix = f"；现金不足新增消费贷 ¥{shortfall:,.0f}" if shortfall > 0 else ""
            return f"生育与产后照护支出 ¥{birth_cost:,.0f}，每月育儿生活支出增加约 ¥2,200，教育储备增加约 ¥1,800/月{suffix}。"
        return ""

    def apply_wealth_decision(game, action):
        if game["status"] in ["现金流破产", "退休未达成", "稳健退休"]:
            return False
        game["current_year_actions"] = game.get("current_year_actions", [])
        game["year_decision_log"] = game.get("year_decision_log", [])
        action_names = {"save": "建应急金", "invest": "长期定投", "debt": "提前还债", "skill": "提升技能", "insurance": "补足保险"}
        if action in game["current_year_actions"]:
            game["last_decision"] = {"name": "本年已执行", "text": f"{action_names.get(action, '该决策')} 本年度已经做过一次，需点击“下一年”后才能再次选择。"}
            return False
        assets = game["assets"]
        debts = game["debts"]
        if action == "save":
            move = min(assets["cash"], 36000)
            assets["cash"] -= move
            assets["money_market"] += move
            game["last_decision"] = {"name": "建应急金", "text": f"转入货币基金 ¥{move:,.0f}，增强现金缓冲。"}
        elif action == "invest":
            invest = min(assets["cash"], 48000)
            assets["cash"] -= invest
            assets["stock"] += invest * 0.35
            assets["dividend"] += invest * 0.35
            assets["bond"] += invest * 0.15
            assets["gold"] += invest * 0.15
            game["last_decision"] = {"name": "长期定投", "text": f"投入 ¥{invest:,.0f} 到股票、红利、债券和黄金组合。"}
        elif action == "debt":
            repay = min(assets["cash"], debts.get("consumer_loan", 0) + debts.get("credit_card", 0) + debts.get("business_loan", 0) + debts.get("car_loan", 0), 60000)
            assets["cash"] -= repay
            remaining = repay
            for key in ["credit_card", "consumer_loan", "business_loan", "car_loan"]:
                used = min(debts.get(key, 0), remaining)
                debts[key] = max(0, debts.get(key, 0) - used)
                remaining -= used
            game["last_decision"] = {"name": "提前还债", "text": f"偿还高息债务 ¥{repay:,.0f}，降低后续月度利息压力。"}
        elif action == "buy_house":
            if assets.get("house", 0) > 0:
                repair_cost = max(15000, game.get("housing_expense", 0) * 6)
                shortfall = finance_cash_cost(game, repair_cost, "consumer_loan")
                suffix = f"，现金不足新增消费贷 ¥{shortfall:,.0f}" if shortfall > 0 else ""
                game["last_decision"] = {"name": "房屋维护", "text": f"已有房产，本年发生装修/维修 ¥{repair_cost:,.0f}{suffix}。"}
            else:
                monthly_housing = game.get("housing_expense", max(1200, game.get("essential_base", 0) * 0.3))
                house_price = round(max(300000, monthly_housing * 360) / 10000) * 10000
                down_payment = round(house_price * 0.3 / 10000) * 10000
                shortfall = finance_cash_cost(game, down_payment, "consumer_loan")
                assets["house"] += house_price
                debts["mortgage"] = debts.get("mortgage", 0) + (house_price - down_payment)
                game["housing_expense"] = round(monthly_housing * 0.25)
                suffix = f"；首付不足部分转消费贷 ¥{shortfall:,.0f}" if shortfall > 0 else ""
                game["last_decision"] = {"name": "买房", "text": f"购入房产 ¥{house_price:,.0f}，首付 ¥{down_payment:,.0f}，新增房贷 ¥{house_price - down_payment:,.0f}{suffix}。"}
        elif action == "buy_car":
            if assets.get("car", 0) > 0:
                upkeep_cost = 12000
                shortfall = finance_cash_cost(game, upkeep_cost, "credit_card")
                suffix = f"，现金不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
                game["last_decision"] = {"name": "养车支出", "text": f"已有车辆，本年车辆保养、保险和停车支出 ¥{upkeep_cost:,.0f}{suffix}。"}
            else:
                car_price = round(max(80000, game["salary"] * 8) / 1000) * 1000
                down_payment = round(car_price * 0.3 / 1000) * 1000
                shortfall = finance_cash_cost(game, down_payment, "credit_card")
                assets["car"] = assets.get("car", 0) + round(car_price * 0.85)
                debts["car_loan"] = debts.get("car_loan", 0) + (car_price - down_payment)
                game["base_living_expense"] = game.get("base_living_expense", game.get("essential_base", 0)) + 1200
                suffix = f"，首付不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
                game["last_decision"] = {"name": "买车", "text": f"购车 ¥{car_price:,.0f}，首付 ¥{down_payment:,.0f}，新增车贷 ¥{car_price - down_payment:,.0f}；每月养车支出增加约 ¥1,200{suffix}。"}
        elif action == "skill":
            shortfall = finance_cash_cost(game, 12000, "credit_card")
            game["salary"] *= 1.03
            assets["side_business"] += 6000
            suffix = f"；现金不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
            game["last_decision"] = {"name": "提升技能", "text": f"投入培训/副业试错 ¥12,000，月收入提升 3%{suffix}。"}
        elif action == "insurance":
            game["insurance_premium"] += 120
            shortfall = finance_cash_cost(game, 2000, "credit_card")
            suffix = f"；现金不足新增信用卡债务 ¥{shortfall:,.0f}" if shortfall > 0 else ""
            game["last_decision"] = {"name": "补足保险", "text": f"补充保障支出 ¥2,000，每月保费增加约 ¥120{suffix}。"}
        elif action == "leisure":
            leisure_cost = round(max(8000, game["salary"] * 1.2) / 1000) * 1000
            shortfall = finance_cash_cost(game, leisure_cost, "credit_card")
            suffix = f"；现金不足新增信用卡债务 ¥{shortfall:,.0f}，后续按月付息" if shortfall > 0 else ""
            game["last_decision"] = {"name": "游乐消费", "text": f"旅行、娱乐和消费体验支出 ¥{leisure_cost:,.0f}{suffix}。"}
        else:
            move = min(assets["cash"], 18000)
            assets["cash"] -= move
            assets["money_market"] += move
            game["last_decision"] = {"name": "均衡决策", "text": f"默认将 ¥{move:,.0f} 转入货币基金，先提高安全垫。"}
        game["current_year_actions"].append(action)
        game["year_decision_log"].append(dict(game["last_decision"]))
        return True

    def summarize_year_decisions(game):
        logs = game.get("year_decision_log", [])
        if not logs:
            return {"name": "未做主动决策", "text": "本年度未执行主动财务决策，直接进入年度事件与现金流结算。"}
        return {
            "name": f"本年已执行 {len(logs)} 项决策",
            "text": "；".join([f"{item.get('name', '')}：{item.get('text', '')}" for item in logs])
        }

    def advance_wealth_game(game):
        if game["status"] in ["现金流破产", "退休未达成", "稳健退休"]:
            return game
        decision_summary = summarize_year_decisions(game)
        event = choose_wealth_event()
        assets = game["assets"]
        if event.get("cash", 0) > 0:
            assets["cash"] += event["cash"]
        if event.get("cash", 0) < 0:
            shortfall = finance_cash_cost(game, abs(event["cash"]), event.get("debt_type", "credit_card"))
            if shortfall > 0:
                event["text"] += f" 现金不足，新增贷款 ¥{shortfall:,.0f}，后续将按月产生利息/还款压力。"
        if event.get("purchase") == "house":
            event["text"] += f" {apply_house_purchase(game)}"
        if event.get("purchase") == "car":
            event["text"] += f" {apply_car_purchase(game)}"
        if event.get("purchase") == "leisure":
            event["text"] += f" {apply_leisure_expense(game)}"
        if event.get("family_event"):
            event["text"] += f" {apply_family_event(game, event['family_event'])}"
        if event.get("salary_boost"):
            game["salary"] *= (1 + event["salary_boost"])
        if event.get("business_shock"):
            assets["side_business"] *= (1 + event["business_shock"])
        for key, shock in event.get("asset_shock", {}).items():
            assets[key] = max(0, assets.get(key, 0) * (1 + shock))
        metrics = calculate_wealth_metrics(game, event)
        assets["cash"] += metrics["annual_cashflow"]
        cashflow_loan = 0
        if assets["cash"] < 0:
            cashflow_loan = abs(assets["cash"])
            assets["cash"] = 0
            game["debts"]["credit_card"] = game["debts"].get("credit_card", 0) + cashflow_loan
            event["text"] += f" 年度现金流缺口 ¥{cashflow_loan:,.0f} 已转为信用卡/短债，后续按月付息。"
        final_metrics = calculate_wealth_metrics(game, event)
        game["negative_cashflow_streak"] = game["negative_cashflow_streak"] + 1 if metrics["annual_cashflow"] < 0 and cashflow_loan > 0 else 0
        game["freedom_streak"] = game["freedom_streak"] + 1 if final_metrics["passive_income"] >= final_metrics["essential_expense"] and final_metrics["emergency_months"] >= 12 else 0
        game["last_event"] = event
        game["year"] += 1
        game["age"] += 1
        if game["freedom_streak"] >= 3:
            game.setdefault("freedom_achieved_age", game["age"])
            game["status"] = "财务韧性胜利"
        if game["negative_cashflow_streak"] >= 2 or final_metrics["debt_ratio"] > 0.9:
            game["status"] = "现金流破产"
        if game["status"] != "现金流破产" and game["age"] >= game.get("retirement_age", WEALTH_GAME_RETIREMENT_AGE):
            game["status"] = "稳健退休" if game["freedom_streak"] >= 3 else "退休未达成"
        final_metrics["annual_cashflow"] = metrics["annual_cashflow"]
        final_metrics["monthly_cashflow"] = metrics["annual_cashflow"]
        record_wealth_year(game, final_metrics, event, decision_summary)
        game["current_year_actions"] = []
        game["year_decision_log"] = []
        game["last_decision"] = {"name": "本年待决策", "text": "新的一年已开启，五个年度决策可各执行一次。"}
        return game

    def wealth_advice(game, metrics):
        if game["status"] == "财务韧性胜利":
            return "你已连续 3 年做到被动现金流覆盖年度必要支出，并保有 12 个月以上应急金。下一步是控制杠杆和分散风险。"
        if game["status"] == "稳健退休":
            return "你已到达 60 岁退休节点，并保持被动现金流覆盖必要支出的能力。请查看下方人生财富分析报告。"
        if game["status"] == "现金流破产":
            return "现金流已经断裂。复盘重点不是追逐高收益，而是降低固定支出、处理高息债务、重建应急金。"
        if game["status"] == "退休未达成":
            return "已经到 60 岁退休节点但尚未达成被动现金流覆盖必要支出的状态。复盘重点是更早控制支出、降低杠杆并增加稳定现金流资产。"
        if metrics["emergency_months"] < 6:
            return "应急金不足 6 个月，优先储蓄和货币基金，不急于加大高波动资产。"
        if metrics["debt_ratio"] > 0.6:
            return "负债率偏高，优先处理信用卡、消费贷和经营贷，避免被利息吞噬现金流。"
        if metrics["passive_income"] < metrics["essential_expense"] * 0.3:
            return "被动现金流还弱，红利、票息、租金和副业现金流需要逐步积累。"
        return "现金流结构相对稳健。保持预算纪律，分散资产，别把成长资产浮盈当作稳定收入。"

    def generate_retirement_report(game, metrics):
        history = game.get("history", [])
        if game["age"] < game.get("retirement_age", WEALTH_GAME_RETIREMENT_AGE) or not history:
            return None
        min_emergency = min(item.get("emergency_months", 0) for item in history)
        max_debt_ratio = max(item.get("debt_ratio", 0) for item in history)
        negative_years = sum(1 for item in history if item.get("cashflow", 0) < 0)
        high_stress_years = sum(1 for item in history if item.get("stress_score", 0) >= 60)
        passive_coverage = metrics["passive_income"] / metrics["essential_expense"] if metrics["essential_expense"] > 0 else 0
        event_counts = {}
        for item in history:
            event_name = item.get("event_name", "未知事件")
            event_counts[event_name] = event_counts.get(event_name, 0) + 1
        notable_events = [
            f"{name}×{count}"
            for name, count in sorted(event_counts.items(), key=lambda kv: kv[1], reverse=True)
            if name not in ["开局", "平稳年份"]
        ][:4]
        debt_items = [
            ("房贷", game["debts"].get("mortgage", 0)),
            ("车贷", game["debts"].get("car_loan", 0)),
            ("消费贷", game["debts"].get("consumer_loan", 0)),
            ("信用卡/短债", game["debts"].get("credit_card", 0)),
            ("经营贷", game["debts"].get("business_loan", 0)),
        ]
        debt_text = "、".join([f"{name} ¥{value:,.0f}" for name, value in debt_items if value > 0]) or "无明显债务"
        conclusion = "退休现金流相对稳健，被动现金流和应急金能够覆盖大部分生活压力。" if passive_coverage >= 1 and metrics["emergency_months"] >= 12 and metrics["debt_ratio"] < 0.4 else "退休准备仍有短板，需要优先处理支取、债务和稳定现金流来源。"
        tips = []
        if min_emergency < 6:
            tips.append("游戏过程中应急金曾低于 6 个月，真实家庭应先补足安全垫。")
        if max_debt_ratio > 0.6:
            tips.append("负债率曾处于偏高区间，买房、买车和消费贷会放大现金流脆弱性。")
        if negative_years > 0:
            tips.append(f"共有 {negative_years} 年年度现金流为负，说明支出或债务还款压力需要更早干预。")
        if passive_coverage < 1:
            tips.append("退休时被动现金流尚未覆盖必要支出，不宜把成长资产浮盈当作稳定收入。")
        if high_stress_years > 0:
            tips.append(f"家庭压力指数有 {high_stress_years} 年处于高位，应关注疾病、家庭意外和职业收入波动。")
        if not tips:
            tips.append("整体路径较稳健，后续重点是维持低杠杆、分散资产和医疗保障。")
        return {
            "conclusion": conclusion,
            "min_emergency": min_emergency,
            "max_debt_ratio": max_debt_ratio,
            "negative_years": negative_years,
            "high_stress_years": high_stress_years,
            "passive_coverage": passive_coverage,
            "notable_events": "、".join(notable_events) if notable_events else "重大事件较少",
            "debt_text": debt_text,
            "tips": tips
        }

    if "wealth_game_state" not in st.session_state:
        st.session_state.wealth_game_state = create_random_wealth_game()
    elif "year" not in st.session_state.wealth_game_state or "city_key" not in st.session_state.wealth_game_state or "identity_key" not in st.session_state.wealth_game_state:
        stored_game = st.session_state.wealth_game_state
        legacy = legacy_profiles.get(stored_game.get("profile_key", "white_collar"), {})
        st.session_state.wealth_game_state = create_wealth_game(
            legacy.get("identity_key", stored_game.get("profile_key", "white_collar")),
            legacy.get("city_key", stored_game.get("city_key", "new_tier1"))
        )
    if not is_profile_option(st.session_state.wealth_game_state):
        st.session_state.wealth_game_state = create_random_wealth_game()
    st.session_state.wealth_game_state["current_year_actions"] = st.session_state.wealth_game_state.get("current_year_actions", [])
    st.session_state.wealth_game_state["year_decision_log"] = st.session_state.wealth_game_state.get("year_decision_log", [])

    current_game = st.session_state.wealth_game_state
    st.markdown("### 代表性身份 × 城市组合表")
    profile_rows = []
    for option in profile_options:
        p = build_wealth_profile(option["identity_key"], option["city_key"])
        is_current = current_game.get("identity_key") == option["identity_key"] and current_game.get("city_key") == option["city_key"]
        profile_rows.append((
            f"{p['label']}（当前）" if is_current else p["label"],
            p["city"],
            p["salary"],
            p["expense"],
            p["housing"],
            p["expense"] + p["housing"],
            p["cash"],
            option["note"]
        ))
    st.caption("随机开局只会从下列代表性画像中抽取；当前开局组合会标注为“当前”。")
    st.dataframe(pd.DataFrame(profile_rows, columns=["身份", "城市", "月收入", "基础消费", "住房", "必要支出", "初始现金", "画像特征"]), use_container_width=True, hide_index=True)

    used_actions = st.session_state.wealth_game_state.get("current_year_actions", [])
    terminal_game = st.session_state.wealth_game_state.get("status") in ["现金流破产", "退休未达成", "稳健退休"]
    c1, c2, c3, c4, c5 = st.columns(5)
    if c1.button("随机新开局", use_container_width=True):
        st.session_state.wealth_game_state = create_random_wealth_game()
        st.rerun()
    if c2.button("下一年：结算", use_container_width=True):
        st.session_state.wealth_game_state = advance_wealth_game(st.session_state.wealth_game_state)
        st.rerun()
    if c3.button("建应急金", use_container_width=True, disabled=terminal_game or "save" in used_actions):
        apply_wealth_decision(st.session_state.wealth_game_state, "save")
        st.rerun()
    if c4.button("长期定投", use_container_width=True, disabled=terminal_game or "invest" in used_actions):
        apply_wealth_decision(st.session_state.wealth_game_state, "invest")
        st.rerun()
    if c5.button("还债", use_container_width=True, disabled=terminal_game or "debt" in used_actions):
        apply_wealth_decision(st.session_state.wealth_game_state, "debt")
        st.rerun()
    d1, d2, d3 = st.columns(3)
    if d1.button("提升技能", use_container_width=True, disabled=terminal_game or "skill" in used_actions):
        apply_wealth_decision(st.session_state.wealth_game_state, "skill")
        st.rerun()
    if d2.button("补保险", use_container_width=True, disabled=terminal_game or "insurance" in used_actions):
        apply_wealth_decision(st.session_state.wealth_game_state, "insurance")
        st.rerun()
    if d3.button("重置", use_container_width=True):
        st.session_state.wealth_game_state = create_random_wealth_game()
        st.rerun()

    game = st.session_state.wealth_game_state
    metrics = calculate_wealth_metrics(game, game.get("last_event", {}))

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    cards = [
        ("年龄 / 阶段", f"{game['age']} 岁 / {game['family_stage']}", "#FFFFFF"),
        ("年度现金流", f"¥{metrics['annual_cashflow']:,.0f}", "#10B981" if metrics["annual_cashflow"] >= 0 else "#EF4444"),
        ("被动现金流", f"¥{metrics['passive_income']:,.0f}", "#3B82F6"),
        ("必要支出", f"¥{metrics['essential_expense']:,.0f}", "#F59E0B"),
        ("应急金月数", f"{metrics['emergency_months']:.1f}", "#10B981" if metrics["emergency_months"] >= 6 else "#EF4444"),
        ("净资产 / 负债率", f"¥{metrics['net_worth']:,.0f} / {metrics['debt_ratio']*100:.1f}%", "#FFFFFF")
    ]
    for col, (label, value, color) in zip([m1, m2, m3, m4, m5, m6], cards):
        col.markdown(f"<div class='card'><div class='metric-label'>{label}</div><div class='metric-value' style='color:{color};'>{value}</div></div>", unsafe_allow_html=True)

    decision_logs = game.get("year_decision_log", [])
    if decision_logs:
        st.markdown(f"### 年度决策：本年已执行 {len(decision_logs)}/5 项决策")
        for item in decision_logs:
            st.write(f"{item.get('name', '')}：{item.get('text', '')}")
    else:
        st.markdown(f"### 年度决策：{game.get('last_decision', {}).get('name', '开局')}")
        st.write(game.get("last_decision", {}).get("text", ""))
    st.markdown(f"### 事件卡：{game['last_event']['name']}")
    st.write(game["last_event"]["text"])
    st.warning(f"教学建议：{wealth_advice(game, metrics)}  家庭压力指数：{metrics['stress_score']}/100；胜利进度：{game['freedom_streak']}/3 年；退休节点：{game.get('retirement_age', WEALTH_GAME_RETIREMENT_AGE)} 岁。")

    retirement_report = generate_retirement_report(game, metrics)
    if retirement_report:
        st.info(
            f"### 60 岁人生财富分析报告\n\n"
            f"**结论：**{retirement_report['conclusion']}\n\n"
            f"**最终指标：**净资产 ¥{metrics['net_worth']:,.0f}；负债率 {metrics['debt_ratio']*100:.1f}%；"
            f"应急金 {metrics['emergency_months']:.1f} 个月；被动现金流覆盖率 {retirement_report['passive_coverage']*100:.1f}%。\n\n"
            f"**过程回顾：**最低应急金 {retirement_report['min_emergency']:.1f} 个月；最高负债率 {retirement_report['max_debt_ratio']*100:.1f}%；"
            f"负现金流年份 {retirement_report['negative_years']} 年；主要事件：{retirement_report['notable_events']}。\n\n"
            f"**退休债务结构：**{retirement_report['debt_text']}。\n\n"
            f"**风险点评：**{' '.join(retirement_report['tips'])}"
        )

    left, right = st.columns(2)
    with left:
        st.markdown("### 资产负债表")
        balance_rows = [
            ("现金", game["assets"]["cash"], "用于应急和年度周转"),
            ("货币基金", game["assets"]["money_market"], "流动性备用金"),
            ("债券/理财", game["assets"]["bond"], "票息型资产"),
            ("A股宽基", game["assets"]["stock"], "成长资产，浮盈不算现金流"),
            ("红利资产", game["assets"]["dividend"], "分红计入被动现金流"),
            ("海外科技", game["assets"]["overseas_tech"], "高波动成长资产"),
            ("黄金", game["assets"]["gold"], "对冲资产"),
            ("车辆", game["assets"].get("car", 0), "自用车，折旧资产，买车后增加车贷和养车支出"),
            ("房产/REITs/副业", game["assets"]["house"] + game["assets"]["reit"] + game["assets"]["side_business"], "租金或经营净流入计入被动现金流"),
            ("总负债", -metrics["total_debts"], "房贷/车贷/消费贷/信用卡/经营贷")
        ]
        st.dataframe(pd.DataFrame(balance_rows, columns=["项目", "金额", "说明"]), use_container_width=True, hide_index=True)
    with right:
        st.markdown("### 现金流表")
        cashflow_rows = [
            ("主动收入", metrics["active_income"], f"月收入基准 ¥{game['salary']:,.0f}，按城市和身份调整"),
            ("被动现金流", metrics["passive_income"], "仅分红、票息、租金、利息、副业净流入"),
            ("必要支出", -metrics["essential_expense"], "生活、住房、教育、赡养、保险"),
            ("债务支出", -metrics["debt_payment"], "房贷、车贷、消费贷、信用卡、经营贷按月付息/还款折算"),
            ("年度现金流", metrics["annual_cashflow"], "全年入账后影响现金余额")
        ]
        st.dataframe(pd.DataFrame(cashflow_rows, columns=["项目", "年度金额", "口径"]), use_container_width=True, hide_index=True)

    hist = pd.DataFrame(game["history"])
    if not hist.empty:
        fig_game = go.Figure()
        fig_game.add_trace(go.Scatter(x=hist["age"], y=hist["net_worth"], mode="lines+markers", name="净资产", line=dict(color="#10B981", width=2)))
        fig_game.add_trace(go.Scatter(x=hist["age"], y=hist["cashflow"], mode="lines+markers", name="年度现金流", line=dict(color="#3B82F6", width=2), yaxis="y2"))
        fig_game.add_trace(go.Scatter(x=hist["age"], y=hist["emergency_months"], mode="lines", name="应急金月数", line=dict(color="#F59E0B", width=2), yaxis="y3"))
        fig_game.update_layout(
            title="财富路径趋势",
            xaxis_title="年龄",
            yaxis=dict(title="净资产", gridcolor="rgba(255,255,255,0.05)"),
            yaxis2=dict(title="现金流", overlaying="y", side="right"),
            yaxis3=dict(visible=False, overlaying="y"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            hovermode="x unified",
            height=360
        )
        st.plotly_chart(fig_game, use_container_width=True)

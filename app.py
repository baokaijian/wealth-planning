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
# 页面基本配置与现代暗黑主题 CSS 注入
# ==========================================
st.set_page_config(
    page_title="红利低波资产现金流规划与监控工具",
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
        padding: 24px;
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
        font-size: 2.2rem;
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
# 初始配置参数：资产数据结构
# ==========================================
DEFAULT_ASSETS = {
    '512890': {'name': '中证红利低波 ETF', 'type': 'ETF', 'weight': 20.0, 'yield': 4.5, 'months': {7: 0.5, 12: 0.5}},
    '515450': {'name': '标普大盘红利低波 ETF', 'type': 'ETF', 'weight': 15.0, 'yield': 4.2, 'months': {7: 1.0}},
    '513530': {'name': '恒生红利低波 ETF', 'type': 'ETF', 'weight': 15.0, 'yield': 4.8, 'months': {7: 0.5, 12: 0.5}},
    '600941': {'name': '中国移动 (个股)', 'type': 'Stock', 'weight': 10.0, 'yield': 6.0, 'months': {6: 0.6, 9: 0.4}},
    '600900': {'name': '长江电力 (个股)', 'type': 'Stock', 'weight': 10.0, 'yield': 3.71, 'months': {7: 1.0}},
    '601398': {'name': '工商银行 (个股)', 'type': 'Stock', 'weight': 10.0, 'yield': 5.5, 'months': {7: 0.7, 12: 0.3}},
    '601088': {'name': '中国神华 (个股)', 'type': 'Stock', 'weight': 10.0, 'yield': 4.77, 'months': {7: 1.0}},
    '601668': {'name': '中国建筑 (个股)', 'type': 'Stock', 'weight': 10.0, 'yield': 5.52, 'months': {6: 1.0}}
}

# ==========================================
# 侧边栏：核心交互设置
# ==========================================
st.sidebar.markdown("<h2 style='color:#10B981;text-align:center;margin-bottom:20px;'>💰 策略配置中心</h2>", unsafe_allow_html=True)

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

# 实际投资金额为总本金减去缓冲池初始储备
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
if menu == "1. 资产配置与股息看板":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>📊 资产配置与股息测算看板</h1>", unsafe_allow_html=True)
    st.write(f"当前总本金 **{principal:.1f}** 万元，其中拨付 **{buffer_seed:.1f}** 万元进入现金缓冲池，实际进入红利资产配置本金为 **{invest_principal:.1f}** 万元。")
    
    # 允许用户微调各资产的权重
    st.markdown("### 🛠️ 组合权重与股息率调整")
    
    cols = st.columns(4)
    weights = {}
    yields = {}
    
    idx = 0
    for code, info in DEFAULT_ASSETS.items():
        col = cols[idx % 4]
        with col:
            st.markdown(f"""
            <div class='card' style='padding: 15px; margin-bottom: 10px;'>
                <div style='font-weight:600; color:#FFFFFF; font-size:0.9rem;'>{info['name']}</div>
                <div style='color:#94A3B8; font-size:0.75rem; margin-bottom:10px;'>代码: {code} | {info['type']}</div>
            </div>
            """, unsafe_allow_html=True)
            # 为了交互精细，使用 slider
            weight = st.slider(f"权重 (%) - {code}", min_value=0.0, max_value=50.0, value=info['weight'], step=0.5, key=f"w_{code}")
            dy = st.number_input(f"税后股息率 (%) - {code}", min_value=0.0, max_value=15.0, value=info['yield'], step=0.1, key=f"y_{code}")
            weights[code] = weight / 100.0
            yields[code] = dy / 100.0
        idx += 1
        
    # 验证权重之和是否为 100%
    total_weight = sum(weights.values())
    if not np.isclose(total_weight, 1.0):
        st.error(f"⚠️ 当前配置的总权重之和为 **{total_weight*100:.1f}%**，必须调整至 **100.0%** 才能使测算准确。")
    else:
        st.success("✅ 组合总权重等于 100%，配置方案完全就绪！")

    # 计算整体预期回报
    blended_yield = sum(weights[code] * yields[code] for code in DEFAULT_ASSETS.keys())
    expected_annual_dividend = invest_principal * blended_yield * 10000 # 转为元
    expected_monthly_avg = expected_annual_dividend / 12.0
    gap_monthly = (target_monthly * 10000) - expected_monthly_avg
    
    # 指标面板展示
    st.markdown("### 🎯 组合预期产出看板")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>加权税后股息率</div>
            <div class='metric-value' style='color:#10B981;'>{blended_yield*100:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>预期年税后分红</div>
            <div class='metric-value'>¥{expected_annual_dividend:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>折合月均现金流</div>
            <div class='metric-value'>¥{expected_monthly_avg:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m_col4:
        color = "#10B981" if gap_monthly <= 0 else "#EF4444"
        gap_text = f"-¥{-gap_monthly:,.0f} (超额)" if gap_monthly <= 0 else f"¥{gap_monthly:,.0f} (缺口)"
        st.markdown(f"""
        <div class='card'>
            <div class='metric-label'>目标月现金流缺口</div>
            <div class='metric-value' style='color:{color};'>{gap_text}</div>
        </div>
        """, unsafe_allow_html=True)

    # 绘制资产占比饼图与明细表格
    st.markdown("### 📋 投资明细与比重分布")
    tab1, tab2 = st.tabs(["📊 资金分配占比图", "🗂️ 标的投资明细数据"])
    
    with tab1:
        chart_data = pd.DataFrame({
            '资产名称': [DEFAULT_ASSETS[code]['name'] for code in DEFAULT_ASSETS.keys()],
            '配置比例 (%)': [weights[code]*100 for code in DEFAULT_ASSETS.keys()],
            '分配金额 (万元)': [invest_principal * weights[code] for code in DEFAULT_ASSETS.keys()],
            '预计年分红 (元)': [invest_principal * weights[code] * yields[code] * 10000 for code in DEFAULT_ASSETS.keys()]
        })
        fig = px.pie(
            chart_data, 
            names='资产名称', 
            values='配置比例 (%)', 
            title="红利配置组合占比饼图",
            color_discrete_sequence=px.colors.qualitative.Dark24
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E2E8F0',
            title_font_size=16
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
        st.table(chart_data.style.format({
            '配置比例 (%)': '{:.1f}%',
            '分配金额 (万元)': '{:.2f} 万元',
            '预计年分红 (元)': '¥{:,.0f}'
        }))

# ==========================================
# 模块 2: 缓冲池与现金流模拟
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
    
    # 当月收到分红柱状图
    fig.add_trace(go.Bar(
        x=timeline_df['模拟月份'], 
        y=timeline_df['当月收到分红 (元)'],
        name='当月分红到账额 (元)',
        marker_color='#3B82F6',
        opacity=0.8
    ))
    
    fig.update_layout(
        title="缓冲池水位 (折线) 与 分红到账节奏 (柱状) 动态趋势图",
        xaxis_title="模拟时间线",
        yaxis_title="金额 (元)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#E2E8F0',
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示详细数据表
    with st.expander("📂 查看36个月现金流流转明细表格"):
        st.dataframe(timeline_df.style.format({
            '当月收到分红 (元)': '¥{:,.0f}',
            '当月利息收益 (元)': '¥{:,.2f}',
            '缓冲池余额 (元)': '¥{:,.0f}',
            '固定生活费流出 (元)': '¥{:,.0f}'
        }))

# ==========================================
# 模块 3: 估值温度计与建仓建议
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
    st.table(pd.DataFrame(rec_data))
    
    # 绘制指数历史股息率图表
    fig_idx = go.Figure()
    fig_idx.add_trace(go.Scatter(
        x=history_dates, 
        y=base_yield, 
        mode='lines', 
        name='历史股息率 (%)',
        line=dict(color='#3B82F6', width=2)
    ))
    # 添加当前红线
    fig_idx.add_trace(go.Scatter(
        x=[history_dates[0], history_dates[-1]], 
        y=[current_idx_yield, current_idx_yield],
        mode='lines',
        name='当前股息率水平',
        line=dict(color=color, dash='dash', width=2)
    ))
    
    fig_idx.update_layout(
        title="中证红利低波动指数历史股息率变化趋势 (过去4年)",
        xaxis_title="日期",
        yaxis_title="股息率 (%)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#E2E8F0'
    )
    st.plotly_chart(fig_idx, use_container_width=True)

# ==========================================
# 模块 4: 资产记账与年度平衡
# ==========================================
elif menu == "4. 资产记账与年度平衡":
    st.markdown("<h1 style='color:#FFFFFF; margin-bottom:10px;'>⚖️ 个人持仓账本与资产再平衡</h1>", unsafe_allow_html=True)
    st.write("长期运行中，各资产随市价涨跌，其权重会偏离预定的目标比例。一般建议**每年年底**检查一次，对偏离度较大的资产进行买卖纠偏。")
    
    st.markdown("### 📝 输入您的当前持仓市值")
    st.write("请在下方输入您目前在每只基金和个股的实际持仓市值（单位：万元），系统将自动帮您测算再平衡方案。")
    
    user_values = {}
    cols_ledger = st.columns(4)
    
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
            val = st.number_input(
                f"{info['name']} (万元)", 
                min_value=0.0, 
                max_value=1000.0, 
                value=mock_values.get(code, 0.0), 
                step=1.0, 
                key=f"hold_{code}"
            )
            user_values[code] = val
        idx += 1
        
    # 计算当前持仓市值和偏离度
    total_hold_val = sum(user_values.values())
    
    if total_hold_val <= 0:
        st.warning("请输入您当期的持仓数据以进行再平衡测算。")
    else:
        st.markdown("### 📊 再平衡操作指导")
        st.write(f"当前投资组合总市值为 **{total_hold_val:.2f}** 万元 (不含缓冲池现金)。")
        
        rebalance_rows = []
        for code, info in DEFAULT_ASSETS.items():
            target_pct = info['weight'] / 100.0
            actual_pct = user_values[code] / total_hold_val
            diff_pct = actual_pct - target_pct
            
            # 计算应持持仓和差额
            ideal_value = total_hold_val * target_pct
            adjust_value = ideal_value - user_values[code] # 正数代表应买入，负数代表应卖出
            
            action = "持平"
            if adjust_value > 0.5:
                action = f"🟢 买入 {adjust_value:.2f} 万元"
            elif adjust_value < -0.5:
                action = f"🔴 卖出 {-adjust_value:.2f} 万元"
                
            rebalance_rows.append({
                '证券名称': info['name'],
                '目标比例': f"{info['weight']:.1f}%",
                '实际比例': f"{actual_pct*100:.1f}%",
                '偏离度': f"{diff_pct*100:+.1f}%",
                '当前持仓': f"{user_values[code]:.2f} 万元",
                '合理目标持仓': f"{ideal_value:.2f} 万元",
                '再平衡操作建议': action
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



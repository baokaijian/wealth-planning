import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

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
    ["1. 资产配置与股息看板", "2. 缓冲池与现金流模拟", "3. 估值温度计与建仓建议", "4. 资产记账与年度平衡"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 基本配置参数")
principal = st.sidebar.number_input("您的可用总本金 (万元)", min_value=10.0, max_value=5000.0, value=400.0, step=10.0)
target_monthly = st.sidebar.number_input("期望月现金流 (万元)", min_value=0.1, max_value=50.0, value=2.0, step=0.5)
buffer_seed = st.sidebar.number_input("现金缓冲池初始资金 (万元)", min_value=0.0, max_value=100.0, value=12.0, step=1.0)
money_market_rate = st.sidebar.slider("缓冲池闲置资金年化收益 (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1) / 100

st.sidebar.markdown("""
<div style='margin-top:20px; padding:15px; border-radius:8px; background:rgba(255,255,255,0.05); font-size:0.8rem; color:#94A3B8;'>
    <strong>💡 现金缓冲池提示</strong><br>
    分红到账时间存在不均衡性，缓冲池能平滑淡季与旺季的现金流，确保每月可稳定提取固定生活费。
</div>
""", unsafe_allow_html=True)

# 实际投资金额为总本金减去缓冲池初始储备
invest_principal = max(principal - buffer_seed, 0.0)

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
    st.write("大多数分红在 5-8 月密集派发。本模拟器展示了分红按真实月份归集到缓冲池，并每月固定流出 2 万元生活费的 36 个月动态过程。")
    
    # 1. 整理各资产分红月份和比例
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
    
    # 缓冲池余额期末值折线图
    fig.add_trace(go.Scatter(
        x=timeline_df['模拟月份'], 
        y=timeline_df['缓冲池余额 (元)'],
        mode='lines+markers',
        name='缓冲池余额 (元)',
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
    history_dates = pd.date_range(end="2026-06-14", periods=200, freq="W")
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
    base_dca = st.number_input("您的基础月定投金额 (万元)", min_value=1.0, max_value=200.0, value=32.3, step=1.0)
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
    # 预设一组带有偏离的模拟市值
    mock_values = {
        '512890': 78.0,
        '515450': 50.0,
        '513530': 65.0,
        '600941': 42.0,
        '600900': 35.0,
        '601398': 38.0,
        '601088': 44.0,
        '601668': 36.0
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

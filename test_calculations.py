import math

def calculate_goal_projection(
    current_year,
    target_year,
    target_amount,
    monthly_surplus,
    growth_rate,
    current_principal,
    reserved_amount=0,
    safe_rate=0.02
):
    years = max(1, target_year - current_year)
    months = years * 12
    monthly_rate = growth_rate / 12.0
    
    # 1. 当前本金复利终值
    fv_principal = current_principal * ((1 + growth_rate) ** years)
    
    # 2. 月结余定投复利终值 (期初年金)
    if monthly_rate > 0:
        fv_monthly = monthly_surplus * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        fv_monthly = monthly_surplus * months
        
    # 3. 单独预留金额终值 (按安全收益率计息)
    fv_reserved = reserved_amount * ((1 + safe_rate) ** years)
    
    fv_total = fv_principal + fv_monthly + fv_reserved
    diff = fv_total - target_amount
    gap = max(0, -diff)
    
    levers = None
    if gap > 0:
        # 杠杆 1: 每月需多储蓄 X 元
        if monthly_rate > 0:
            annuity_factor = (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
            extra_monthly = math.ceil(gap / annuity_factor)
        else:
            extra_monthly = math.ceil(gap / months)
            
        # 杠杆 2: 收益率需提升 Y 个百分点
        low = growth_rate
        high = 1.0  # 100%
        r_req = None
        for _ in range(100):
            mid = (low + high) / 2.0
            mid_monthly_rate = mid / 12.0
            mid_fv_p = current_principal * ((1 + mid) ** years)
            if mid_monthly_rate > 0:
                mid_fv_m = monthly_surplus * (((1 + mid_monthly_rate) ** months - 1) / mid_monthly_rate) * (1 + mid_monthly_rate)
            else:
                mid_fv_m = monthly_surplus * months
            mid_total = mid_fv_p + mid_fv_m + fv_reserved
            if abs(mid_total - target_amount) < 1.0:
                r_req = mid
                break
            elif mid_total < target_amount:
                low = mid
            else:
                high = mid
        if r_req is None:
            r_req = high
        rate_diff_pct = (r_req - growth_rate) * 100.0
        is_rate_safe = r_req <= 0.08
        
        # 杠杆 3: 目标金额放宽 或 时点需延后几年
        loosen_amount = gap
        delay_years = None
        for extra_y in range(1, 31):
            cur_y = years + extra_y
            cur_m = cur_y * 12
            cur_fv_p = current_principal * ((1 + growth_rate) ** cur_y)
            if monthly_rate > 0:
                cur_fv_m = monthly_surplus * (((1 + monthly_rate) ** cur_m - 1) / monthly_rate) * (1 + monthly_rate)
            else:
                cur_fv_m = monthly_surplus * cur_m
            cur_fv_r = reserved_amount * ((1 + safe_rate) ** cur_y)
            if (cur_fv_p + cur_fv_m + cur_fv_r) >= target_amount:
                delay_years = extra_y
                break
                
        levers = {
            'extra_monthly': extra_monthly,
            'req_rate': round(r_req * 100, 2),
            'rate_diff_pct': round(rate_diff_pct, 2),
            'is_rate_safe': is_rate_safe,
            'loosen_amount': loosen_amount,
            'delay_years': delay_years if delay_years else 30,
            'delayed_target_year': (target_year + delay_years) if delay_years else (target_year + 30)
        }
        
    return {
        'years': years,
        'months': months,
        'fv_principal': fv_principal,
        'fv_monthly': fv_monthly,
        'fv_reserved': fv_reserved,
        'fv_total': fv_total,
        'diff': diff,
        'is_achieved': diff >= 0,
        'gap': gap,
        'levers': levers
    }

def simulate_early_retirement(
    current_age=35,
    retire_age=50,
    target_amount=2000000,
    projected_capital_at_retire=None,
    monthly_expense=10000,
    dividend_yield=0.048,
    buffer_interest_rate=0.02,
    end_age=85
):
    total_years = max(1, end_age - retire_age)
    total_months = total_years * 12
    capital = projected_capital_at_retire if (projected_capital_at_retire and projected_capital_at_retire > 0) else target_amount
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
        
        div_weight = seasonality.get(cal_month, 1.0 / 12.0)
        monthly_div = capital * dividend_yield * div_weight
        monthly_interest = max(0, capital) * (buffer_interest_rate / 12.0)
        
        capital = capital + monthly_div + monthly_interest - monthly_expense
        
        if capital < lowest_capital:
            lowest_capital = capital
            most_fragile_month = m
            
        if capital <= 0 and depletion_month is None:
            depletion_month = m
            depletion_age = round(curr_age, 1)
            
    is_sustainable = depletion_month is None
    return {
        'total_years': total_years,
        'total_months': total_months,
        'is_sustainable': is_sustainable,
        'final_capital': capital,
        'depletion_age': depletion_age,
        'depletion_month': depletion_month,
        'lowest_capital': lowest_capital,
        'most_fragile_month': most_fragile_month,
        'most_fragile_age': round(retire_age + (most_fragile_month - 1) / 12.0, 1)
    }

def calculate_debt_decision_metrics(
    debt_bracket='4.5-6%',
    custom_debt_rate=None,
    high_interest_balance=0,
    growth_rate=6.5,
    conservative_yield_override=None,
    available_fund_x=200000
):
    bracket_medians = {
        '<3.5%': 3.0,
        '3.5-4.5%': 4.0,
        '4.5-6%': 5.25,
        '>6%': 7.2
    }
    
    bracket_median = bracket_medians.get(debt_bracket, 5.25)
    effective_debt_rate = custom_debt_rate if (custom_debt_rate is not None and custom_debt_rate > 0) else bracket_median
    
    if conservative_yield_override is not None:
        conservative_yield = conservative_yield_override
    else:
        conservative_yield = round(growth_rate * 0.7, 2)
        
    if effective_debt_rate > (conservative_yield + 2.0):
        decision_text = "优先清偿高息债务（相当于获得无风险的利差收益）"
        decision_type = "repay_first"
    elif effective_debt_rate < (conservative_yield - 2.0):
        decision_text = "保持贷款、优先投资，但需确认现金流稳定性"
        decision_type = "invest_first"
    else:
        decision_text = "两者皆可，优先级取决于风险偏好与流动性需求"
        decision_type = "neutral"
        
    has_high_interest_alert = (high_interest_balance > 0) or (debt_bracket == '>6%') or (effective_debt_rate > 6.0)
    
    r_debt = effective_debt_rate / 100.0
    r_invest = conservative_yield / 100.0
    
    table = []
    for years in [3, 5, 10]:
        fv_repay = available_fund_x * ((1 + r_debt) ** years)
        fv_invest = available_fund_x * ((1 + r_invest) ** years)
        diff = fv_repay - fv_invest
        table.append({
            'years': years,
            'fv_repay': round(fv_repay, 2),
            'fv_invest': round(fv_invest, 2),
            'diff': round(diff, 2),
            'advantage': '提前还贷更优' if diff > 0 else ('坚持投资更优' if diff < 0 else '持平')
        })
        
    return {
        'debt_bracket': debt_bracket,
        'bracket_median': bracket_median,
        'effective_debt_rate': effective_debt_rate,
        'growth_rate': growth_rate,
        'conservative_yield': conservative_yield,
        'decision_text': decision_text,
        'decision_type': decision_type,
        'has_high_interest_alert': has_high_interest_alert,
        'available_fund_x': available_fund_x,
        'comparison_table': table
    }

# 1. 保障缺口测算
def calculate_insurance_gap(
    monthly_income=30000,
    essential_monthly_expense=12000,
    child_edu_target=500000,
    liquid_assets=950000,
    total_debt=800000,
    existing_life=500000,
    existing_crit=200000,
    existing_accident=500000,
    has_million_medical=False,
    stability_tier='medium',
    coverage_tier='insufficient'
):
    stability_map = {
        'high': {'years': 3, 'medical': 300000},
        'medium': {'years': 4, 'medical': 400000},
        'low': {'years': 5, 'medical': 500000}
    }
    annual_income = monthly_income * 12
    future_10y_expense = essential_monthly_expense * 120

    life_target = max(0, total_debt + future_10y_expense + child_edu_target - liquid_assets)
    life_gap = max(0, life_target - existing_life)
    life_mult = round(life_gap / annual_income, 1) if annual_income > 0 else 0

    cfg = stability_map.get(stability_tier, stability_map['medium'])
    crit_target = cfg['years'] * annual_income + cfg['medical']
    crit_gap = max(0, crit_target - existing_crit)
    crit_mult = round(crit_gap / annual_income, 1) if annual_income > 0 else 0

    accident_target = round(life_target * 0.5)
    accident_gap = max(0, accident_target - existing_accident)
    accident_mult = round(accident_gap / annual_income, 1) if annual_income > 0 else 0

    has_net_gap = (life_gap > 0) or (crit_gap > 0) or (accident_gap > 0) or (not has_million_medical)
    should_warn_downgrade = (coverage_tier in ['none', 'insufficient']) and has_net_gap

    return {
        'life_target': life_target,
        'life_gap': life_gap,
        'life_mult': life_mult,
        'crit_target': crit_target,
        'crit_gap': crit_gap,
        'crit_mult': crit_mult,
        'accident_target': accident_target,
        'accident_gap': accident_gap,
        'accident_mult': accident_mult,
        'has_million_medical': has_million_medical,
        'should_warn_downgrade': should_warn_downgrade
    }

# 4. 个人养老金税优测算
def calculate_pension_tax_benefit(has_account=True, current_year_deposited=4000, marginal_tax_rate=0.20):
    deposited = min(12000, max(0, current_year_deposited))
    remaining = max(0, 12000 - deposited)
    annual_tax_saved = round(remaining * marginal_tax_rate)
    cumulative_20y = annual_tax_saved * 20
    is_tax_limited = marginal_tax_rate <= 0.001
    return {
        'has_account': has_account,
        'deposited': deposited,
        'remaining': remaining,
        'annual_tax_saved': annual_tax_saved,
        'cumulative_20y': cumulative_20y,
        'is_tax_limited': is_tax_limited
    }

# 5. 房产集中度与首付核验
def calculate_real_estate_risk(
    property_val=2800000,
    mortgage=800000,
    financial_assets=950000,
    other_debt=0,
    has_house_plan=False,
    expected_down_payment=600000,
    bucket1y=100000,
    bucket1_3y=150000,
    stress_drop_pct=20
):
    property_net = max(0, property_val - mortgage)
    total_assets = property_val + financial_assets
    total_debt = mortgage + other_debt
    total_net_worth = max(1, total_assets - total_debt)
    ratio = round((property_net / total_net_worth) * 100, 1)

    tier = 'green'
    if ratio > 75:
        tier = 'red'
    elif ratio >= 60:
        tier = 'yellow'

    ready_funds = bucket1y + bucket1_3y
    down_payment_gap = max(0, expected_down_payment - ready_funds)
    is_down_payment_short = has_house_plan and (down_payment_gap > 0)

    stress_prop_val = property_val * (1 - stress_drop_pct / 100.0)
    stress_total_assets = stress_prop_val + financial_assets
    stress_net_worth = max(0, stress_total_assets - total_debt)
    normal_d_to_a = round((total_debt / total_assets) * 100, 1)
    stress_d_to_a = round((total_debt / stress_total_assets) * 100, 1)

    return {
        'property_net': property_net,
        'total_net_worth': total_net_worth,
        'ratio': ratio,
        'tier': tier,
        'is_down_payment_short': is_down_payment_short,
        'down_payment_gap': down_payment_gap,
        'stress_net_worth': stress_net_worth,
        'normal_d_to_a': normal_d_to_a,
        'stress_d_to_a': stress_d_to_a
    }

# 9. 流动性硬隔离校验
def check_liquidity_segregation(
    bucket1y=100000,
    bucket1_3y=150000,
    bucket3_5y=200000,
    bucket5y_plus=500000,
    principal_ten_thousand=50,
    discount_factor=0.5
):
    liquid_financial = bucket1y + bucket1_3y + bucket3_5y + bucket5y_plus
    investable_ceiling = max(0, liquid_financial - (bucket1y * 1.0) - (bucket1_3y * discount_factor))
    principal_yuan = principal_ten_thousand * 10000
    is_violated = principal_yuan > investable_ceiling
    excess_amount = max(0, principal_yuan - investable_ceiling)
    short_term_total = bucket1y + bucket1_3y
    coverage_ratio = round(liquid_financial / short_term_total, 2) if short_term_total > 0 else 99.0
    return {
        'liquid_financial': liquid_financial,
        'investable_ceiling': investable_ceiling,
        'principal_yuan': principal_yuan,
        'is_violated': is_violated,
        'excess_amount': excess_amount,
        'coverage_ratio': coverage_ratio,
        'is_coverage_insufficient': coverage_ratio < 1.5
    }

# 7. 行为约束引擎
def calculate_behavioral_equity_ceiling(
    drawdown_bracket='10-20%',
    panic_reaction='panic_sell',
    cashflow_reliance_high=True,
    industry_volatile_high=False,
    actual_equity_weight=75.0
):
    drawdown_map = {'<5%': 20, '5-10%': 35, '10-20%': 55, '20-30%': 70, '>30%': 85}
    base = drawdown_map.get(drawdown_bracket, 55)
    panic_deduction = 15 if panic_reaction == 'panic_sell' else (5 if panic_reaction == 'pause_watch' else 0)
    cashflow_deduction = 10 if cashflow_reliance_high else 0
    industry_deduction = 10 if industry_volatile_high else 0

    raw_ceiling = base - panic_deduction - cashflow_deduction - industry_deduction
    final_ceiling = max(15, raw_ceiling)
    is_exceeded = actual_equity_weight > final_ceiling
    implicit_drawdown = round(final_ceiling * 0.40, 1)

    return {
        'base': base,
        'final_ceiling': final_ceiling,
        'is_exceeded': is_exceeded,
        'excess_weight': max(0, actual_equity_weight - final_ceiling),
        'implicit_drawdown': implicit_drawdown
    }

# 8. 估值温度计
def calculate_thermometer_signal(percentile=85):
    val = min(100, max(0, percentile))
    if val < 20:
        code = 'deep_low'
    elif val < 40:
        code = 'low'
    elif val < 60:
        code = 'neutral'
    elif val < 80:
        code = 'warm'
    else:
        code = 'overheat'
    return {
        'percentile': val,
        'code': code,
        'is_overheated': code == 'overheat',
        'is_deep_low': code == 'deep_low'
    }

# 6. 复合情景压力测试
def run_compound_stress_test(
    principal_ten_thousand=50,
    buffer_seed_ten_thousand=5,
    target_monthly_ten_thousand=0.2,
    money_market_rate=0.02,
    unemployment_months=12,
    dividend_drop_rate=0.50,
    equity_drawdown_rate=0.35,
    medical_expense=200000,
    medical_month=6,
    delay_months=0,
    inflation_rate=0.0,
    months_range=36
):
    invest_principal = max(0, principal_ten_thousand - buffer_seed_ten_thousand) * 10000
    target_withdraw = target_monthly_ten_thousand * 10000
    current_buffer = buffer_seed_ten_thousand * 10000
    exhaustion_month = None
    max_deficit = 0
    min_buffer = current_buffer

    # 简化派息模型：年均股息率 4.8%，7月集中派息 50%，12月 50%
    for t in range(1, months_range + 1):
        cal_m = ((t - 1) % 12) + 1
        # 通胀
        m_withdraw = target_withdraw * ((1 + inflation_rate / 12.0) ** t)
        extra_outflow = medical_expense if (medical_expense > 0 and t == medical_month) else 0

        # 分红
        month_div = 0
        eff_cal_m = ((((cal_m - 1 - delay_months) % 12) + 12) % 12) + 1
        if eff_cal_m in [7, 12]:
            month_div = invest_principal * 0.048 * 0.5 * (1 - dividend_drop_rate)

        interest = max(0, current_buffer) * (money_market_rate / 12.0)
        next_buffer = current_buffer + month_div + interest - m_withdraw - extra_outflow

        if current_buffer < min_buffer:
            min_buffer = current_buffer
        if next_buffer < 0 and exhaustion_month is None:
            exhaustion_month = t
        if next_buffer < 0 and abs(next_buffer) > max_deficit:
            max_deficit = abs(next_buffer)

        current_buffer = next_buffer

    discount_mult = max(0.1, 1 - equity_drawdown_rate)
    min_asset_to_sell = round(max_deficit / discount_mult) if exhaustion_month else 0

    return {
        'exhaustion_month': exhaustion_month,
        'is_exhausted': exhaustion_month is not None,
        'min_buffer': round(min_buffer),
        'max_deficit': round(max_deficit),
        'min_asset_to_sell': min_asset_to_sell
    }

# 10. 三重集中度检查
def check_triple_concentration(assets):
    asset_list = []
    for code, item in assets.items():
        asset_list.append({
            'code': code,
            'name': item.get('name', ''),
            'weight': item.get('weight', 0),
            'market': item.get('market', 'A股'),
            'style': item.get('style', '其他')
        })

    # 1. 标的集中度
    sorted_assets = sorted(asset_list, key=lambda x: x['weight'], reverse=True)
    max_single = sorted_assets[0] if sorted_assets else {'name': '无', 'weight': 0}
    top3_weight = sum(a['weight'] for a in sorted_assets[:3])

    target_status = 'green'
    if top3_weight > 70:
        target_status = 'red'
    elif max_single['weight'] > 40:
        target_status = 'yellow'

    # 2. 市场集中度
    market_sums = {}
    for a in asset_list:
        m = a['market']
        market_sums[m] = market_sums.get(m, 0) + a['weight']
    max_market = max(market_sums.items(), key=lambda x: x[1]) if market_sums else ('A股', 0)
    market_status = 'yellow' if max_market[1] > 60 else 'green'

    # 3. 风格集中度 (红利低波)
    dividend_style_weight = sum(a['weight'] for a in asset_list if a['style'] == '红利低波')
    style_status = 'yellow' if dividend_style_weight > 50 else 'green'

    return {
        'target_status': target_status,
        'max_single': max_single,
        'top3_weight': top3_weight,
        'market_status': market_status,
        'max_market': max_market,
        'style_status': style_status,
        'dividend_style_weight': dividend_style_weight
    }

# 11. 评分可解释化与统一风险仪表盘
def calculate_explainable_scores(
    has_high_debt=False,
    debt_balance=0,
    is_liq_violated=False,
    is_coverage_insufficient=False,
    has_ins_downgrade=False,
    has_ins_gap=False,
    is_buf_unsafe=False,
    min_buf=50000,
    equity_weight=50.0,
    growth_rate=6.5,
    is_beh_exceeded=False,
    beh_excess_weight=0.0
):
    debt_score = 30 if has_high_debt else (20 if debt_balance > 1000000 else (10 if debt_balance > 0 else 0))
    liq_score = 30 if is_liq_violated else (18 if is_coverage_insufficient else 5)
    ins_score = 25 if has_ins_downgrade else (15 if has_ins_gap else 0)
    buf_score = 15 if is_buf_unsafe else (8 if min_buf < 20000 else 0)
    total_vuln = debt_score + liq_score + ins_score + buf_score

    eq_score = min(40, round((equity_weight / 100.0) * 40))
    g_score = min(30, round((max(0, growth_rate - 3.0) / 7.0) * 30))
    beh_score = min(30, round(beh_excess_weight * 1.5)) if is_beh_exceeded else 5
    total_agg = min(100, eq_score + g_score + beh_score)

    return {
        'total_vulnerability': total_vuln,
        'vulnerability_level': '高危脆弱' if total_vuln > 60 else ('中度脆弱' if total_vuln > 35 else '稳健安全'),
        'total_aggressiveness': total_agg,
        'aggressiveness_level': '激进进攻' if total_agg > 70 else ('平衡进取' if total_agg > 40 else '谨慎保守')
    }

def calculate_unified_risk_dashboard(red_count, yellow_count):
    overall = '高风险' if red_count > 0 else ('关注' if yellow_count > 1 else '健康')
    return {
        'red_count': red_count,
        'yellow_count': yellow_count,
        'overall_health': overall
    }

def run_all_unit_tests():
    print("=== 开始运行纯函数单元测试 ===")
    
    # 1. 保障缺口测试
    # 负债 80万, 生活费底线 12000/月 (10年120个月: 144万), 教育 50万, 流动资产 95万
    # 寿险责任 = 80 + 144 + 50 - 95 = 179万; 已有 50万 -> 净缺口 129万
    ins = calculate_insurance_gap(
        monthly_income=30000,
        essential_monthly_expense=12000,
        child_edu_target=500000,
        liquid_assets=950000,
        total_debt=800000,
        existing_life=500000,
        coverage_tier='insufficient'
    )
    assert ins['life_target'] == 1790000, f"寿险总责任期望 179万, 实际 {ins['life_target']}"
    assert ins['life_gap'] == 1290000, f"寿险净缺口期望 129万, 实际 {ins['life_gap']}"
    assert ins['should_warn_downgrade'] is True, "自评不足且有缺口应触发降级警告"
    print("✅ 保障缺口测算单元测试通过！")

    # 4. 养老金税优测试
    pen = calculate_pension_tax_benefit(has_account=True, current_year_deposited=4000, marginal_tax_rate=0.20)
    assert pen['remaining'] == 8000, "剩余额度应为 8000"
    assert pen['annual_tax_saved'] == 1600, "年放弃税优应为 1600"
    assert pen['cumulative_20y'] == 32000, "20年累计应为 32000"
    print("✅ 个人养老金税优单元测试通过！")

    # 5. 房产集中度测试
    re = calculate_real_estate_risk(
        property_val=2800000,
        mortgage=800000,
        financial_assets=950000,
        has_house_plan=True,
        expected_down_payment=600000,
        bucket1y=100000,
        bucket1_3y=150000
    )
    # 房产净值 200万, 金融资产 95万, 总净资产 295万 -> 比例 200/295 = 67.8% -> 黄色
    assert re['property_net'] == 2000000
    assert re['tier'] == 'yellow'
    assert re['is_down_payment_short'] is True, "可用 25万 < 首付 60万 应提示缺口"
    print("✅ 房产集中度与首付核验单元测试通过！")

    # 9. 流动性硬隔离测试
    # 流动金融资产 95万 (10+15+20+50), 12m=10万, 1-3y=15万 (折减50%=7.5万)
    # 可投资上限 = 95 - 10 - 7.5 = 77.5 万元
    liq = check_liquidity_segregation(
        bucket1y=100000,
        bucket1_3y=150000,
        bucket3_5y=200000,
        bucket5y_plus=500000,
        principal_ten_thousand=80
    )
    assert liq['investable_ceiling'] == 775000, f"期望上限 77.5万, 实际 {liq['investable_ceiling']}"
    assert liq['is_violated'] is True, "80万本金超出77.5万上限应标红超限"
    print("✅ 流动性硬隔离单元测试通过！")

    # 7. 行为约束引擎测试
    beh = calculate_behavioral_equity_ceiling(
        drawdown_bracket='10-20%',
        panic_reaction='panic_sell',
        cashflow_reliance_high=True,
        industry_volatile_high=False,
        actual_equity_weight=50.0
    )
    # 基础 55% - 恐慌 15% - 现金流 10% = 30%
    assert beh['final_ceiling'] == 30, f"期望行为约束上限 30%, 实际 {beh['final_ceiling']}"
    assert beh['is_exceeded'] is True, "实际 50% 超出上限 30% 应报警"
    print("✅ 行为约束引擎单元测试通过！")

    # 8. 估值温度计测试
    therm = calculate_thermometer_signal(percentile=85)
    assert therm['is_overheated'] is True, "85% 百分位应处于过热状态"
    print("✅ 估值温度计单元测试通过！")

    # 6. 复合压力测试测试
    stress = run_compound_stress_test(
        principal_ten_thousand=50,
        buffer_seed_ten_thousand=5,
        target_monthly_ten_thousand=0.2,
        unemployment_months=12,
        dividend_drop_rate=0.50,
        equity_drawdown_rate=0.35,
        medical_expense=200000,
        medical_month=6
    )
    assert stress['is_exhausted'] is True, "严重复合情景下缓冲池应出现枯竭"
    assert stress['min_asset_to_sell'] > 0, "枯竭时需变现资产必须大于0"
    print(f"  • 严重复合情景枯竭月份: 第 {stress['exhaustion_month']} 个月, 需折价变现资产: ¥{stress['min_asset_to_sell']:,} 元")
    print("✅ 复合压力测试推演单元测试通过！")

if __name__ == "__main__":
    run_all_unit_tests()

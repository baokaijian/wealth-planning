# test_calculations.py
import math

def calculate_board_metrics(principal, buffer_seed, target_monthly, growth_rate, assets):
    invest_principal = max(0, principal - buffer_seed)
    total_weight = 0
    blended_yield = 0
    for a in assets.values():
        w = a.get('weight', 0) / 100.0
        y = a.get('yield', 0) / 100.0
        total_weight += w
        blended_yield += w * y
    expected_annual_dividend = invest_principal * blended_yield * 10000
    expected_monthly_avg = expected_annual_dividend / 12.0
    target_monthly_yuan = target_monthly * 10000
    gap_monthly = target_monthly_yuan - expected_monthly_avg
    return {
        'invest_principal': invest_principal,
        'total_weight': round(total_weight * 100, 2),
        'blended_yield': round(blended_yield * 100, 2),
        'growth_rate': growth_rate,
        'expected_annual_dividend': round(expected_annual_dividend, 2),
        'expected_monthly_avg': round(expected_monthly_avg, 2),
        'target_monthly_yuan': target_monthly_yuan,
        'gap_monthly': round(gap_monthly, 2),
        'is_weight_valid': abs(total_weight - 1.0) < 0.001
    }

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
    r_annual = growth_rate / 100.0 if growth_rate > 1 else growth_rate
    monthly_rate = r_annual / 12.0

    fv_principal = current_principal * ((1 + r_annual) ** years)
    if monthly_rate > 0:
        fv_monthly = monthly_surplus * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        fv_monthly = monthly_surplus * months
    fv_reserved = reserved_amount * ((1 + safe_rate) ** years)
    fv_total = fv_principal + fv_monthly + fv_reserved
    diff = fv_total - target_amount
    gap = max(0, -diff)

    levers = None
    if gap > 0:
        if monthly_rate > 0:
            annuity_factor = (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
            extra_monthly = math.ceil(gap / annuity_factor)
        else:
            extra_monthly = math.ceil(gap / months)

        low = r_annual
        high = 1.0
        r_req = high
        for _ in range(100):
            mid = (low + high) / 2.0
            mid_m = mid / 12.0
            mid_p = current_principal * ((1 + mid) ** years)
            mid_m_fv = monthly_surplus * (((1 + mid_m) ** months - 1) / mid_m) * (1 + mid_m) if mid_m > 0 else monthly_surplus * months
            if (mid_p + mid_m_fv + fv_reserved) >= target_amount:
                r_req = mid
                high = mid
            else:
                low = mid
        rate_diff_pct = (r_req - r_annual) * 100.0
        is_rate_safe = r_req <= 0.08

        loosen_amount = gap
        delay_years = None
        for dy in range(1, 31):
            cy = years + dy
            cm = cy * 12
            cp = current_principal * ((1 + r_annual) ** cy)
            cm_fv = monthly_surplus * (((1 + monthly_rate) ** cm - 1) / monthly_rate) * (1 + monthly_rate) if monthly_rate > 0 else monthly_surplus * cm
            cr = reserved_amount * ((1 + safe_rate) ** cy)
            if (cp + cm_fv + cr) >= target_amount:
                delay_years = dy
                break

        levers = {
            'extra_monthly': extra_monthly,
            'req_rate_pct': round(r_req * 100, 2),
            'rate_diff_pct': round(rate_diff_pct, 2),
            'is_rate_safe': is_rate_safe,
            'loosen_amount': loosen_amount,
            'delay_years': delay_years if delay_years else 30,
            'delayed_target_year': (target_year + (delay_years if delay_years else 30))
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

def calculate_multi_goal_projections(goals, total_investable_principal=800000, total_monthly_surplus=12000, growth_rate=6.5, safe_rate=0.02):
    sorted_goals = sorted(
        [dict(g, original_idx=i) for i, g in enumerate(goals)],
        key=lambda x: (0 if x.get('priority') == '刚性' else 1, x.get('targetYear', 2030))
    )

    remaining_p = total_investable_principal
    remaining_s = total_monthly_surplus
    results = []
    total_alloc_p = 0
    total_alloc_s = 0

    r_annual = growth_rate / 100.0 if growth_rate > 1 else growth_rate
    r_monthly = r_annual / 12.0

    for g in sorted_goals:
        years = max(1, g.get('targetYear', 2030) - 2026)
        months = years * 12
        reserved = g.get('reservedAmount', 0)
        fv_res = reserved * ((1 + safe_rate) ** years)
        net_needed = max(0, g.get('targetAmount', 0) - fv_res)

        alloc_p = 0
        if remaining_p > 0 and net_needed > 0:
            p_needed = net_needed / ((1 + r_annual) ** years)
            alloc_p = min(remaining_p, math.floor(p_needed * 0.5))

        fv_p = alloc_p * ((1 + r_annual) ** years)
        rem_need = max(0, net_needed - fv_p)

        alloc_s = 0
        if remaining_s > 0 and rem_need > 0:
            annuity = (((1 + r_monthly) ** months - 1) / r_monthly) * (1 + r_monthly) if r_monthly > 0 else months
            s_needed = math.ceil(rem_need / annuity)
            alloc_s = min(remaining_s, s_needed)

        remaining_p -= alloc_p
        remaining_s -= alloc_s
        total_alloc_p += alloc_p
        total_alloc_s += alloc_s

        proj = calculate_goal_projection(
            current_year=2026,
            target_year=g.get('targetYear', 2030),
            target_amount=g.get('targetAmount', 0),
            monthly_surplus=alloc_s,
            growth_rate=growth_rate,
            current_principal=alloc_p,
            reserved_amount=reserved,
            safe_rate=safe_rate
        )

        results.append({
            **g,
            'allocated_principal': alloc_p,
            'allocated_surplus': alloc_s,
            'projection': proj
        })

    results.sort(key=lambda x: x['original_idx'])
    return {
        'goal_results': results,
        'remaining_principal': remaining_p,
        'remaining_surplus': remaining_s,
        'total_allocated_principal': total_alloc_p,
        'total_allocated_surplus': total_alloc_s,
        'is_resource_crowded_out': remaining_p <= 0 or remaining_s <= 0
    }

def calculate_debt_decision_metrics(debt_state, growth_rate=6.5):
    brackets = {
        '<3.5%': 3.0,
        '3.5-4.5%': 4.0,
        '4.5-6%': 5.25,
        '>6%': 7.2
    }
    bracket = debt_state.get('debtRateBracket', '3.5-4.5%')
    bracket_median = brackets.get(bracket, 4.0)

    use_custom = debt_state.get('useCustomRate', False) and (debt_state.get('customDebtRate') is not None) and (debt_state.get('customDebtRate') > 0)
    effective_rate = debt_state['customDebtRate'] if use_custom else bracket_median
    rate_source = f"用户自定义 ({effective_rate}%)" if use_custom else f"档位中值估算 ({bracket}: {effective_rate}%)"

    conservative_yield = round(growth_rate * 0.70, 2)
    # P1-4: spread = conservative_yield - effective_rate
    spread = round(conservative_yield - effective_rate, 2)
    spread_label = '正利差 (投资回报高于借贷成本)' if spread > 0 else '负利差 (借贷成本高于投资保守预期)'

    if spread < -2.0:
        decision_type = 'repay_first'
        decision_text = '优先清偿债务（获得确定性无风险利差收益，有效阻断利息损耗）'
    elif spread > 2.0:
        decision_type = 'invest_first'
        decision_text = '保持贷款、优先投资（正利差显著，但需维持现金流稳定与应急储备）'
    else:
        decision_type = 'balanced'
        decision_text = '平衡兼顾：按既定计划偿还月供，余钱稳健定投积累核心资产'

    total_debt = (debt_state.get('mortgageBalance', 0) +
                  debt_state.get('carLoanBalance', 0) +
                  debt_state.get('consumerLoanBalance', 0) +
                  debt_state.get('businessLoanBalance', 0))

    has_high_debt = (debt_state.get('highInterestDebtBalance', 0) > 0) or (effective_rate > 6.0)

    fund_x = debt_state.get('availableFundX', 200000)
    comp_table = []
    for y in [1, 3, 5, 10, 15]:
        fv_repay = fund_x * ((1 + effective_rate / 100.0) ** y)
        fv_invest = fund_x * ((1 + conservative_yield / 100.0) ** y)
        diff = fv_repay - fv_invest
        comp_table.append({
            'years': y,
            'fund_x': fund_x,
            'fv_repay': round(fv_repay),
            'fv_invest': round(fv_invest),
            'diff': round(diff),
            'advantage': '提前还贷占优' if diff > 1 else ('坚持投资更优' if diff < -1 else '两者基本持平')
        })

    return {
        'bracket': bracket,
        'effective_rate': effective_rate,
        'is_using_custom': use_custom,
        'rate_source': rate_source,
        'growth_rate': growth_rate,
        'conservative_yield': conservative_yield,
        'spread': spread,
        'spread_label': spread_label,
        'decision_type': decision_type,
        'decision_text': decision_text,
        'total_debt': total_debt,
        'has_high_debt': has_high_debt,
        'remaining_years': debt_state.get('remainingYears', 15),
        'comparison_table': comp_table
    }

def calculate_insurance_gap(health_state, insurance_state, total_debt_balance):
    monthly_income = health_state.get('monthlyIncome', 30000)
    annual_income = monthly_income * 12
    essential_monthly = health_state.get('essentialMonthlyExpense', 12000)
    future_10y = essential_monthly * 120

    # P1-2: 寿险扣除高流动性现金 (现金活期 + 货基短债)
    breakdown = health_state.get('assetsBreakdown', {})
    high_liquid = breakdown.get('cashCurrent', 100000) + breakdown.get('cashShortDebt', 200000)

    child_edu = insurance_state.get('childEduTarget', 500000)
    life_target = max(0, total_debt_balance + future_10y + child_edu - high_liquid)
    existing_life = insurance_state.get('existingLifeCover', 0)
    life_gap = max(0, life_target - existing_life)

    stab_map = {
        'high': (3, 300000),
        'medium': (4, 400000),
        'low': (5, 500000)
    }
    stab_key = insurance_state.get('stabilityTier', 'medium')
    stab_years, stab_med = stab_map.get(stab_key, (4, 400000))
    crit_target = stab_years * annual_income + stab_med
    existing_crit = insurance_state.get('existingCritCover', 0)
    crit_gap = max(0, crit_target - existing_crit)

    # P1-2: 意外险目标 = 寿险净缺口的 50%
    accident_target = round(life_gap * 0.5)
    existing_accident = insurance_state.get('existingAccidentCover', 0)
    accident_gap = max(0, accident_target - existing_accident)

    has_mil = insurance_state.get('hasMillionMedical', False)
    weak_tier = insurance_state.get('coverageTier') in ['none', 'insufficient']
    should_warn = weak_tier and ((life_gap > 0) or (crit_gap > 0) or (accident_gap > 0) or not has_mil)

    return {
        'high_liquid_deduction': high_liquid,
        'child_edu_target': child_edu,
        'life_target': life_target,
        'life_gap': life_gap,
        'crit_target': crit_target,
        'crit_gap': crit_gap,
        'accident_target': accident_target,
        'accident_gap': accident_gap,
        'has_million_medical': has_mil,
        'should_warn_downgrade': should_warn
    }

def calculate_real_estate_risk(property_state, health_state, debt_state):
    property_val = property_state.get('totalEstimatedValue', 2800000)
    mortgage = debt_state.get('mortgageBalance', 800000)
    financial_debt = (debt_state.get('carLoanBalance', 0) +
                      debt_state.get('consumerLoanBalance', 0) +
                      debt_state.get('businessLoanBalance', 0))
    total_debt = mortgage + financial_debt

    breakdown = health_state.get('assetsBreakdown', {})
    financial_assets = (breakdown.get('cashCurrent', 0) +
                        breakdown.get('cashShortDebt', 0) +
                        breakdown.get('equityAssets', 0) +
                        breakdown.get('goldAssets', 0) +
                        breakdown.get('bondAssets', 0) +
                        breakdown.get('pensionCashValue', 0) +
                        breakdown.get('otherAssets', 0))
    total_assets = property_val + financial_assets
    total_net_worth = total_assets - total_debt
    financial_net_worth = financial_assets - financial_debt

    normal_debt_ratio = round((total_debt / total_assets * 100), 1) if total_assets > 0 else 0
    fin_debt_ratio = round((financial_debt / financial_assets * 100), 1) if financial_assets > 0 else 0
    re_ratio = round(((property_val - mortgage) / total_net_worth * 100), 1) if total_net_worth > 0 else 0

    # 房产下跌 20% 冲击
    drop_pct = property_state.get('stressDropPct', 20)
    stress_drop_amount = property_val * (drop_pct / 100.0)
    stress_total_assets = total_assets - stress_drop_amount
    stress_net_worth = total_net_worth - stress_drop_amount
    stress_debt_ratio = round((total_debt / stress_total_assets * 100), 1) if stress_total_assets > 0 else 0

    return {
        'property_val': property_val,
        'mortgage': mortgage,
        'financial_assets': financial_assets,
        'financial_debt': financial_debt,
        'financial_net_worth': financial_net_worth,
        'financial_debt_ratio': fin_debt_ratio,
        'total_assets': total_assets,
        'total_debt': total_debt,
        'total_net_worth': total_net_worth,
        'normal_debt_ratio': normal_debt_ratio,
        're_ratio': re_ratio,
        'stress_drop_pct': drop_pct,
        'stress_drop_amount': stress_drop_amount,
        'stress_total_assets': stress_total_assets,
        'stress_net_worth': stress_net_worth,
        'stress_debt_ratio': stress_debt_ratio
    }

def check_liquidity_segregation(health_state, principal_ten_thousand=80):
    breakdown = health_state.get('assetsBreakdown', {})
    liquid_fin_assets = (breakdown.get('cashCurrent', 0) +
                         breakdown.get('cashShortDebt', 0) +
                         breakdown.get('equityAssets', 0) +
                         breakdown.get('goldAssets', 0) +
                         breakdown.get('bondAssets', 0) +
                         breakdown.get('otherAssets', 0))
    expenses = health_state.get('expectedExpenses', {})
    exp_1y = expenses.get('expense1y', 100000)
    exp_1to3y = expenses.get('expense1To3y', 150000)

    # 可投资资金上限 = 流动金融资产 - 12m*100% - 1-3y*50%
    investable_ceiling = max(0, liquid_fin_assets - exp_1y * 1.0 - exp_1to3y * 0.5)
    principal_yuan = principal_ten_thousand * 10000
    is_violated = principal_yuan > investable_ceiling
    excess_amount = max(0, principal_yuan - investable_ceiling)

    short_expenses = exp_1y + exp_1to3y
    coverage_ratio = round(liquid_fin_assets / short_expenses, 2) if short_expenses > 0 else 99.0
    is_coverage_insufficient = coverage_ratio < 1.5

    return {
        'liquid_financial_assets': liquid_fin_assets,
        'expense_1y': exp_1y,
        'expense_1to3y': exp_1to3y,
        'investable_ceiling': investable_ceiling,
        'principal_yuan': principal_yuan,
        'is_violated': is_violated,
        'excess_amount': excess_amount,
        'coverage_ratio': coverage_ratio,
        'is_coverage_insufficient': is_coverage_insufficient
    }

def calculate_behavioral_equity_ceiling(behavior_state, assets):
    # P0-4: 严格按 category === 'Equity' 统计实际权益持仓
    actual_equity_weight = sum(a.get('weight', 0) for a in assets.values() if a.get('category') == 'Equity')

    drawdown_map = { '<5%': 20, '5-10%': 35, '10-20%': 55, '20-30%': 70, '>30%': 85 }
    bracket = behavior_state.get('drawdownBracket', '10-20%')
    base_ceiling = drawdown_map.get(bracket, 55)

    deductions = 0
    if behavior_state.get('marketDropReaction') == 'panic_sell':
        deductions += 15
    elif behavior_state.get('marketDropReaction') == 'pause_watch':
        deductions += 5
    if behavior_state.get('cashflowRelianceHigh'):
        deductions += 10
    if behavior_state.get('industryVolatileHigh'):
        deductions += 10

    final_ceiling = max(15, base_ceiling - deductions)
    is_exceeded = actual_equity_weight > final_ceiling
    excess_weight = round(max(0, actual_equity_weight - final_ceiling), 1)

    return {
        'bracket': bracket,
        'base_ceiling': base_ceiling,
        'deductions': deductions,
        'final_ceiling': final_ceiling,
        'actual_equity_weight': round(actual_equity_weight, 1),
        'is_exceeded': is_exceeded,
        'excess_weight': excess_weight
    }

def calculate_thermometer_signal(percentile):
    # P2-1: 20% 边界判定: 0-20 是 deep_low, 20-40 是 low, 40-60 neutral, 60-80 warm, 80-100 overheat
    if percentile < 20:
        code = 'deep_low'
        dca_mult = 1.8
    elif percentile < 40:
        code = 'low'
        dca_mult = 1.2
    elif percentile < 60:
        code = 'neutral'
        dca_mult = 1.0
    elif percentile < 80:
        code = 'warm'
        dca_mult = 0.5
    else:
        code = 'overheat'
        dca_mult = 0.0

    return {
        'percentile': percentile,
        'code': code,
        'dca_multiplier': dca_mult,
        'is_deep_low': code == 'deep_low',
        'is_overheated': code == 'overheat'
    }

def calculate_incremental_rebalance(assets, user_holdings, incremental_cash=50000):
    total_holding = sum(user_holdings.values()) if user_holdings else 0
    total_target_w = sum(a.get('weight', 0) for a in assets.values()) or 100.0

    gaps = []
    total_neg_gap = 0
    for code, a in assets.items():
        h = user_holdings.get(code, 0)
        curr_pct = (h / total_holding * 100) if total_holding > 0 else 0
        tgt_pct = (a.get('weight', 0) / total_target_w) * 100
        diff = curr_pct - tgt_pct
        if diff < 0:
            total_neg_gap += abs(diff)
        gaps.append({
            'code': code,
            'name': a.get('name', ''),
            'current_pct': curr_pct,
            'target_pct': tgt_pct,
            'diff_pct': diff
        })

    allocations = []
    for item in gaps:
        if item['diff_pct'] < 0 and total_neg_gap > 0:
            share = abs(item['diff_pct']) / total_neg_gap
            cash = round(incremental_cash * share)
        else:
            cash = 0
        allocations.append({
            **item,
            'allocated_cash': cash
        })

    return allocations

def run_compound_stress_test(
    board_state,
    scenario,
    health_state,
    months_range=36,
    unemployment_replacement_rate=0.3
):
    principal = board_state.get('principal', 80)
    buffer_seed = board_state.get('bufferSeed', 10)
    target_monthly = board_state.get('targetMonthly', 1.2)
    assets = board_state.get('assets', {})

    invest_principal_yuan = max(0, principal - buffer_seed) * 10000
    base_monthly_withdraw = target_monthly * 10000
    mm_rate = board_state.get('moneyMarketRate', 2.0) / 100.0

    monthly_income = health_state.get('monthlyIncome', 30000)
    essential_expense = health_state.get('essentialMonthlyExpense', 12000)

    unemployment_months = scenario.get('unemploymentMonths', 0)
    div_drop = scenario.get('dividendDropRate', 0.0)
    eq_dd = scenario.get('equityDrawdownRate', 0.20)
    medical_exp = scenario.get('medicalExpense', 0)
    medical_m = scenario.get('medicalMonth', 0)
    inflation_rate = scenario.get('inflationRate', 0.0)
    delay_months = scenario.get('delayMonths', 0)
    monthly_dd_curve = scenario.get('monthlyDrawdown', None)

    # P0-1: 失业期收入损失模型
    replacement_income = monthly_income * unemployment_replacement_rate
    unemployment_loss_per_month = max(0, essential_expense - replacement_income)

    current_buffer = buffer_seed * 10000
    min_buffer = current_buffer
    exhaustion_month = None
    timeline = []

    for t in range(1, months_range + 1):
        cal_m = ((t - 1) % 12) + 1
        inf_factor = (1 + inflation_rate) ** ((t - 1) / 12.0)

        # 失业损失
        cur_loss = unemployment_loss_per_month if t <= unemployment_months else 0
        cur_med = medical_exp if t == medical_m else 0
        month_withdraw = base_monthly_withdraw * inf_factor + cur_loss + cur_med

        # 分红
        month_div = 0
        if t > delay_months:
            for a in assets.values():
                dist = a.get('months', {}).get(cal_m, 0)
                if dist > 0:
                    val = invest_principal_yuan * (a.get('weight', 0) / 100.0)
                    month_div += val * (a.get('yield', 0) / 100.0) * dist * (1 - div_drop)

        month_interest = max(0, current_buffer) * (mm_rate / 12.0)
        next_buffer = current_buffer + month_div + month_interest - month_withdraw

        if current_buffer < min_buffer:
            min_buffer = current_buffer
        if next_buffer < 0 and exhaustion_month is None:
            exhaustion_month = t

        timeline.append({
            'month': t,
            'calendar_month': cal_m,
            'start_buffer': current_buffer,
            'dividend': month_div,
            'unemployment_loss': cur_loss,
            'withdraw': month_withdraw,
            'end_buffer': next_buffer
        })
        current_buffer = next_buffer

    is_exhausted = exhaustion_month is not None
    max_deficit = abs(min_buffer) if min_buffer < 0 else 0

    # 变现折算
    if monthly_dd_curve and exhaustion_month and exhaustion_month <= len(monthly_dd_curve):
        cur_dd = abs(monthly_dd_curve[exhaustion_month - 1])
    else:
        cur_dd = eq_dd
    discount = max(0.1, 1 - cur_dd)
    min_asset_to_sell = math.ceil(max_deficit / discount) if is_exhausted else 0

    monthly_surplus = health_state.get('monthlySurplus', 12000)
    months_to_recover = math.ceil((buffer_seed * 10000 + max_deficit) / monthly_surplus) if is_exhausted and monthly_surplus > 0 else 0

    return {
        'is_exhausted': is_exhausted,
        'exhaustion_month': exhaustion_month,
        'min_buffer': min_buffer,
        'min_asset_to_sell': min_asset_to_sell,
        'months_to_recover': months_to_recover,
        'timeline': timeline
    }

def calculate_explainable_scores(state):
    # 7-factor vulnerability + 4-factor objective aggressiveness
    debt_state = state.get('debt', {})
    health_state = state.get('health', {})
    insurance_state = state.get('insurance', {})
    board_state = state.get('board', {})
    behavior_state = state.get('behavior', {})

    debt_metrics = calculate_debt_decision_metrics(debt_state, board_state.get('growthRate', 6.5))
    total_debt = debt_metrics['total_debt']
    repay_ratio = (debt_state.get('monthlyDebtPayment', 0) / health_state.get('monthlyIncome', 30000)) if health_state.get('monthlyIncome', 0) > 0 else 0

    # 1. 债务
    f_debt = 20 if debt_metrics['has_high_debt'] else (14 if total_debt > 1000000 else (8 if total_debt > 0 else 0))
    # 2. 还贷比
    f_repay = 15 if repay_ratio > 0.5 else (10 if repay_ratio > 0.35 else 4)
    # 3. 流动性
    liq = check_liquidity_segregation(health_state, board_state.get('principal', 80))
    f_liq = 20 if liq['is_violated'] else (12 if liq['is_coverage_insufficient'] else 3)
    # 4. 收入结构
    inc_src = health_state.get('incomeSourceCount', 'dual')
    f_inc = 15 if inc_src == 'single' else (8 if inc_src == 'dual' else 3)
    # 5. 失业恢复期
    rec_m = health_state.get('unemploymentRecoveryMonths', 6)
    f_rec = 10 if rec_m > 9 else (6 if rec_m >= 6 else 2)
    # 6. 保障缺口
    ins = calculate_insurance_gap(health_state, insurance_state, total_debt)
    f_ins = 10 if ins['should_warn_downgrade'] else (6 if (ins['life_gap'] > 0 or not ins['has_million_medical']) else 0)
    # 7. 缓冲池
    sim = run_compound_stress_test(board_state, {'unemploymentMonths': 6, 'dividendDropRate': 0.3, 'equityDrawdownRate': 0.2}, health_state)
    f_buf = 10 if sim['is_exhausted'] else (5 if sim['min_buffer'] < 20000 else 0)

    total_vuln = f_debt + f_repay + f_liq + f_inc + f_rec + f_ins + f_buf

    # 进攻性 4 大客观因子
    beh = calculate_behavioral_equity_ceiling(behavior_state, board_state.get('assets', {}))
    eq_w = beh['actual_equity_weight']
    f_eq = min(35, round((eq_w / 100.0) * 35))

    high_vol = sum(a.get('weight', 0) for a in board_state.get('assets', {}).values() if a.get('market') in ['港股', '美股'] or a.get('style') in ['成长', '科创'])
    f_vol = min(25, round((high_vol / 100.0) * 25))

    f_lev = 20 if debt_metrics['has_high_debt'] else (14 if repay_ratio > 0.4 else (8 if total_debt > 0 else 0))
    f_exceed = min(20, round(beh['excess_weight'] * 1.5)) if beh['is_exceeded'] else 0

    total_agg = min(100, f_eq + f_vol + f_lev + f_exceed)

    return {
        'total_vulnerability': total_vuln,
        'vulnerability_level': '高危脆弱' if total_vuln > 60 else ('中度脆弱' if total_vuln > 30 else '稳健安全'),
        'total_aggressiveness': total_agg,
        'aggressiveness_level': '激进进攻' if total_agg > 70 else ('平衡进取' if total_agg > 40 else '谨慎保守')
    }

def run_all_unit_tests():
    print("=== 开始运行纯函数单元测试 (P0-1 ~ P2-6 验收) ===")

    # 1. P0-6: 权重总和校验
    assets_demo = {
        '511880': {'weight': 15.0, 'yield': 1.8, 'category': 'Cash', 'bucket': 'safety'},
        '511360': {'weight': 15.0, 'yield': 2.7, 'category': 'FixedIncome', 'bucket': 'safety'},
        '512890': {'weight': 20.0, 'yield': 4.5, 'category': 'Equity', 'bucket': 'growth'},
        '515450': {'weight': 15.0, 'yield': 4.2, 'category': 'Equity', 'bucket': 'growth'},
        '513530': {'weight': 10.0, 'yield': 4.8, 'category': 'Equity', 'bucket': 'growth'},
        '510300': {'weight': 10.0, 'yield': 1.5, 'category': 'Equity', 'bucket': 'growth'},
        '518880': {'weight': 7.0, 'yield': 0.0, 'category': 'Gold', 'bucket': 'hedge'},
        '511010': {'weight': 8.0, 'yield': 2.2, 'category': 'FixedIncome', 'bucket': 'hedge'}
    }
    board_m = calculate_board_metrics(80, 10, 1.2, 6.5, assets_demo)
    assert board_m['is_weight_valid'] is True, f"默认资产总权重应当严格为 100%, 实际 {board_m['total_weight']}%"
    print("✅ P0-6 / P0-4: 3桶资产配置 100% 权重校验通过！")

    # 2. P0-4: 严格权益 category === 'Equity'
    # 权益资产为: 512890(20) + 515450(15) + 513530(10) + 510300(10) = 55%
    beh = calculate_behavioral_equity_ceiling({'drawdownBracket': '10-20%', 'marketDropReaction': 'panic_sell', 'cashflowRelianceHigh': False, 'industryVolatileHigh': False}, assets_demo)
    assert beh['actual_equity_weight'] == 55.0, f"实际严格权益比例期望 55%, 实际 {beh['actual_equity_weight']}%"
    print("✅ P0-4: 严格权益 category === 'Equity' 分类核算通过！")

    # 3. P0-1: 失业损失模型
    # 收入 30000, 必要支出 12000, 替代率 30% -> 替代收入 9000, 每月净损耗 = 12000 - 9000 = 3000 元/月
    # 6 个月失业期增加总损耗 = 18000 元
    health_demo = {
        'monthlyIncome': 30000,
        'monthlyExpense': 18000,
        'essentialMonthlyExpense': 12000,
        'monthlySurplus': 12000,
        'assetsBreakdown': {
            'cashCurrent': 100000,
            'cashShortDebt': 200000,
            'equityAssets': 440000,
            'goldAssets': 56000,
            'bondAssets': 184000,
            'propertyEstimated': 2800000,
            'pensionCashValue': 20000,
            'otherAssets': 0
        },
        'expectedExpenses': {
            'expense1y': 100000,
            'expense1To3y': 150000,
            'expense3To5y': 100000
        }
    }
    stress_std = run_compound_stress_test(
        {'principal': 80, 'bufferSeed': 10, 'targetMonthly': 1.2, 'moneyMarketRate': 2.0, 'assets': assets_demo},
        {'unemploymentMonths': 6, 'dividendDropRate': 0.3, 'equityDrawdownRate': 0.2, 'medicalExpense': 0, 'medicalMonth': 0},
        health_demo,
        36,
        0.3
    )
    # 验证第1个月失业损耗是否正好是 3000 元
    assert stress_std['timeline'][0]['unemployment_loss'] == 3000, f"失业月净损耗期望 3000 元, 实际 {stress_std['timeline'][0]['unemployment_loss']}"
    assert stress_std['timeline'][6]['unemployment_loss'] == 0, "第7个月失业期结束损耗应为 0"
    print("✅ P0-1: 失业参数收入替代率损失模型测试通过！")

    # 4. P0-3 & P1-4: 债务决策与利差符号
    # 档位 3.5-4.5% 中值为 4.0%; 增长收益率 6.5% 的 70% 为 4.55%
    # spread = conservative_yield - effective_rate = 4.55 - 4.0 = +0.55%
    debt_demo = {'debtRateBracket': '3.5-4.5%', 'customDebtRate': 5.5, 'useCustomRate': False, 'mortgageBalance': 800000}
    debt_m = calculate_debt_decision_metrics(debt_demo, 6.5)
    assert debt_m['effective_rate'] == 4.0, f"默认应使用档位中值 4.0%, 实际 {debt_m['effective_rate']}"
    assert debt_m['spread'] == 0.55, f"利差期望 +0.55%, 实际 {debt_m['spread']}"

    # 若开启自定义 5.5%
    debt_custom = {'debtRateBracket': '3.5-4.5%', 'customDebtRate': 5.5, 'useCustomRate': True, 'mortgageBalance': 800000}
    debt_m2 = calculate_debt_decision_metrics(debt_custom, 6.5)
    assert debt_m2['effective_rate'] == 5.5, f"自定义期望 5.5%, 实际 {debt_m2['effective_rate']}"
    assert debt_m2['spread'] == -0.95, f"利差期望 -0.95%, 实际 {debt_m2['spread']}"
    assert "用户自定义" in debt_m2['rate_source']
    print("✅ P0-3 & P1-4: 债务决策自定义开关、档位中值与利差符号对齐通过！")

    # 5. P1-1: 流动性硬隔离解耦
    # liquid_fin = 10+20+44+5.6+18.4 = 98 万
    # investable_ceiling = 98 - 10*1.0 - 15*0.5 = 98 - 17.5 = 80.5 万元 (805,000 元)
    # 本金 80 万 < 80.5 万 -> 不违规
    liq = check_liquidity_segregation(health_demo, 80)
    assert liq['investable_ceiling'] == 805000, f"可投资上限期望 80.5万, 实际 {liq['investable_ceiling']}"
    assert liq['is_violated'] is False, "80万本金应在80.5万上限之内"
    print("✅ P1-1: A组资产与B组支出彻底解耦流动性硬隔离核算通过！")

    # 6. P1-2: 责任缺口法寿险与意外险
    # 负债 80万 + 10年生活底线 144万 + 子女教育 50万 - 高流动性现金 (10+20=30万) = 244 万
    # 已有保额 50万 -> 净缺口 194 万
    # 意外险建议额 = 194万 * 0.5 = 97 万
    ins = calculate_insurance_gap(health_demo, {'childEduTarget': 500000, 'existingLifeCover': 500000, 'existingCritCover': 200000, 'existingAccidentCover': 500000, 'hasMillionMedical': False, 'coverageTier': 'insufficient'}, 800000)
    assert ins['high_liquid_deduction'] == 300000, f"寿险扣减现金期望 30万, 实际 {ins['high_liquid_deduction']}"
    assert ins['life_target'] == 2440000, f"寿险总需求期望 244万, 实际 {ins['life_target']}"
    assert ins['life_gap'] == 1940000, f"寿险净缺口期望 194万, 实际 {ins['life_gap']}"
    assert ins['accident_target'] == 970000, f"意外险目标期望 97万 (寿险缺口50%), 实际 {ins['accident_target']}"
    print("✅ P1-2: 寿险责任扣减高流动性现金与意外险50%锚定测试通过！")

    # 7. P1-3: 房产双视角资产负债表与 20% 冲击
    # 房产 280万, 金融资产 100万 (含养老金现值2万等), 房贷 80万, 无金融负债
    # 全口径总资产 380万, 总负债 80万, 净资产 300万, 负债率 80/380 = 21.1%
    # 剔除房产口径: 金融总资产 100万, 金融负债 0, 金融净资产 100万, 负债率 0%
    # 房产下跌 20% (-56万): 总资产变为 324万, 净资产变为 244万, 负债率变为 80/324 = 24.7%
    re_risk = calculate_real_estate_risk({'totalEstimatedValue': 2800000, 'stressDropPct': 20}, health_demo, {'mortgageBalance': 800000, 'carLoanBalance': 0, 'consumerLoanBalance': 0, 'businessLoanBalance': 0})
    assert re_risk['total_net_worth'] == 3000000, f"全口径净资产期望 300万, 实际 {re_risk['total_net_worth']}"
    assert re_risk['financial_net_worth'] == 1000000, f"金融净资产期望 100万, 实际 {re_risk['financial_net_worth']}"
    assert re_risk['stress_drop_amount'] == 560000, f"房产下跌20%期望缩水 56万, 实际 {re_risk['stress_drop_amount']}"
    assert re_risk['stress_net_worth'] == 2440000, f"冲击后净资产期望 244万, 实际 {re_risk['stress_net_worth']}"
    print("✅ P1-3: 全口径 vs 剔除房产双视角资产负债表及 20% 冲击测试通过！")

    # 8. P1-5: 多目标资源挤占模型
    goals_demo = [
        {'id': 'g1', 'name': '2035 子女教育', 'type': '子女教育金', 'priority': '刚性', 'targetAmount': 1000000, 'targetYear': 2035, 'reservedAmount': 0},
        {'id': 'g2', 'name': '2040 提前退休', 'type': '提前退休', 'priority': '弹性', 'targetAmount': 2500000, 'targetYear': 2040, 'reservedAmount': 150000}
    ]
    mg = calculate_multi_goal_projections(goals_demo, 800000, 12000, 6.5, 0.02)
    assert len(mg['goal_results']) == 2
    # 刚性教育目标优先获得本金和月结余
    g1_res = mg['goal_results'][0]
    assert g1_res['allocated_principal'] > 0, "刚性目标必须优先分配本金"
    assert mg['total_allocated_principal'] <= 800000, "总分配本金不能超过池上限"
    print("✅ P1-5: 多目标资金排挤与资源池分配推演测试通过！")

    # 9. P2-1: 估值温度计 20% 边界判定
    therm_20 = calculate_thermometer_signal(20)
    assert therm_20['code'] == 'low', f"20% 分位数应为 low (低估), 实际 {therm_20['code']}"
    assert therm_20['dca_multiplier'] == 1.2, f"low 档定投倍数应为 1.2x, 实际 {therm_20['dca_multiplier']}"
    therm_19 = calculate_thermometer_signal(19)
    assert therm_19['code'] == 'deep_low', f"19% 分位数应为 deep_low (深度低估), 实际 {therm_19['code']}"
    assert therm_19['dca_multiplier'] == 1.8
    print("✅ P2-1: 估值温度计 20% 边界判定与定投倍数核对通过！")

    # 10. P2-2: 增量资金再平衡计算
    holdings = {'512890': 20.0, '515450': 10.0} # 515450 目标 15%, 现仅 10万 (33.3% < 50%), 欠配
    inc_reb = calculate_incremental_rebalance({'512890': {'weight': 20.0, 'name': '中证红利'}, '515450': {'weight': 15.0, 'name': '标普红利'}}, holdings, 50000)
    alloc_515450 = next(x for x in inc_reb if x['code'] == '515450')
    assert alloc_515450['allocated_cash'] > 0, "欠配标的必须分配到新增资金"
    print("✅ P2-2: 增量资金再平衡计算器测试通过！")

    print("\n🎉 全部 16 项核心量化模型与业务规则单元测试全部通过！")

if __name__ == '__main__':
    run_all_unit_tests()

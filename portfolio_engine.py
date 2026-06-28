import datetime


def is_stable_cashflow_asset(asset):
    return asset.get('income_type') in ['dividend', 'cash_interest']


def calculate_portfolio(weights, assets, principal, buffer_seed, money_market_rate):
    """
    1. 组合收益测算
    weights: dict of {code: weight_val (float 0-100)}
    assets: dict or list of dicts.
    """
    if isinstance(assets, list):
        assets_dict = {item['code']: item for item in assets}
    else:
        assets_dict = assets

    invest_principal = max(principal - buffer_seed, 0.0)
    total_weight = 0.0
    blended_cash_yield = 0.0
    blended_growth_return = 0.0
    blended_total_return = 0.0

    asset_details = []

    for code, asset in assets_dict.items():
        weight = float(weights.get(code, 0.0))
        total_weight += weight

        current_price = asset.get('price', 0.0)
        current_yield = asset.get('yield') if asset.get('yield') is not None else asset.get('estimated_yield', 0.0)
        est_return = asset.get('estimated_return') if asset.get('estimated_return') is not None else current_yield

        allocated_amt = invest_principal * (weight / 100.0)
        stable_cashflow = is_stable_cashflow_asset(asset)
        expected_annual_div = allocated_amt * (current_yield / 100.0) * 10000.0 if stable_cashflow else 0.0  # 元

        asset_details.append({
            'code': code,
            'name': asset.get('name', ''),
            'role': asset.get('role', ''),
            'market': asset.get('market', ''),
            'volatility_level': asset.get('volatility_level', ''),
            'income_type': asset.get('income_type', ''),
            'weight': weight,
            'price': current_price,
            'yield': current_yield,
            'estimated_return': est_return,
            'target_index_code': asset.get('target_index_code'),
            'rebalance_band': asset.get('rebalance_band', 3),
            'stableCashflow': stable_cashflow,
            'allocatedAmt': allocated_amt,
            'expectedAnnualDiv': expected_annual_div,
            'strategy_note': asset.get('strategy_note', ''),
            'risk_note': asset.get('risk_note', '')
        })

        if stable_cashflow:
            blended_cash_yield += (weight / 100.0) * current_yield
        if asset.get('income_type') == 'capital_growth':
            blended_growth_return += (weight / 100.0) * est_return
        
        blended_total_return += (weight / 100.0) * est_return

    expected_annual_dividend = invest_principal * (blended_cash_yield / 100.0) * 10000.0  # 元
    expected_monthly_dividend = expected_annual_dividend / 12.0
    expected_monthly_growth = invest_principal * (blended_growth_return / 100.0) * 10000.0 / 12.0

    return {
        'investPrincipal': invest_principal,
        'totalWeight': total_weight,
        'blendedCashYield': blended_cash_yield,
        'blendedGrowthReturn': blended_growth_return,
        'blendedTotalReturn': blended_total_return,
        'expectedAnnualDividend': expected_annual_dividend,
        'expectedMonthlyDividend': expected_monthly_dividend,
        'expectedMonthlyGrowth': expected_monthly_growth,
        'assetDetails': asset_details
    }


def _get_harvest_return(asset, harvest_scenario):
    if harvest_scenario == 'conservative':
        return -10.0
    if harvest_scenario == 'neutral':
        return 3.0
    if harvest_scenario == 'optimistic':
        return float(asset.get('estimated_return') or 0.0)
    return 0.0


def simulate_cashflow(months_range, monthly_withdraw, buffer_seed, invest_principal, weights, assets, money_market_rate, rebalance_harvest=False, harvest_scenario='neutral'):
    """
    2. 36个月缓冲池流转模拟
    """
    if isinstance(assets, list):
        assets_dict = {item['code']: item for item in assets}
    else:
        assets_dict = assets

    buffer_balance = [buffer_seed * 10000.0]  # 元
    dividends_history = []
    interest_earned_history = []
    harvest_history = []
    breached_at_month = None

    for t in range(1, months_range + 1):
        c_month = ((t - 1) % 12) + 1

        # 1) 计算当月常规分红流入 (仅针对 income_type 为 dividend 或 cash_interest 的资产)
        month_dividend = 0.0
        for code, asset in assets_dict.items():
            weight = float(weights.get(code, 0.0))
            current_yield = asset.get('yield') if asset.get('yield') is not None else asset.get('estimated_yield', 0.0)

            if is_stable_cashflow_asset(asset):
                dist_months = asset.get('distribution_months', None) or asset.get('months', {})
                month_dist_ratio = dist_months.get(str(c_month)) or dist_months.get(c_month) or 0.0
                if month_dist_ratio > 0.0:
                    asset_value = invest_principal * (weight / 100.0) * 10000.0  # 元
                    month_dividend += asset_value * (current_yield / 100.0) * month_dist_ratio

        # 2) 乐观/情景假设下卖出成长资产补充现金流。默认关闭，安全结论不依赖该项。
        month_harvest = 0.0
        if rebalance_harvest and (t % 12 == 0):
            for code, asset in assets_dict.items():
                weight = float(weights.get(code, 0.0))
                if asset.get('income_type') == 'capital_growth':
                    scenario_return = _get_harvest_return(asset, harvest_scenario)
                    if scenario_return <= 0:
                        continue
                    asset_value = invest_principal * (weight / 100.0) * 10000.0  # 元
                    month_harvest += asset_value * (scenario_return / 100.0)

        # 3) 缓冲池利息 (月度利息)
        current_interest = buffer_balance[-1] * (money_market_rate / 12.0)

        # 4) 缓冲池结转
        next_balance = buffer_balance[-1] + month_dividend + month_harvest + current_interest - monthly_withdraw

        dividends_history.append(month_dividend)
        interest_earned_history.append(current_interest)
        harvest_history.append(month_harvest)
        buffer_balance.append(next_balance)

        if next_balance < 0 and breached_at_month is None:
            breached_at_month = t

    buffer_history = buffer_balance[1:]

    return {
        'bufferHistory': buffer_history,
        'dividendsHistory': dividends_history,
        'interestEarnedHistory': interest_earned_history,
        'harvestHistory': harvest_history,
        'breachedAtMonth': breached_at_month,
        'minBuffer': min(buffer_history) if buffer_history else 0.0
    }


def calculate_cashflow_feasibility(months_range, target_monthly_withdraw, buffer_seed, principal, weights, assets, money_market_rate):
    """
    现金流可行性反推。所有结论只基于分红/票息/现金利息，不纳入卖出成长资产。
    principal/buffer_seed 单位为万元；withdraw 单位为元。
    """
    def survives(test_monthly, test_principal, test_buffer_seed):
        invest_principal = max(test_principal - test_buffer_seed, 0.0)
        sim = simulate_cashflow(
            months_range,
            test_monthly,
            test_buffer_seed,
            invest_principal,
            weights,
            assets,
            money_market_rate,
            False,
            'neutral'
        )
        return sim['minBuffer'] > 0

    low, high = 0.0, max(target_monthly_withdraw * 3.0, 1.0)
    for _ in range(40):
        mid = (low + high) / 2.0
        if survives(mid, principal, buffer_seed):
            low = mid
        else:
            high = mid
    safe_monthly = low

    min_principal = principal
    if target_monthly_withdraw > 0 and not survives(target_monthly_withdraw, principal, buffer_seed):
        low_p = max(buffer_seed, 0.0)
        high_p = max(principal, buffer_seed + 1.0)
        while not survives(target_monthly_withdraw, high_p, buffer_seed) and high_p < 100000.0:
            high_p *= 1.5
            if high_p <= buffer_seed:
                high_p = buffer_seed + 1.0
        if high_p < 100000.0:
            for _ in range(40):
                mid = (low_p + high_p) / 2.0
                if survives(target_monthly_withdraw, mid, buffer_seed):
                    high_p = mid
                else:
                    low_p = mid
            min_principal = high_p
        else:
            min_principal = None

    min_buffer_months = 0.0
    if target_monthly_withdraw > 0:
        high_m = 60.0
        if survives(target_monthly_withdraw, principal, 0.0):
            min_buffer_months = 0.0
        elif survives(target_monthly_withdraw, principal, high_m * target_monthly_withdraw / 10000.0):
            low_m = 0.0
            for _ in range(40):
                mid_m = (low_m + high_m) / 2.0
                test_buffer = mid_m * target_monthly_withdraw / 10000.0
                if survives(target_monthly_withdraw, principal, test_buffer):
                    high_m = mid_m
                else:
                    low_m = mid_m
            min_buffer_months = high_m
        else:
            min_buffer_months = None

    return {
        'safeMonthlyWithdraw': safe_monthly,
        'safeMonthlyWithdrawWan': safe_monthly / 10000.0,
        'recommendedMonthlyExpense': safe_monthly * 0.95,
        'recommendedMonthlyExpenseWan': safe_monthly * 0.95 / 10000.0,
        'minPrincipalWan': min_principal,
        'minBufferMonths': min_buffer_months,
        'isTargetFeasibleWithoutHarvest': survives(target_monthly_withdraw, principal, buffer_seed) if target_monthly_withdraw > 0 else True
    }


def get_dca_adjustment(history_data, index_code, role):
    """
    3. 估值分位温度计与 DCA 调节因子
    """
    fallback_res = {
        'hasHistory': False,
        'percentile': 50.0,
        'factor': 1.0,
        'pe': "--",
        'pb': "--",
        'dividend_yield': "--",
        'valuationZone': "数据不足，保持基础计划",
        'tips': "由于未找到此标的的估值历史序列，系统将采用基础配置计划，不进行动态调节。"
    }
    if not history_data:
        return fallback_res

    filtered = [item for item in history_data if item.get('index_code') == index_code]
    if not filtered:
        return fallback_res

    # Sort by date
    def get_date(item):
        d_str = item.get('date', '1970-01-01')
        try:
            return datetime.datetime.strptime(d_str, '%Y-%m-%d')
        except Exception:
            return datetime.datetime.min
    filtered.sort(key=get_date)

    latest = filtered[-1]
    
    def safe_float(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    pe_list = [safe_float(item.get('pe')) for item in filtered if safe_float(item.get('pe')) is not None]
    pb_list = [safe_float(item.get('pb')) for item in filtered if safe_float(item.get('pb')) is not None]
    dy_list = [safe_float(item.get('dividend_yield')) for item in filtered if safe_float(item.get('dividend_yield')) is not None]

    current_pe = safe_float(latest.get('pe'))
    current_pb = safe_float(latest.get('pb'))
    current_dy = safe_float(latest.get('dividend_yield'))

    if current_pe is None: current_pe = 0.0
    if current_pb is None: current_pb = 0.0
    if current_dy is None: current_dy = 0.0

    percentile = 50.0
    factor = 1.0
    valuation_zone = "合理估值区间 (估值适中)"
    tips = ""

    if role == 'dividend_income':
        if dy_list:
            count = sum(1 for y in dy_list if y < current_dy)
            percentile = round((count / len(dy_list)) * 100, 1)
        
        if percentile >= 70.0:
            valuation_zone = "极具性价比 (低估区域)"
            factor = 1.3
            tips = "提示：目前红利资产股息率处于历史较高百分位，具备优秀的派息性价比，定投系数已调升至 1.3x。"
        elif percentile >= 30.0:
            valuation_zone = "合理估值区间 (估值中性)"
            factor = 1.0
            tips = "提示：估值处于常态百分位，建议保持基础定投计划，定投系数 1.0x。"
        else:
            valuation_zone = "估值偏贵区间 (高估区域)"
            factor = 0.5
            tips = "提示：股息率已被估值上涨稀释，性价比偏低，定投系数下调至 0.5x 以控制建仓成本。"

    elif role == 'domestic_beta':
        if pe_list:
            pe_pct = round((sum(1 for p in pe_list if p < current_pe) / len(pe_list)) * 100, 1)
            pb_pct = round((sum(1 for p in pb_list if p < current_pb) / len(pb_list)) * 100, 1) if pb_list else pe_pct
            percentile = max(pe_pct, pb_pct)
        
        if percentile <= 30.0:
            valuation_zone = "极具性价比 (国内宽基低估)"
            factor = 1.2
            tips = "提示：国内宽基 PE/PB 估值处于历史低位，长期配置性价比凸显，定投系数上调至 1.2x。"
        elif percentile <= 70.0:
            valuation_zone = "合理估值区间 (估值中性)"
            factor = 1.0
            tips = "提示：宽基估值处于历史常态水平，建议按基础定投稳步积累，系数 1.0x。"
        else:
            valuation_zone = "估值偏贵区间 (宽基估值高企)"
            factor = 0.6
            tips = "提示：国内宽基 PE/PB 已进入历史高估区域，适当下调定投金额，系数 0.6x。"

    elif role == 'tech_growth':
        if pe_list:
            count = sum(1 for p in pe_list if p < current_pe)
            percentile = round((count / len(pe_list)) * 100, 1)

        if percentile <= 25.0:
            valuation_zone = "超跌低估区间 (科技成长蓄势)"
            factor = 1.1
            tips = "提示：科技类资产估值进入历史低位，但波动较高，定投系数仅小幅调高至 1.1x。"
        elif percentile <= 75.0:
            valuation_zone = "合理估值区间 (估值中性)"
            factor = 0.8
            tips = "提示：科技指数估值温和，但仍属于高波动资产，建议保持克制的小额定投，系数 0.8x。"
        else:
            valuation_zone = "情绪过热区间 (科技估值透支)"
            factor = 0.3
            tips = "提示：科技成长股情绪过热，估值高位溢价，为防范高位被套，定投系数严格下调至 0.3x。"

    elif role in ['overseas_broad', 'overseas_tech', 'overseas_beta']:
        if not pe_list:
            valuation_zone = "海外估值数据不足"
            factor = 1.0
            tips = "提示：当前缺少该海外资产的本地估值历史，保持 1.0x 基础计划。纳指100属于海外科技，并不等同于海外宽基。"
        elif role == 'overseas_tech':
            count = sum(1 for p in pe_list if p < current_pe)
            percentile = round((count / len(pe_list)) * 100, 1)

            if percentile <= 25.0:
                valuation_zone = "海外科技估值低位"
                factor = 1.0
                tips = "提示：海外科技低估时仍需控制集中度，定投系数不超过 1.0x。"
            elif percentile <= 75.0:
                valuation_zone = "海外科技估值中性"
                factor = 0.8
                tips = "提示：纳指100偏科技成长属性，估值中性时保持克制定投，系数 0.8x。"
            else:
                valuation_zone = "海外科技估值偏贵"
                factor = 0.3
                tips = "提示：海外科技高估时严格降温，系数 0.3x，并注意汇率与溢价风险。"
        else:
            count = sum(1 for p in pe_list if p < current_pe)
            percentile = round((count / len(pe_list)) * 100, 1)
            if percentile <= 30.0:
                valuation_zone = "低估配置区域 (海外宽基低估)"
                factor = 1.0
                tips = "提示：海外宽基估值偏低，但因汇率和数据覆盖限制，最高保持 1.0x。"
            elif percentile <= 70.0:
                valuation_zone = "合理估值区间 (估值中性)"
                factor = 1.0
                tips = "提示：海外宽基估值合理，定投系数 1.0x。建议分批换汇以平滑汇率波动。"
            else:
                valuation_zone = "高估警戒区域 (海外宽基高估)"
                factor = 0.5
                tips = "提示：海外指数市盈率偏高，定投系数降低至 0.5x。防止高位接盘和汇率波动双重风险。"

    return {
        'hasHistory': True,
        'percentile': percentile,
        'factor': factor,
        'pe': f"{current_pe:.2f}",
        'pb': f"{current_pb:.2f}",
        'dividend_yield': f"{current_dy:.2f}%",
        'valuationZone': valuation_zone,
        'tips': tips
    }


def run_stress_test(weights, assets, invest_principal, monthly_withdraw, buffer_months, money_market_rate, stress_params):
    """
    4. 极端市况压力测试
    stress_params: dict containing 'drawdown' (dict of role->pct) and 'dividendDrop' (dict of role->pct)
    """
    if isinstance(assets, list):
        assets_dict = {item['code']: item for item in assets}
    else:
        assets_dict = assets

    start_buffer = buffer_months * monthly_withdraw
    stress_buffer_balance = [start_buffer]
    stress_dividends_history = []
    interest_earned_history = []
    breached_at_month = None
    months_range = 36

    initial_portfolio_val = invest_principal * 10000.0  # 元
    stressed_portfolio_val = 0.0

    for code, asset in assets_dict.items():
        weight = float(weights.get(code, 0.0))
        asset_val = initial_portfolio_val * (weight / 100.0)
        role = asset.get('role', '')

        drawdown_ratio = stress_params.get('drawdown', {}).get(role, 30.0)
        stressed_portfolio_val += asset_val * (1.0 - drawdown_ratio / 100.0)

    max_net_worth_drawdown = ((initial_portfolio_val - stressed_portfolio_val) / initial_portfolio_val) * 100.0 if initial_portfolio_val > 0 else 0.0

    for t in range(1, months_range + 1):
        c_month = ((t - 1) % 12) + 1

        month_dividend = 0.0
        for code, asset in assets_dict.items():
            weight = float(weights.get(code, 0.0))
            current_yield = asset.get('yield') if asset.get('yield') is not None else asset.get('estimated_yield', 0.0)

            if is_stable_cashflow_asset(asset):
                dist_months = asset.get('distribution_months', None) or asset.get('months', {})
                month_dist_ratio = dist_months.get(str(c_month)) or dist_months.get(c_month) or 0.0
                if month_dist_ratio > 0.0:
                    asset_val = invest_principal * (weight / 100.0) * 10000.0  # 元
                    role = asset.get('role', '')
                    asset_drawdown = stress_params.get('drawdown', {}).get(role, 30.0)
                    stressed_asset_val = asset_val * (1.0 - asset_drawdown / 100.0)

                    div_drop = stress_params.get('dividendDrop', {}).get(role, 20.0)
                    stressed_yield = current_yield * (1.0 - div_drop / 100.0)

                    month_dividend += stressed_asset_val * (stressed_yield / 100.0) * month_dist_ratio

        current_interest = stress_buffer_balance[-1] * (money_market_rate / 12.0)
        next_balance = stress_buffer_balance[-1] + month_dividend + current_interest - monthly_withdraw

        stress_dividends_history.append(month_dividend)
        interest_earned_history.append(current_interest)
        stress_buffer_balance.append(next_balance)

        if next_balance < 0 and breached_at_month is None:
            breached_at_month = t

    stressed_buffer_history = stress_buffer_balance[1:]

    return {
        'stressedBufferHistory': stressed_buffer_history,
        'stressDividendsHistory': stress_dividends_history,
        'interestEarnedHistory': interest_earned_history,
        'breachedAtMonth': breached_at_month,
        'maxNetWorthDrawdown': max_net_worth_drawdown,
        'isBreached': breached_at_month is not None,
        'minStressedBuffer': min(stressed_buffer_history) if stressed_buffer_history else 0.0
    }


def calculate_four_money_analysis(fd, total_assets, net_worth, leverage, repay_income_ratio, surplus_ratio, cash_coverage_months, risk_tolerance_code):
    """
    四类钱配置合理性分析：要花的钱、保命的钱、生钱的钱、保本升值的钱。
    """
    def num(key):
        try:
            return float(fd.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    monthly_living_expense = max(num('f-fixed-expense'), 1.0)
    monthly_essential_expense = max(num('f-essential-expense'), monthly_living_expense * 0.7, 1.0)
    monthly_required_outflow = monthly_essential_expense + num('debt-monthly-repay')
    liquid_cash = num('ast-cash') + num('ast-mmf')
    planned_spend_12m = num('f-planned-spend-12m')
    planned_spend_36m = num('f-planned-spend-36m')
    high_interest_debt = num('debt-high-interest')
    coverage_level = fd.get('protect-coverage') or 'basic'
    has_large_expense = any(fd.get(key) for key in [
        'expense-buyhouse', 'expense-edu', 'expense-med', 'expense-biz', 'expense-city', 'expense-other'
    ])
    has_family_pressure = (
        fd.get('f-children') == 'yes' or fd.get('f-elders') == 'yes' or
        fd.get('f-stability') == 'volatile' or leverage > 0.45 or repay_income_ratio > 0.3 or
        high_interest_debt > 0
    )

    spend_min_months = 6 if (has_large_expense or planned_spend_12m > 0) else 2
    spend_max_months = 12 if (has_large_expense or planned_spend_36m > 0) else 3
    life_min_months = 12 if has_family_pressure else 6
    life_max_months = 18 if has_family_pressure else 12

    spend_min = max(monthly_required_outflow * spend_min_months, planned_spend_12m)
    spend_max = max(monthly_required_outflow * spend_max_months, planned_spend_12m + planned_spend_36m * 0.5)
    spend_amount = min(liquid_cash, spend_max)
    liquid_after_spend = max(0.0, liquid_cash - spend_amount)

    coverage_credit_months = {'none': 0, 'basic': 3, 'adequate': 6, 'strong': 9}.get(coverage_level, 3)
    protection_credit = monthly_required_outflow * coverage_credit_months
    life_min = monthly_required_outflow * life_min_months
    life_max = monthly_required_outflow * life_max_months
    life_reserve = min(liquid_after_spend, life_max)
    stable_liquid_remainder = max(0.0, liquid_after_spend - life_reserve)

    life_amount = life_reserve + num('ast-insurance') + protection_credit
    earn_amount = num('ast-ashare') + num('ast-hk') + num('ast-overseas') + num('ast-others')
    preserve_amount = num('ast-house') + num('ast-gold') + stable_liquid_remainder
    base_assets = max(float(total_assets or 0), 1.0)

    earn_min_pct = 25
    earn_max_pct = 55
    try:
        tolerance = float(risk_tolerance_code or 0)
    except (TypeError, ValueError):
        tolerance = 0.0

    if cash_coverage_months < 6 or repay_income_ratio > 0.35 or surplus_ratio < 0.15 or high_interest_debt > 0:
        earn_min_pct = 10
        earn_max_pct = 30
    elif cash_coverage_months >= 12 and surplus_ratio >= 0.25 and tolerance >= 30:
        earn_min_pct = 35
        earn_max_pct = 65

    preserve_min_pct = 15
    preserve_max_pct = 60 if has_large_expense else 50
    if num('ast-house') / base_assets > 0.7:
        preserve_max_pct = 65

    def classify_amount(value, min_value, max_value, low_advice, high_advice, ok_advice):
        if value < min_value:
            return {'status': '偏低', 'color': 'var(--accent-red)', 'advice': low_advice, 'isOk': False}
        if value > max_value:
            return {'status': '偏高', 'color': 'var(--accent-orange)', 'advice': high_advice, 'isOk': False}
        return {'status': '合理', 'color': 'var(--accent-emerald)', 'advice': ok_advice, 'isOk': True}

    def classify_pct(value, min_pct, max_pct, low_advice, high_advice, ok_advice):
        pct = value / base_assets * 100
        return classify_amount(pct, min_pct, max_pct, low_advice, high_advice, ok_advice)

    spend_status = classify_amount(
        spend_amount, spend_min, spend_max,
        '近期生活费、月供和确定性开销储备不足，先补足独立现金账户。',
        '近期可花资金过厚，可把超出部分转入应急金或稳健增值资产。',
        '日常开销、月供和未来三年开销预留基本匹配。'
    )
    life_status = classify_amount(
        life_amount, life_min, life_max + num('ast-insurance') + protection_credit,
        '失业、医疗或家庭意外缓冲不足，优先补齐应急金、基础保障和高息债务处理。',
        '保命资金占用偏多，确认保障充足后可分批转入保值或生钱资产。',
        '风险兜底资金覆盖度较好，家庭抗冲击能力较稳。'
    )
    earn_status = classify_pct(
        earn_amount, earn_min_pct, earn_max_pct,
        '生钱资产不足，长期购买力可能被通胀侵蚀。',
        '生钱资产偏高，若现金防线不足，回撤时可能被迫卖出。',
        '权益和经营类资产占比与当前风险承受力大致匹配。'
    )
    preserve_status = classify_pct(
        preserve_amount, preserve_min_pct, preserve_max_pct,
        '保值稳健资产不足，组合对通胀和系统性波动的缓冲偏弱。',
        '保本升值资产偏重，尤其房产占比高时会压低流动性。',
        '稳健保值资产能够承担资产底仓和波动缓冲角色。'
    )

    buckets = [
        {
            'key': 'spend',
            'title': '要花的钱',
            'subtitle': '未来 2-12 个月刚性支出与确定性开销',
            'amount': spend_amount,
            'ratio': spend_amount / base_assets,
            'targetText': f'{spend_min_months}-{spend_max_months} 个月刚性支出，且覆盖未来12个月确定支出',
            'components': '活期现金、货币/短债中优先隔离的近期支出',
            **spend_status
        },
        {
            'key': 'life',
            'title': '保命的钱',
            'subtitle': '失业、医疗、家庭意外与保障防线',
            'amount': life_amount,
            'ratio': life_amount / base_assets,
            'targetText': f'{life_min_months}-{life_max_months} 个月刚性支出 + 基础保障',
            'components': '应急现金、货币/短债、养老金/保险现金价值、保障覆盖等效额度',
            **life_status
        },
        {
            'key': 'earn',
            'title': '生钱的钱',
            'subtitle': '承担长期现金流与增长弹性的资产',
            'amount': earn_amount,
            'ratio': earn_amount / base_assets,
            'targetText': f'{earn_min_pct}-{earn_max_pct}% 总资产',
            'components': 'A股、港股、海外权益、其他可增值资产',
            **earn_status
        },
        {
            'key': 'preserve',
            'title': '保本升值的钱',
            'subtitle': '稳健底仓、抗通胀与资产压舱石',
            'amount': preserve_amount,
            'ratio': preserve_amount / base_assets,
            'targetText': f'{preserve_min_pct}-{preserve_max_pct}% 总资产',
            'components': '房产、黄金、超额货币/短债留存',
            **preserve_status
        }
    ]

    ok_count = sum(1 for item in buckets if item['isOk'])
    critical_low = spend_status['status'] == '偏低' or life_status['status'] == '偏低'
    score = min(100, ok_count * 22 + (0 if critical_low else 12))
    overall_status = '结构需调整'
    overall_color = 'var(--accent-orange)'
    if ok_count >= 3 and not critical_low:
        overall_status = '配置较合理'
        overall_color = 'var(--accent-emerald)'
    elif critical_low:
        overall_status = '基础防线不足'
        overall_color = 'var(--accent-red)'
    elif earn_status['status'] == '偏高':
        overall_status = '收益资产偏激进'
        overall_color = 'var(--accent-orange)'

    return {
        'overallStatus': overall_status,
        'overallColor': overall_color,
        'score': score,
        'summary': f'四类资金中 {ok_count}/4 项处于建议区间。先确保“要花的钱”和“保命的钱”不缺口，再讨论“生钱的钱”的进攻比例。',
        'buckets': buckets
    }


def evaluate_family_profile(fd, investable_assets, net_worth, total_assets, leverage, repay_income_ratio, surplus_ratio, cash_coverage_months, investment_goal_codes, risk_tolerance_code):
    """
    5. 家庭财务画像体检
    """
    profile_key = "balanced"
    profile_title = "⚖️ 均衡发展型家庭"
    profile_diag = "家庭资产负债结构中性，流动性防线与增长资产比例处于大致平稳的状态。"
    quote = "“维护资产流动性与成长性的平衡是长胜法则。不要冒无谓的风险，用纪律抵抗市场情绪。”"
    border_color = "var(--text-secondary)"

    safety = 30
    longterm = 50
    hedge = 20
    reason = "红利负责稳健派息现金流，宽基与科技负责博取长期增值弹性，黄金对冲极端宏观不确定性，现金缓冲锁定日常开销，确保家庭无被迫割肉变现之忧。"

    has_short_term_large_expense = (
        fd.get('expense-buyhouse') or fd.get('expense-edu') or fd.get('expense-med') or 
        fd.get('expense-biz') or fd.get('expense-city') or fd.get('expense-other')
    )

    is_low_cash = cash_coverage_months < 6
    high_interest_debt = float(fd.get('debt-high-interest', 0) or 0)
    monthly_income = float(fd.get('f-monthly-income', 0) or 0)
    is_high_debt = leverage > 0.5 or repay_income_ratio > 0.35 or (monthly_income > 0 and high_interest_debt > monthly_income)
    is_low_surplus = surplus_ratio < 0.15

    is_prohibit_aggressive = is_low_cash or is_high_debt or is_low_surplus

    if is_high_debt:
        profile_key = "leverage"
        profile_title = "🚨 债务高锁型家庭"
        profile_diag = "家庭负债率偏高，或每月贷款偿还比例已超出安全红线，现金流极易断裂。"
        quote = "“别让时间约束变成情绪惩罚。高额负债不仅锁死了本金弹性，更放大了市场大跌时的心理恐慌。”"
        border_color = "var(--accent-red)"
        safety = 50
        longterm = 30
        hedge = 20
        reason = "鉴于家庭负债偏高，安全防御资产应占据首要核心位置（50%），限制或禁止高波动的科技/海外成长性配置，防止市场下行与偿债支出重叠时被动清仓。"
    elif is_low_cash or is_low_surplus:
        profile_key = "tight"
        profile_title = "⚠️ 现金流脆弱型家庭"
        profile_diag = "月度储蓄率不足，或者应急备用金储备少于6个月固定生活费。"
        quote = "“现金不是最便宜的资产，它是让你在市场底部拿到留在牌桌上的入场券。优先充实池水。”"
        border_color = "var(--accent-red)"
        safety = 60
        longterm = 20
        hedge = 20
        reason = "优先使用流动资产和红利低波资产积攒至少12个月的应急现金防御墙（安全桶拉升至60%），待收支结余率与现金池充裕后，再逐步增配增长资产。"
    elif cash_coverage_months >= 12 and surplus_ratio >= 0.25 and risk_tolerance_code >= 5:
        profile_key = "stable"
        profile_title = "💎 稳健积累型家庭"
        profile_diag = "负债水平极低，每月结余能力强，且手握超过一年的固定开支现金储备，具备扎实的抗冲击底气。"
        quote = "“这类家庭拥有极高的财务喘息空间，可以更加注重长期大类资产配置的‘再平衡纪律’，分享企业增长红利。”"
        border_color = "var(--accent-emerald)"
        safety = 20
        longterm = 65
        hedge = 15
        reason = "由于财务底子扎实且风险承受期长，可缩减安全备用金至 20%，增配国内沪深300（经济Beta）、纳斯达克/科创50（科技增长）以及黄金对冲，最大化分享复利增值。"
    elif investable_assets > 0.0 and ((fd.get('ast-cash', 0) + fd.get('ast-mmf', 0)) / investable_assets) > 0.7 and not has_short_term_large_expense:
        profile_key = "conservative"
        profile_title = "🛡️ 现金沉淀型家庭"
        profile_diag = "家庭极度保守，绝大部分可投资资产以现金或货币基金沉淀，未能建立对抗通胀的被动权益防线。"
        quote = "“全存现金的风险在于通货膨胀对实际购买力的隐性吞噬。安全感不应以未来购买力的缩水为隐性代价。”"
        border_color = "var(--accent-blue)"
        safety = 30
        longterm = 55
        hedge = 15
        reason = "保留 6-12 个月应急现金，将其余长期闲置的积淀现金分批配置到被动宽基（国内+海外）和红利低波指基中，获取 6%~8% 的加权年化回报以战胜通胀风险。"

    return {
        'profileKey': profile_key,
        'profileTitle': profile_title,
        'profileDiag': profile_diag,
        'quote': quote,
        'borderColor': border_color,
        'safety': safety,
        'longterm': longterm,
        'hedge': hedge,
        'reason': reason,
        'isProhibitAggressive': is_prohibit_aggressive,
        'fourMoney': calculate_four_money_analysis(
            fd, total_assets, net_worth, leverage, repay_income_ratio,
            surplus_ratio, cash_coverage_months, risk_tolerance_code
        )
    }

"""家庭快速评估的 Python 实现，与 src/utils/familyAssessment.js 保持稳定契约一致。"""

from __future__ import annotations

from math import isfinite


RISK_LABELS = {1: "保守", 2: "稳健", 3: "均衡", 4: "成长", 5: "积极"}
LIFECYCLE_CONFIG = {
    "young_single": {"title": "年轻单身积累期", "emergencyMonths": 6},
    "dual_income_parent": {"title": "双薪育儿家庭", "emergencyMonths": 9},
    "single_income_dependents": {"title": "单薪多责任家庭", "emergencyMonths": 12},
    "self_employed_variable": {"title": "自雇及收入波动家庭", "emergencyMonths": 12},
    "home_purchase": {"title": "买房或换房准备期", "emergencyMonths": 9},
    "near_retirement": {"title": "临近退休家庭", "emergencyMonths": 12},
    "retired": {"title": "已退休家庭", "emergencyMonths": 18},
    "general": {"title": "家庭发展期", "emergencyMonths": 9},
}
PROFILE_CONFIG = {
    "high_debt_pressure": "高债务承压家庭",
    "cashflow_pressure": "现金流承压家庭",
    "property_business_concentrated": "高房产或经营资产集中家庭",
    "protection_gap": "保障缺口家庭",
}
REQUIRED_FIELDS = [
    ("household.adults", "家庭成年人数"),
    ("household.children", "子女人数"),
    ("household.primaryAge", "家庭主要决策者年龄"),
    ("household.incomeSourceType", "收入来源类型"),
    ("household.incomeStability", "收入稳定性"),
    ("cashflow.monthlyIncome", "税后月收入"),
    ("cashflow.essentialMonthlyExpense", "月必要支出"),
    ("cashflow.monthlyDebtPayment", "每月偿债额"),
    ("assets.cash", "随时可用现金"),
    ("assets.bonds", "稳健类金融资产"),
    ("assets.equities", "权益类金融资产"),
    ("assets.property", "房产估值"),
    ("debts.total", "负债总额"),
    ("debts.highInterest", "高息负债余额"),
    ("goals.expensesWithin1Year", "一年内确定支出"),
    ("goals.expenses1To3Years", "一至三年确定支出"),
    ("protection.basicMedicalCovered", "基础医疗保障情况"),
    ("risk.investmentHorizonYears", "投资期限"),
    ("risk.maxAcceptableLossPct", "最大可接受亏损"),
    ("risk.marketDropReaction", "市场下跌反应"),
]


def _provided(value):
    return value is not None and value != ""


def _number_or_none(value):
    if not _provided(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _non_negative_or_none(value):
    number = _number_or_none(value)
    return None if number is None else max(0.0, number)


def _rounded(value, digits=2):
    if value is None or not isfinite(value):
        return None
    return round(value, digits)


def _get_path(value, path):
    current = value
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize(input_data):
    household = input_data.get("household") or {}
    cashflow = input_data.get("cashflow") or {}
    assets = input_data.get("assets") or {}
    debts = input_data.get("debts") or {}
    goals = input_data.get("goals") or {}
    protection = input_data.get("protection") or {}
    risk = input_data.get("risk") or {}
    return {
        "household": {
            "adults": _non_negative_or_none(household.get("adults")),
            "children": _non_negative_or_none(household.get("children")),
            "elderlyDependents": _non_negative_or_none(household.get("elderlyDependents")),
            "primaryAge": _non_negative_or_none(household.get("primaryAge")),
            "incomeSourceType": household.get("incomeSourceType") if _provided(household.get("incomeSourceType")) else None,
            "incomeStability": household.get("incomeStability") if _provided(household.get("incomeStability")) else None,
            "yearsToRetirement": _non_negative_or_none(household.get("yearsToRetirement")),
            "retired": household.get("retired") is True,
        },
        "cashflow": {
            "monthlyIncome": _non_negative_or_none(cashflow.get("monthlyIncome")),
            "essentialMonthlyExpense": _non_negative_or_none(cashflow.get("essentialMonthlyExpense")),
            "monthlyDebtPayment": _non_negative_or_none(cashflow.get("monthlyDebtPayment")),
            "incomeShockPct": _non_negative_or_none(cashflow.get("incomeShockPct")),
        },
        "assets": {key: _non_negative_or_none(assets.get(key)) for key in (
            "cash", "bonds", "equities", "gold", "property", "business", "otherLiquid"
        )},
        "debts": {
            "total": _non_negative_or_none(debts.get("total")),
            "highInterest": _non_negative_or_none(debts.get("highInterest")),
            "highestRate": _non_negative_or_none(debts.get("highestRate")),
        },
        "goals": {
            "expensesWithin1Year": _non_negative_or_none(goals.get("expensesWithin1Year")),
            "expenses1To3Years": _non_negative_or_none(goals.get("expenses1To3Years")),
            "homePurchaseWithinYears": _non_negative_or_none(goals.get("homePurchaseWithinYears")),
        },
        "protection": {
            "basicMedicalCovered": protection.get("basicMedicalCovered") if isinstance(protection.get("basicMedicalCovered"), bool) else None,
            "lifeCoverageGap": _non_negative_or_none(protection.get("lifeCoverageGap")),
        },
        "risk": {
            "investmentHorizonYears": _non_negative_or_none(risk.get("investmentHorizonYears")),
            "maxAcceptableLossPct": _non_negative_or_none(risk.get("maxAcceptableLossPct")),
            "marketDropReaction": risk.get("marketDropReaction") if _provided(risk.get("marketDropReaction")) else None,
            "largestHoldingPct": _non_negative_or_none(risk.get("largestHoldingPct")),
            "singleMarketPct": _non_negative_or_none(risk.get("singleMarketPct")),
        },
    }


def _completeness(data):
    missing = [path for path, _ in REQUIRED_FIELDS if not _provided(_get_path(data, path))]
    labels = [label for path, label in REQUIRED_FIELDS if path in missing]
    completed = len(REQUIRED_FIELDS) - len(missing)
    score = int((completed / len(REQUIRED_FIELDS)) * 100 + 0.5)
    sufficient = (
        score >= 80
        and _provided(data["cashflow"]["monthlyIncome"])
        and _provided(data["cashflow"]["essentialMonthlyExpense"])
        and _provided(data["assets"]["cash"])
        and _provided(data["risk"]["maxAcceptableLossPct"])
    )
    return {
        "score": score, "completedFields": completed, "totalFields": len(REQUIRED_FIELDS),
        "missingFields": missing, "missingLabels": labels, "isSufficient": sufficient,
    }


def _lifecycle(data):
    household, goals = data["household"], data["goals"]
    key = "general"
    if household["retired"] or household["incomeSourceType"] == "pension":
        key = "retired"
    elif household["yearsToRetirement"] is not None and household["yearsToRetirement"] <= 5:
        key = "near_retirement"
    elif goals["homePurchaseWithinYears"] is not None and goals["homePurchaseWithinYears"] <= 3:
        key = "home_purchase"
    elif household["incomeSourceType"] == "self_employed" or household["incomeStability"] == "volatile":
        key = "self_employed_variable"
    elif (household["children"] or 0) + (household["elderlyDependents"] or 0) > 0 and household["incomeSourceType"] == "single_salary":
        key = "single_income_dependents"
    elif (household["children"] or 0) > 0 and household["incomeSourceType"] in ("dual_salary", "multiple"):
        key = "dual_income_parent"
    elif (household["adults"] or 0) == 1 and (household["primaryAge"] or 0) <= 35:
        key = "young_single"
    return {"key": key, **LIFECYCLE_CONFIG[key]}


def _metrics(data, lifecycle):
    cashflow, assets, debts, goals = data["cashflow"], data["assets"], data["debts"], data["goals"]
    monthly_need = None if cashflow["essentialMonthlyExpense"] is None else cashflow["essentialMonthlyExpense"] + (cashflow["monthlyDebtPayment"] or 0)
    surplus = None if cashflow["monthlyIncome"] is None or monthly_need is None else cashflow["monthlyIncome"] - monthly_need
    if cashflow["monthlyIncome"] in (None, 0):
        debt_service = 100 if (cashflow["monthlyDebtPayment"] or 0) > 0 else 0
    else:
        debt_service = (cashflow["monthlyDebtPayment"] or 0) / cashflow["monthlyIncome"] * 100
    liquid = sum((assets[key] or 0) for key in ("cash", "bonds", "equities", "gold", "otherLiquid"))
    total_assets = liquid + (assets["property"] or 0) + (assets["business"] or 0)
    net_worth = None if debts["total"] is None else total_assets - debts["total"]
    coverage = None if monthly_need is None else ((assets["cash"] or 0) / monthly_need if monthly_need > 0 else None)
    emergency = None if monthly_need is None else monthly_need * lifecycle["emergencyMonths"]
    property_concentration = (assets["property"] or 0) / total_assets * 100 if total_assets > 0 else 0
    business_ratio = ((assets["business"] or 0) / liquid * 100) if liquid > 0 else (100 if (assets["business"] or 0) > 0 else 0)
    equity_ratio = ((assets["equities"] or 0) / liquid * 100) if liquid > 0 else 0
    short_expenses = None if goals["expensesWithin1Year"] is None or goals["expenses1To3Years"] is None else goals["expensesWithin1Year"] + goals["expenses1To3Years"]
    return {
        "monthlyNeed": monthly_need, "monthlySurplus": surplus, "debtServiceRatio": _rounded(debt_service),
        "liquidFinancialAssets": liquid, "totalAssets": total_assets, "netWorth": net_worth,
        "cashCoverageMonths": _rounded(coverage), "emergencyTarget": emergency,
        "propertyConcentration": _rounded(property_concentration), "businessToLiquidRatio": _rounded(business_ratio),
        "equityRatio": _rounded(equity_ratio), "shortTermExpenses": short_expenses,
    }


def _constraints(data, metrics):
    ranks = {
        "high_interest_debt": 1, "negative_cashflow": 2, "debt_service_overload": 3,
        "emergency_reserve_critical": 4, "protection_gap": 5, "emergency_reserve_low": 6,
        "property_concentration": 7, "business_concentration": 8, "market_concentration": 9,
    }
    result = []

    def add(code, severity, title):
        result.append({"code": code, "severity": severity, "title": title, "priorityRank": ranks[code]})

    if metrics["monthlySurplus"] is not None and metrics["monthlySurplus"] <= 0:
        add("negative_cashflow", "critical", "月度现金流无法覆盖必要支出")
    if (data["debts"]["highInterest"] or 0) > 0 and ((data["debts"]["highestRate"] or 0) >= 8 or data["debts"]["highInterest"] >= (data["cashflow"]["monthlyIncome"] or 0)):
        add("high_interest_debt", "critical", "存在需要优先处理的高息负债")
    if (metrics["debtServiceRatio"] or 0) >= 50:
        add("debt_service_overload", "critical", "月度偿债占收入比例过高")
    if metrics["cashCoverageMonths"] is not None and metrics["cashCoverageMonths"] < 3:
        add("emergency_reserve_critical", "critical", "应急资金不足三个月")
    elif metrics["cashCoverageMonths"] is not None and metrics["cashCoverageMonths"] < 6:
        add("emergency_reserve_low", "warning", "应急资金低于基础安全线")
    if data["protection"]["basicMedicalCovered"] is False or (data["protection"]["lifeCoverageGap"] or 0) > 0:
        add("protection_gap", "warning", "家庭保障存在缺口")
    if metrics["propertyConcentration"] >= 70:
        add("property_concentration", "warning", "房产占家庭总资产比例较高")
    if metrics["businessToLiquidRatio"] >= 50:
        add("business_concentration", "warning", "经营资产相对可变现金融资产较高")
    if (data["risk"]["largestHoldingPct"] or 0) >= 40 or (data["risk"]["singleMarketPct"] or 0) >= 60:
        add("market_concentration", "warning", "金融资产存在单一持仓或市场集中")
    return sorted(result, key=lambda item: item["priorityRank"])


def _risk(data, metrics, constraints, completeness):
    if not completeness["isSufficient"]:
        pending = {"level": None, "label": "待补充资料"}
        return {"capacity": pending.copy(), "willingness": pending.copy(), "actualExposure": {**pending, "observedRiskLevel": None}, "finalLevel": None, "finalLabel": "待评估", "method": "三维最低值法"}
    capacity = 3
    if (data["risk"]["investmentHorizonYears"] or 0) >= 10: capacity += 1
    if (metrics["cashCoverageMonths"] or 0) >= 12: capacity += 1
    if data["household"]["incomeSourceType"] in ("dual_salary", "multiple"): capacity += 1
    if data["household"]["incomeStability"] == "volatile" or data["household"]["incomeSourceType"] == "self_employed": capacity -= 1
    if (metrics["debtServiceRatio"] or 0) >= 30: capacity -= 1
    if data["household"]["retired"] or data["household"]["incomeSourceType"] == "pension": capacity = min(capacity, 2)
    if any(item["severity"] == "critical" for item in constraints): capacity = 1
    capacity = min(5, max(1, capacity))
    loss = data["risk"]["maxAcceptableLossPct"] or 0
    willingness = 1 if loss < 10 else 2 if loss < 15 else 3 if loss < 25 else 4 if loss < 35 else 5
    if data["risk"]["marketDropReaction"] == "panic_sell": willingness = 1
    if data["risk"]["marketDropReaction"] == "reduce": willingness = min(willingness, 2)
    ratio = metrics["equityRatio"]
    observed = 1 if ratio < 20 else 2 if ratio < 40 else 3 if ratio < 60 else 4 if ratio < 75 else 5
    exposure = 2 if ratio >= 80 else 3 if ratio >= 65 else 5
    if any(item["code"] == "market_concentration" for item in constraints): exposure = min(exposure, 2)
    if any(item["code"] in ("property_concentration", "business_concentration") for item in constraints): exposure = min(exposure, 3)
    if any(item["severity"] == "critical" for item in constraints): exposure = 1
    final = min(capacity, willingness, exposure)
    return {
        "capacity": {"level": capacity, "label": RISK_LABELS[capacity]},
        "willingness": {"level": willingness, "label": RISK_LABELS[willingness]},
        "actualExposure": {"level": exposure, "label": RISK_LABELS[exposure], "observedRiskLevel": observed, "equityRatio": ratio},
        "finalLevel": final, "finalLabel": RISK_LABELS[final], "method": "三维最低值法",
    }


def _investable(data, metrics, lifecycle, completeness, constraints):
    if not completeness["isSufficient"] or metrics["shortTermExpenses"] is None or metrics["emergencyTarget"] is None:
        return {"safeUpperBound": None, "liquidFinancialAssets": metrics["liquidFinancialAssets"], "reservedForEmergency": metrics["emergencyTarget"], "reservedForShortTermGoals": metrics["shortTermExpenses"], "reservedForHighInterestDebt": data["debts"]["highInterest"], "emergencyMonths": lifecycle["emergencyMonths"], "status": "insufficient_information"}
    stopped = any(item["code"] == "negative_cashflow" for item in constraints)
    upper = 0 if stopped else max(0, metrics["liquidFinancialAssets"] - metrics["emergencyTarget"] - metrics["shortTermExpenses"] - (data["debts"]["highInterest"] or 0))
    return {"safeUpperBound": round(upper), "liquidFinancialAssets": round(metrics["liquidFinancialAssets"]), "reservedForEmergency": round(metrics["emergencyTarget"]), "reservedForShortTermGoals": round(metrics["shortTermExpenses"]), "reservedForHighInterestDebt": round(data["debts"]["highInterest"] or 0), "emergencyMonths": lifecycle["emergencyMonths"], "status": "available" if upper > 0 else "no_safe_surplus"}


def _allocation(risk, constraints):
    if risk["finalLevel"] is None:
        return None
    ranges = {
        1: {"safety": [60, 75], "stable": [15, 25], "growth": [0, 10], "hedge": [5, 10]},
        2: {"safety": [45, 60], "stable": [20, 30], "growth": [10, 20], "hedge": [5, 10]},
        3: {"safety": [30, 45], "stable": [20, 30], "growth": [25, 40], "hedge": [5, 10]},
        4: {"safety": [20, 35], "stable": [15, 25], "growth": [40, 55], "hedge": [5, 10]},
        5: {"safety": [15, 25], "stable": [10, 20], "growth": [55, 70], "hedge": [5, 10]},
    }[risk["finalLevel"]]
    if any(item["code"] in ("high_interest_debt", "debt_service_overload", "negative_cashflow") for item in constraints):
        ranges["growth"] = [0, 0]
    labels = {"safety": "安全流动层", "stable": "稳健收益层", "growth": "长期成长层", "hedge": "风险对冲层"}
    result = {key: {"min": value[0], "max": value[1], "label": labels[key]} for key, value in ranges.items()}
    result["note"] = "区间用于家庭大类资产规划，不构成具体产品推荐。"
    return result


def _stress(data, metrics, constraints):
    if metrics["monthlyNeed"] is None or metrics["monthlyNeed"] <= 0:
        return {"cashCoverageMonths": metrics["cashCoverageMonths"], "stressedCoverageMonths": None, "status": "insufficient_information", "message": "补充必要支出后才能计算家庭现金流压力。"}
    shock = min(100, max(0, 50 if data["cashflow"]["incomeShockPct"] is None else data["cashflow"]["incomeShockPct"]))
    burden = metrics["monthlyNeed"] + (data["cashflow"]["monthlyIncome"] or 0) * shock / 100
    stressed = (data["assets"]["cash"] or 0) / burden if burden > 0 else None
    concentrated = any("concentration" in item["code"] for item in constraints)
    critical = any(item["severity"] == "critical" for item in constraints)
    status = "critical" if critical else "warning" if stressed is not None and stressed < 6 else "warning" if concentrated else "resilient"
    message = "现金流或债务红线会放大收入中断冲击，应先修复家庭安全底座。" if status == "critical" else f"按收入下降 {shock:g}% 的保守情景，现金压力覆盖约 {_rounded(stressed, 1)} 个月。"
    if concentrated: message += " 房产、经营或市场集中会降低应急变现能力。"
    return {"cashCoverageMonths": metrics["cashCoverageMonths"], "stressedCoverageMonths": _rounded(stressed), "incomeShockPct": shock, "status": status, "message": message}


def _profile(lifecycle, constraints):
    codes = [item["code"] for item in constraints]
    key = lifecycle["key"]
    if any(code in ("high_interest_debt", "debt_service_overload") for code in codes): key = "high_debt_pressure"
    elif any(code in ("negative_cashflow", "emergency_reserve_critical") for code in codes): key = "cashflow_pressure"
    elif any(code in ("property_concentration", "business_concentration") for code in codes): key = "property_business_concentrated"
    elif "protection_gap" in codes: key = "protection_gap"
    return {"key": key, "title": PROFILE_CONFIG.get(key, lifecycle["title"]), "lifecycleKey": lifecycle["key"], "constraintCodes": codes}


def _actions(completeness, constraints, lifecycle, risk):
    mapping = {
        "high_interest_debt": ("repay_high_interest_debt", "优先处理高息负债", "暂停新增高波动配置，制定明确的高息负债清偿顺序。"),
        "negative_cashflow": ("repair_cashflow", "先修复月度现金流", "压降非必要支出或增加稳定收入，恢复持续结余后再安排长期投资。"),
        "debt_service_overload": ("reduce_debt_service", "降低月度偿债压力", "优先降低月供占收入比例，避免收入中断时出现资金链风险。"),
        "emergency_reserve_critical": ("build_emergency_reserve", "补足应急资金", f"先建立至少 {lifecycle['emergencyMonths']} 个月必要支出的安全储备。"),
        "emergency_reserve_low": ("build_emergency_reserve", "提高应急资金覆盖", f"逐步将应急储备提升至 {lifecycle['emergencyMonths']} 个月必要支出。"),
        "protection_gap": ("close_protection_gap", "补齐基础保障缺口", "先覆盖可能击穿家庭资产负债表的医疗和家庭责任风险。"),
        "property_concentration": ("reduce_property_concentration", "降低房产集中风险", "新增结余优先补充高流动性金融资产，避免继续放大不动产集中。"),
        "business_concentration": ("separate_business_assets", "隔离经营与家庭资产", "建立家庭安全资金与经营周转资金的独立边界。"),
        "market_concentration": ("diversify_financial_exposure", "降低金融资产集中度", "按市场和风险来源分散长期资产，设置单一持仓上限。"),
    }
    lifecycle_actions = {
        "young_single": ("set_long_term_plan", "建立长期积累计划", "在安全储备完成后，以长期目标和固定投入形成积累纪律。"),
        "dual_income_parent": ("fund_rigid_goals", "隔离育儿与刚性目标资金", "把教育、医疗等确定支出与长期成长资金分开管理。"),
        "single_income_dependents": ("protect_primary_income", "保护家庭主收入来源", "提高应急储备并检视主收入者责任保障。"),
        "self_employed_variable": ("smooth_variable_income", "建立淡旺季现金流规则", "用较长周期估算可支配结余，隔离经营和家庭资金。"),
        "home_purchase": ("isolate_home_funds", "硬隔离购房资金", "三年内确定使用的首付及税费资金不承担权益市场波动。"),
        "near_retirement": ("prepare_retirement_runway", "建立退休支取跑道", "逐步准备退休初期现金与稳健资产，降低回撤顺序风险。"),
        "retired": ("protect_retirement_withdrawals", "保障退休持续支取", "先验证生活、医疗和长寿情景下的现金流覆盖。"),
        "general": ("clarify_family_goals", "明确家庭目标顺序", "按刚性程度和使用期限为目标排序并隔离资金。"),
    }
    result = []
    if not completeness["isSufficient"]:
        result.append({"code": "complete_information", "title": "先补齐关键家庭资料", "detail": f"仍需补充：{'、'.join(completeness['missingLabels'][:4]) or '关键风险信息'}。", "priority": "critical"})
    for item in constraints:
        code, title, detail = mapping.get(item["code"], ("review_constraint", item["title"], "优先处理该项约束后再提高风险暴露。"))
        result.append({"code": code, "title": title, "detail": detail, "priority": item["severity"]})
    code, title, detail = lifecycle_actions[lifecycle["key"]]
    result.append({"code": code, "title": title, "detail": detail, "priority": "normal"})
    if risk["finalLevel"] is not None:
        result.append({"code": "align_risk_exposure", "title": "按最低风险维度校准配置", "detail": f"风险能力、意愿与现有暴露适配度取最低值，当前建议以“{risk['finalLabel']}”作为上限。", "priority": "normal"})
    result.append({"code": "review_quarterly", "title": "在家庭情况变化后复评", "detail": "收入、负债、家庭成员或重大目标变化时重新评估，至少每季度复核一次。", "priority": "normal"})
    unique = []
    seen = set()
    for item in result:
        if item["code"] not in seen:
            seen.add(item["code"])
            unique.append(item)
    return unique[:3]


def assess_family(input_data=None):
    """返回与前端 assessFamily 相同的稳定业务契约。"""
    data = _normalize(input_data or {})
    completeness = _completeness(data)
    lifecycle = _lifecycle(data)
    metrics = _metrics(data, lifecycle)
    constraints = _constraints(data, metrics)
    risk = _risk(data, metrics, constraints, completeness)
    return {
        "version": 1,
        "normalized": data,
        "lifecycle": lifecycle,
        "profile": _profile(lifecycle, constraints),
        "completeness": completeness,
        "constraints": constraints,
        "redLines": [item for item in constraints if item["severity"] == "critical"],
        "metrics": metrics,
        "risk": risk,
        "investable": _investable(data, metrics, lifecycle, completeness, constraints),
        "allocationRanges": _allocation(risk, constraints),
        "stress": _stress(data, metrics, constraints),
        "topActions": _actions(completeness, constraints, lifecycle, risk),
        "disclaimer": "本结果用于家庭财务规划与风险教育，不构成具体投资产品建议。",
    }

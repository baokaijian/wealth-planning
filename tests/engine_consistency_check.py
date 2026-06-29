import json
import math
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("engine_consistency_cases.json")

sys.path.insert(0, str(REPO_ROOT))
import portfolio_engine  # noqa: E402


def load_assets():
    assets_list = json.loads((REPO_ROOT / "assets.json").read_text(encoding="utf-8"))
    assets = {}
    for item in assets_list:
        assets[item["code"]] = {
            **item,
            "yield": item["estimated_yield"],
            "price": 0.0,
            "months": {int(k): v for k, v in item.get("distribution_months", {}).items()},
        }
    return assets


def family_metrics(fd):
    total_assets = (
        fd["ast-cash"] + fd["ast-mmf"] + fd["ast-ashare"] + fd["ast-hk"] +
        fd["ast-overseas"] + fd["ast-gold"] + fd["ast-house"] + fd["ast-insurance"] + fd["ast-others"]
    )
    total_liabilities = fd["debt-house"] + fd["debt-car"] + fd["debt-consumption"] + fd["debt-biz"]
    net_worth = total_assets - total_liabilities
    leverage = total_liabilities / total_assets if total_assets > 0 else 0.0
    repay_income_ratio = fd["debt-monthly-repay"] / fd["f-monthly-income"] if fd["f-monthly-income"] > 0 else 0.0
    surplus_ratio = fd["f-surplus-income"] / fd["f-monthly-income"] if fd["f-monthly-income"] > 0 else 0.0
    liquid_cash = fd["ast-cash"] + fd["ast-mmf"]
    monthly_essential = max(fd["f-essential-expense"], fd["f-fixed-expense"] * 0.7, 1.0)
    cash_coverage_months = liquid_cash / (monthly_essential + fd["debt-monthly-repay"])
    investable_assets = fd["ast-cash"] + fd["ast-mmf"] + fd["ast-ashare"] + fd["ast-hk"] + fd["ast-overseas"] + fd["ast-gold"] + fd["ast-others"]
    return total_assets, net_worth, leverage, repay_income_ratio, surplus_ratio, cash_coverage_months, investable_assets


def run_python_case(case):
    assets = load_assets()
    weights = {code: asset["weight"] for code, asset in assets.items()}
    withdraw = case["targetMonthlyWan"] * 10000.0
    money_rate = case["moneyMarketRatePct"] / 100.0
    feasibility = portfolio_engine.calculate_cashflow_feasibility(
        36,
        withdraw,
        case["bufferSeed"],
        case["principal"],
        weights,
        assets,
        money_rate,
        case["startMonth"],
        case["stableIncomeDrop"],
        case["delayMonths"],
        case["pauseDividendYear"],
    )
    stress = portfolio_engine.run_stress_test(
        weights,
        assets,
        max(case["principal"] - case["bufferSeed"], 0.0),
        withdraw,
        case["stressBufferMonths"],
        money_rate,
        case["stressParams"],
    )
    fd = case["familyData"]
    total_assets, net_worth, leverage, repay_income_ratio, surplus_ratio, cash_coverage_months, investable_assets = family_metrics(fd)
    family = portfolio_engine.evaluate_family_profile(
        fd,
        investable_assets,
        net_worth,
        total_assets,
        leverage,
        repay_income_ratio,
        surplus_ratio,
        cash_coverage_months,
        [],
        int(fd["inv-drawdown"]),
    )
    return {
        "name": case["name"],
        "safeMonthlyWithdrawWan": feasibility["safeMonthlyWithdrawWan"],
        "healthScore": family["fourMoney"]["score"],
        "breachedAtMonth": stress["breachedAtMonth"],
        "minStressedBuffer": stress["minStressedBuffer"],
    }


def compare_value(key, py_val, js_val, tolerance=1e-6):
    if py_val is None or js_val is None:
        return py_val == js_val
    if isinstance(py_val, (int, float)) and isinstance(js_val, (int, float)):
        return math.isclose(float(py_val), float(js_val), rel_tol=tolerance, abs_tol=tolerance)
    return py_val == js_val


def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    node_output = subprocess.check_output(
        ["node", str(Path(__file__).with_name("engine_consistency_check.js")), str(CASES_PATH)],
        cwd=REPO_ROOT,
        text=True,
    )
    js_results = {item["name"]: item for item in json.loads(node_output)}
    py_results = {case["name"]: run_python_case(case) for case in cases}

    diffs = []
    keys = ["safeMonthlyWithdrawWan", "healthScore", "breachedAtMonth", "minStressedBuffer"]
    for name, py_result in py_results.items():
        js_result = js_results.get(name)
        if not js_result:
            diffs.append({"case": name, "metric": "case", "python": "present", "javascript": "missing"})
            continue
        for key in keys:
            if not compare_value(key, py_result.get(key), js_result.get(key)):
                diffs.append({"case": name, "metric": key, "python": py_result.get(key), "javascript": js_result.get(key)})

    print(json.dumps({"python": list(py_results.values()), "javascript": list(js_results.values()), "diffs": diffs}, ensure_ascii=False, indent=2))
    if diffs:
        print("发现双引擎差异：请人工确认是否来自 JS/Python 公式实现差异，脚本不会自动统一逻辑。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

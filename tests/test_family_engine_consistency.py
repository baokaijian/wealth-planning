import json
import subprocess
import unittest
from pathlib import Path

from family_assessment import assess_family


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_HELPER = REPO_ROOT / "tests" / "helpers" / "run_family_assessment.mjs"


HEALTHY_BASE = {
    "household": {
        "adults": 2, "children": 1, "elderlyDependents": 0, "primaryAge": 36,
        "incomeSourceType": "dual_salary", "incomeStability": "stable",
        "yearsToRetirement": 24,
    },
    "cashflow": {
        "monthlyIncome": 36000, "essentialMonthlyExpense": 15000,
        "monthlyDebtPayment": 5000, "incomeShockPct": 50,
    },
    "assets": {
        "cash": 260000, "bonds": 180000, "equities": 360000, "gold": 60000,
        "property": 1800000, "business": 0, "otherLiquid": 0,
    },
    "debts": {"total": 600000, "highInterest": 0, "highestRate": 3.6},
    "goals": {
        "expensesWithin1Year": 30000, "expenses1To3Years": 100000,
        "homePurchaseWithinYears": None,
    },
    "protection": {"basicMedicalCovered": True, "lifeCoverageGap": 0},
    "risk": {
        "investmentHorizonYears": 12, "maxAcceptableLossPct": 20,
        "marketDropReaction": "hold", "largestHoldingPct": 30, "singleMarketPct": 45,
    },
}


def clone(value):
    return json.loads(json.dumps(value))


def js_assessment(input_data):
    completed = subprocess.run(
        ["node", str(NODE_HELPER)],
        cwd=REPO_ROOT,
        input=json.dumps(input_data),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def stable_contract(result):
    ranges = result.get("allocationRanges")
    return {
        "lifecycle": result["lifecycle"]["key"],
        "profile": result["profile"]["key"],
        "completeness": {
            "score": result["completeness"]["score"],
            "missingFields": result["completeness"]["missingFields"],
            "isSufficient": result["completeness"]["isSufficient"],
        },
        "constraintCodes": [item["code"] for item in result["constraints"]],
        "redLineCodes": [item["code"] for item in result["redLines"]],
        "risk": {
            "capacity": result["risk"]["capacity"]["level"],
            "willingness": result["risk"]["willingness"]["level"],
            "exposure": result["risk"]["actualExposure"]["level"],
            "final": result["risk"]["finalLevel"],
        },
        "investable": {
            "safeUpperBound": result["investable"]["safeUpperBound"],
            "status": result["investable"]["status"],
        },
        "allocationRanges": None if ranges is None else {
            key: {"min": ranges[key]["min"], "max": ranges[key]["max"]}
            for key in ("safety", "stable", "growth", "hedge")
        },
        "actionCodes": [item["code"] for item in result["topActions"]],
    }


class FamilyEngineConsistencyTests(unittest.TestCase):
    def test_python_and_javascript_share_stable_contract(self):
        cases = []

        cases.append(HEALTHY_BASE)

        zero_case = clone(HEALTHY_BASE)
        zero_case["cashflow"].update(monthlyIncome=0, monthlyDebtPayment=0)
        zero_case["assets"].update(cash=0, property=0)
        zero_case["debts"].update(total=0)
        zero_case["goals"].update(expensesWithin1Year=0, expenses1To3Years=0)
        cases.append(zero_case)

        debt_case = clone(HEALTHY_BASE)
        debt_case["cashflow"].update(monthlyIncome=20000, essentialMonthlyExpense=10000, monthlyDebtPayment=12000)
        debt_case["debts"].update(highInterest=100000, highestRate=12)
        cases.append(debt_case)

        incomplete_case = {
            "household": {"adults": 1, "children": 0, "primaryAge": 27},
            "cashflow": {"monthlyIncome": None},
            "assets": {"cash": 0},
        }
        cases.append(incomplete_case)

        lifecycle_overrides = [
            {"household": {"adults": 1, "children": 0, "primaryAge": 28, "incomeSourceType": "single_salary"}},
            {"household": {"children": 2, "elderlyDependents": 1, "incomeSourceType": "single_salary"}},
            {"household": {"incomeSourceType": "self_employed", "incomeStability": "volatile"}},
            {"goals": {"homePurchaseWithinYears": 2}},
            {"household": {"yearsToRetirement": 3}},
            {"household": {"primaryAge": 67, "incomeSourceType": "pension", "retired": True, "yearsToRetirement": 0}},
        ]
        for override in lifecycle_overrides:
            case = clone(HEALTHY_BASE)
            for section, values in override.items():
                case.setdefault(section, {}).update(values)
            cases.append(case)

        for index, case in enumerate(cases):
            with self.subTest(case=index):
                self.assertEqual(
                    stable_contract(assess_family(case)),
                    stable_contract(js_assessment(case)),
                )


if __name__ == "__main__":
    unittest.main()

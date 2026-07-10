import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ASSET_FIELDS = {
    "code", "name", "type", "role", "target_index_code", "market",
    "volatility_level", "income_type", "rebalance_band", "weight",
    "estimated_yield", "estimated_return", "distribution_months",
    "strategy_note", "risk_note"
}


def main():
    assets = json.loads((ROOT / "assets.json").read_text(encoding="utf-8"))
    live = json.loads((ROOT / "live_data.json").read_text(encoding="utf-8"))
    history = json.loads((ROOT / "valuation_history.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "planning_rules.json").read_text(encoding="utf-8"))
    errors = []
    codes = set()
    for index, asset in enumerate(assets):
        missing = REQUIRED_ASSET_FIELDS - set(asset)
        if missing:
            errors.append(f"assets[{index}] 缺少字段: {sorted(missing)}")
        code = str(asset.get("code", ""))
        if code in codes:
            errors.append(f"资产代码重复: {code}")
        codes.add(code)
        months_total = sum(float(value) for value in asset.get("distribution_months", {}).values())
        # 月度比例通常保留三位小数，允许累计产生不超过 0.5% 的舍入差。
        if asset.get("distribution_months") and abs(months_total - 1.0) > 0.005:
            errors.append(f"{code} distribution_months 合计为 {months_total}")
    total_weight = sum(float(asset.get("weight", 0.0)) for asset in assets)
    if abs(total_weight - 100.0) > 1e-8:
        errors.append(f"默认权重合计为 {total_weight}，应为 100")
    if live.get("status") != "success" or not isinstance(live.get("data"), dict):
        errors.append("live_data.json 状态或 data 结构无效")
    missing_live = codes - set(live.get("data", {}))
    if missing_live:
        errors.append(f"live_data.json 缺少资产: {sorted(missing_live)}")
    for index, item in enumerate(history):
        if not item.get("index_code") or not item.get("date"):
            errors.append(f"valuation_history[{index}] 缺少 index_code/date")
    if not rules.get("family_risk") or not rules.get("concentration"):
        errors.append("planning_rules.json 缺少 family_risk/concentration")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"数据校验通过：{len(assets)} 个资产，默认权重 {total_weight:.1f}%，{len(history)} 条估值历史。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

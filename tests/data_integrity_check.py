import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ASSET_FIELDS = {
    "code", "name", "type", "role", "target_index_code", "market",
    "volatility_level", "income_type", "rebalance_band", "weight",
    "estimated_yield", "estimated_return", "distribution_months",
    "strategy_note", "risk_note"
}
VERIFIED_VALUATION_CODES = {
    "000015", "000300", "000510", "000905", "000688", "932039", "H30269", "HSHYLV"
}
VERIFIED_PERCENTILE_FIELDS = {
    "pe_percentile_3y", "pb_percentile_3y", "dividend_yield_percentile_3y"
}


def main():
    assets = json.loads((ROOT / "assets.json").read_text(encoding="utf-8"))
    live = json.loads((ROOT / "live_data.json").read_text(encoding="utf-8"))
    history = json.loads((ROOT / "valuation_history.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "planning_rules.json").read_text(encoding="utf-8"))
    presets = json.loads((ROOT / "strategy_presets.json").read_text(encoding="utf-8"))
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
    for code, record in live.get("data", {}).items():
        if not isinstance(record.get("price"), (int, float)) or record.get("price", 0) <= 0:
            errors.append(f"live_data.json {code} 缺少有效价格")
        if not record.get("price_as_of"):
            errors.append(f"live_data.json {code} 缺少价格时间")
        if record.get("yield_method") == "implied_from_reference_distribution":
            errors.append(f"live_data.json {code} 仍使用参考价格反推收益率")
    for index, item in enumerate(history):
        if not item.get("index_code") or not item.get("date"):
            errors.append(f"valuation_history[{index}] 缺少 index_code/date")
        for field in VERIFIED_PERCENTILE_FIELDS & set(item):
            value = item.get(field)
            if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                errors.append(f"valuation_history[{index}] {field} 不在 0-100")
    history_codes = {str(item.get("index_code")) for item in history}
    if {"588000", "HSHDY"} & history_codes:
        errors.append("valuation_history.json 仍使用 ETF/错误别名作为指数代码")
    asset_targets = {str(asset.get("target_index_code")) for asset in assets if asset.get("target_index_code")}
    missing_target_history = (asset_targets - {"NDX"}) - history_codes
    if missing_target_history:
        errors.append(f"估值历史缺少目标指数: {sorted(missing_target_history)}")
    latest_verified = {
        code: max((item for item in history if item.get("index_code") == code), key=lambda item: item.get("date", ""), default={})
        for code in VERIFIED_VALUATION_CODES
    }
    for code, item in latest_verified.items():
        if item.get("date") != "2026-07-20" or not VERIFIED_PERCENTILE_FIELDS <= set(item):
            errors.append(f"{code} 缺少 2026-07-20 已验证估值或三年百分位")
    if not rules.get("family_risk") or not rules.get("concentration"):
        errors.append("planning_rules.json 缺少 family_risk/concentration")
    preset_items = presets.get("presets", {})
    if set(preset_items) != {"conservative", "balanced", "aggressive"}:
        errors.append("strategy_presets.json 缺少三套标准方案")
    for preset_id, preset in preset_items.items():
        weights = preset.get("weights", {})
        if set(weights) != codes:
            errors.append(f"{preset_id} 的资产代码与 assets.json 不一致")
        if abs(sum(float(value) for value in weights.values()) - 100.0) > 1e-8:
            errors.append(f"{preset_id} 权重合计不为 100")
    backtest = presets.get("backtest") or {}
    if set((backtest.get("results") or {})) != set(preset_items):
        errors.append("strategy_presets.json 缺少完整回测结果")
    if (backtest.get("quote_alignment_check") or {}).get("status") != "passed":
        errors.append("历史行情与最新行情对齐检查未通过")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"数据校验通过：{len(assets)} 个资产，默认权重 {total_weight:.1f}%，{len(history)} 条估值历史。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
import math
import os
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_PATH = os.path.join(SCRIPT_DIR, "assets.json")
PRESETS_PATH = os.path.join(SCRIPT_DIR, "strategy_presets.json")
LIVE_DATA_PATH = os.path.join(SCRIPT_DIR, "live_data.json")
HISTORY_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
USER_AGENT = "Mozilla/5.0 (compatible; wealth-planning-backtest/1.0)"
TRADING_DAYS = 252
FEE_BPS = 3.0


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def fetch_adjusted_history(code):
    sec_id = f"sh{code}"
    params = urllib.parse.urlencode({"param": f"{sec_id},day,,,2000,qfq"})
    request = urllib.request.Request(
        f"{HISTORY_URL}?{params}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://gu.qq.com/",
            "Connection": "close",
        },
    )
    payload = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.0 * (attempt + 1))
    data = (payload.get("data") or {}).get(sec_id) or {}
    rows = data.get("qfqday") or data.get("day") or []
    history = {}
    for row in rows:
        if len(row) < 3:
            continue
        try:
            close = float(row[2])
        except ValueError:
            continue
        if close > 0:
            history[row[0]] = close
    if len(history) < 2:
        raise RuntimeError(f"insufficient adjusted history for {code}")
    return history


def common_dates(histories, codes):
    dates = set(histories[codes[0]])
    for code in codes[1:]:
        dates.intersection_update(histories[code])
    return sorted(dates)


def calculate_metrics(dates, portfolio_values, daily_returns, total_cost):
    initial_value = portfolio_values[0]
    final_value = portfolio_values[-1]
    total_return = final_value / initial_value - 1.0
    elapsed_days = max(
        (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[0], "%Y-%m-%d")).days,
        1,
    )
    cagr = (final_value / initial_value) ** (365.25 / elapsed_days) - 1.0
    volatility = statistics.stdev(daily_returns) * math.sqrt(TRADING_DAYS) if len(daily_returns) > 1 else 0.0
    peak = portfolio_values[0]
    max_drawdown = 0.0
    for value in portfolio_values:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1.0)
    return {
        "start_date": dates[0],
        "end_date": dates[-1],
        "trading_days": len(dates),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "annualized_volatility_pct": round(volatility * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "ending_value_from_100": round(final_value / initial_value * 100, 2),
        "estimated_total_cost_from_100": round(total_cost, 4),
    }


def run_strategy_backtest(weights, histories):
    active_weights = {code: float(weight) for code, weight in weights.items() if float(weight) > 0}
    total_weight = sum(active_weights.values())
    if abs(total_weight - 100.0) > 1e-8:
        raise ValueError(f"active strategy weights sum to {total_weight}, expected 100")
    codes = sorted(active_weights)
    dates = common_dates(histories, codes)
    if len(dates) < 2:
        raise RuntimeError("strategy has insufficient common trading dates")

    fee_rate = FEE_BPS / 10000.0
    initial_value = 100.0 * (1.0 - fee_rate)
    values = {code: initial_value * active_weights[code] / 100.0 for code in codes}
    total_cost = 100.0 * fee_rate
    portfolio_values = [sum(values.values())]
    daily_returns = []

    for index in range(1, len(dates)):
        previous_date = dates[index - 1]
        current_date = dates[index]
        if current_date[:4] != previous_date[:4]:
            current_total = sum(values.values())
            current_weights = {code: values[code] / current_total for code in codes}
            turnover = sum(abs(current_weights[code] - active_weights[code] / 100.0) for code in codes) / 2.0
            rebalance_cost = current_total * turnover * fee_rate
            total_cost += rebalance_cost
            investable_total = current_total - rebalance_cost
            values = {
                code: investable_total * active_weights[code] / 100.0
                for code in codes
            }

        previous_total = sum(values.values())
        for code in codes:
            values[code] *= histories[code][current_date] / histories[code][previous_date]
        current_total = sum(values.values())
        daily_returns.append(current_total / previous_total - 1.0)
        portfolio_values.append(current_total)

    return calculate_metrics(dates, portfolio_values, daily_returns, total_cost)


def quote_cross_check(histories, live_payload):
    checks = {}
    for code, history in histories.items():
        last_date = max(history)
        adjusted_close = history[last_date]
        live_record = (live_payload.get("data") or {}).get(code) or {}
        live_price = live_record.get("price")
        same_date = str(live_record.get("price_as_of", "")).startswith(last_date)
        difference_pct = None
        if same_date and isinstance(live_price, (int, float)) and live_price > 0:
            difference_pct = abs(float(live_price) / adjusted_close - 1.0) * 100
        checks[code] = {
            "history_end": last_date,
            "history_close": adjusted_close,
            "quote_price": live_price,
            "same_trading_date": same_date,
            "absolute_difference_pct": round(difference_pct, 4) if difference_pct is not None else None,
        }
    comparable = [item["absolute_difference_pct"] for item in checks.values() if item["absolute_difference_pct"] is not None]
    return {
        "status": "passed" if len(comparable) == len(histories) and max(comparable, default=0) <= 0.5 else "review_required",
        "compared_assets": len(comparable),
        "max_absolute_difference_pct": max(comparable, default=None),
        "details": checks,
    }


def main():
    assets = load_json(ASSETS_PATH)
    presets_payload = load_json(PRESETS_PATH)
    live_payload = load_json(LIVE_DATA_PATH)
    asset_codes = [str(item["code"]) for item in assets]
    histories = {}
    for code in asset_codes:
        histories[code] = fetch_adjusted_history(code)
        time.sleep(0.35)

    strategy_results = {}
    for preset_id, preset in presets_payload["presets"].items():
        strategy_results[preset_id] = {
            "name": preset["name"],
            **run_strategy_backtest(preset["weights"], histories),
        }

    data_ranges = {
        code: {
            "start_date": min(history),
            "end_date": max(history),
            "observations": len(history),
        }
        for code, history in histories.items()
    }
    presets_payload["backtest"] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "methodology": {
            "history": "public daily forward-adjusted closing prices",
            "return_scope": "adjusted-price total-return proxy before investor taxes",
            "portfolio_construction": "initial target weights with rebalancing on the first common trading day of each calendar year",
            "transaction_cost_bps_one_way": FEE_BPS,
            "start_rule": "latest first-available date among all positive-weight assets in each preset",
            "missing_data_rule": "only dates present for every positive-weight asset are used",
            "limitations": "short histories for newer ETFs constrain the common period; past performance is not a forecast",
        },
        "data_ranges": data_ranges,
        "quote_alignment_check": quote_cross_check(histories, live_payload),
        "results": strategy_results,
    }

    with open(PRESETS_PATH, "w", encoding="utf-8") as file:
        json.dump(presets_payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"Backtest updated for {len(strategy_results)} strategies and {len(histories)} assets.")
    for preset_id, result in strategy_results.items():
        print(
            f"{preset_id}: {result['start_date']} to {result['end_date']}, "
            f"CAGR {result['cagr_pct']:.2f}%, max drawdown {result['max_drawdown_pct']:.2f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

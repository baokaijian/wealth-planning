import json
import os
import re
import urllib.request
from datetime import datetime, timedelta


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_PATH = os.path.join(SCRIPT_DIR, "assets.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "live_data.json")
QUOTE_URL = "https://qt.gtimg.cn/q={}"
DIVIDEND_URL = "https://fundf10.eastmoney.com/fhsp_{}.html"
USER_AGENT = "Mozilla/5.0 (compatible; wealth-planning-data-refresh/1.0)"

# 东方财富“分红送配详情”表格的两种现金分红格式：
#   每10份派现金1.4300元  -> 每份 0.143 元（除以 10）
#   每份派现金0.0500元    -> 每份 0.05 元（除以 1）
_DIVIDEND_PATTERNS = (
    (
        re.compile(
            r"<tr><td>\d{4}年</td><td>(\d{4}-\d{2}-\d{2})</td>"
            r"<td>(\d{4}-\d{2}-\d{2})</td><td>每10份派现金([0-9.]+)元</td>"
        ),
        10.0,
    ),
    (
        re.compile(
            r"<tr><td>\d{4}年</td><td>(\d{4}-\d{2}-\d{2})</td>"
            r"<td>(\d{4}-\d{2}-\d{2})</td><td>每份派现金([0-9.]+)元</td>"
        ),
        1.0,
    ),
)


def load_assets():
    with open(ASSETS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def exchange_prefix(code):
    return "sh" if str(code).startswith(("5", "6")) else "sz"


def fetch_text(url, encoding="utf-8"):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode(encoding, errors="replace")


def parse_quote_time(raw_value):
    try:
        return datetime.strptime(raw_value, "%Y%m%d%H%M%S")
    except (TypeError, ValueError):
        return None


def fetch_quotes(assets):
    sec_ids = [f"{exchange_prefix(item['code'])}{item['code']}" for item in assets]
    payload = fetch_text(QUOTE_URL.format(",".join(sec_ids)), "gbk")
    quotes = {}

    for line in payload.splitlines():
        if "=" not in line:
            continue
        variable, content = line.split("=", 1)
        code = variable.strip().replace("v_sh", "").replace("v_sz", "")
        fields = content.strip().strip('";').split("~")
        if len(fields) < 35:
            continue
        try:
            price = float(fields[3])
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue

        quote_time = parse_quote_time(fields[30])
        quotes[code] = {
            "name": fields[1],
            "price": price,
            "previous_close": float(fields[4]) if fields[4] else None,
            "open": float(fields[5]) if fields[5] else None,
            "high": float(fields[33]) if fields[33] else None,
            "low": float(fields[34]) if fields[34] else None,
            "price_source": "tencent_realtime_quote",
            "price_as_of": quote_time.strftime("%Y-%m-%d %H:%M:%S") if quote_time else "",
        }
    return quotes


def fetch_distribution_events(code):
    """解析东方财富分红送配详情页，返回现金分红事件列表。

    页面为服务端渲染，表格结构形如：
      <tr><td>2026年</td><td>2026-01-20</td><td>2026-01-21</td>
          <td>每10份派现金1.4300元</td><td>2026-01-26</td></tr>
    部分债券/货币基金可能使用“每份派现金”口径，两种格式均支持。
    返回 (events, fetch_error)：
      events      按 ex_date 升序的现金分红事件
      fetch_error 页面抓取失败时为对应异常消息，否则为 None
    """
    try:
        html = fetch_text(DIVIDEND_URL.format(code))
    except Exception as error:
        return [], str(error)

    events = []
    for pattern, unit_scale in _DIVIDEND_PATTERNS:
        for registration_date, ex_date, amount in pattern.findall(html):
            try:
                cash_per_unit = float(amount) / unit_scale
            except (TypeError, ValueError):
                continue
            events.append(
                {
                    "registration_date": registration_date,
                    "ex_date": ex_date,
                    "cash_per_unit": cash_per_unit,
                }
            )
    events.sort(key=lambda item: item["ex_date"])
    return events, None


def trailing_distribution_summary(events, price, as_of):
    start_date = as_of.date() - timedelta(days=365)
    trailing = []
    for event in events:
        try:
            ex_date = datetime.strptime(event["ex_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if start_date < ex_date <= as_of.date():
            trailing.append(event)

    cash_per_unit = round(sum(item["cash_per_unit"] for item in trailing), 6)
    distribution_yield = round(cash_per_unit / price * 100, 4) if trailing and price > 0 else None
    month_amounts = {}
    for event in trailing:
        month = str(int(event["ex_date"][5:7]))
        month_amounts[month] = month_amounts.get(month, 0.0) + event["cash_per_unit"]
    distribution_months = {
        month: round(amount / cash_per_unit, 6)
        for month, amount in sorted(month_amounts.items(), key=lambda pair: int(pair[0]))
    } if cash_per_unit > 0 else {}

    return {
        "yield": distribution_yield,
        "impliedYield": distribution_yield,
        "yield_method": "trailing_12m_cash_distributions" if trailing else "no_cash_distribution_in_trailing_12m",
        "trailing_12m_cash_per_unit": cash_per_unit,
        "distribution_count": len(trailing),
        "distribution_as_of": max((item["ex_date"] for item in trailing), default=""),
        "distribution_months": distribution_months,
    }


def build_data_quality_report(assets, records, fetch_errors):
    """生成数据质量报告，突出“声明为稳定现金流但近12个月无真实分红”的资产。

    这类资产在界面上会静默回退到 estimated_yield 规划假设；为了不让用户误以为
    现金流来自真实分红，必须显式告警。
    """
    alerts = []
    for asset in assets:
        code = str(asset["code"])
        income_type = asset.get("income_type")
        if income_type not in ("dividend", "cash_interest"):
            continue
        record = records.get(code) or {}
        if fetch_errors.get(code):
            alerts.append(
                {
                    "code": code,
                    "name": asset.get("name", ""),
                    "income_type": income_type,
                    "declared_yield": asset.get("estimated_yield"),
                    "severity": "error",
                    "reason": "dividend_source_fetch_failed",
                    "detail": fetch_errors[code],
                }
            )
        elif record.get("yield_method") == "no_cash_distribution_in_trailing_12m":
            alerts.append(
                {
                    "code": code,
                    "name": asset.get("name", ""),
                    "income_type": income_type,
                    "declared_yield": asset.get("estimated_yield"),
                    "severity": "warning",
                    "reason": "no_verified_cash_distribution_in_trailing_12m",
                    "detail": "该资产近12个月在分红数据源中无真实现金分配记录，界面使用的收益率是规划假设，不是可核验的实际分红。",
                }
            )
    return alerts


def valuation_freshness_report():
    """检查 valuation_history.json 的估值数据新鲜度，返回结构化报告。

    估值历史当前为半手动维护（无自动化抓取源），因此至少要让管线显式报告滞后，
    避免用户在不知情的情况下基于过期的百分位做判断。
    """
    valuation_path = os.path.join(SCRIPT_DIR, "valuation_history.json")
    if not os.path.exists(valuation_path):
        return {
            "status": "missing",
            "detail": "valuation_history.json 不存在，估值温度计将保持 1.0x 基础计划。",
        }
    try:
        with open(valuation_path, "r", encoding="utf-8") as file:
            records = json.load(file)
    except (OSError, ValueError) as error:
        return {"status": "error", "detail": f"valuation_history.json 解析失败：{error}"}

    if not records:
        return {"status": "missing", "detail": "valuation_history.json 为空。"}

    max_by_index = {}
    latest_overall = None
    for record in records:
        index_code = record.get("index_code")
        date = record.get("date")
        if not index_code or not date:
            continue
        try:
            parsed = datetime.strptime(date, "%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        if max_by_index.get(index_code) is None or parsed > max_by_index[index_code]:
            max_by_index[index_code] = parsed
        if latest_overall is None or parsed > latest_overall:
            latest_overall = parsed

    if latest_overall is None:
        return {"status": "missing", "detail": "valuation_history.json 缺少可用日期字段。"}

    today = datetime.now()
    stale_days = (today - latest_overall).days
    status = "stale" if stale_days > 21 else ("aging" if stale_days > 7 else "fresh")
    return {
        "status": status,
        "latest_date": latest_overall.strftime("%Y-%m-%d"),
        "stale_days": stale_days,
        "indices": sorted(max_by_index.keys()),
        "detail": (
            f"估值历史最新日期 {latest_overall.strftime('%Y-%m-%d')}，距今 {stale_days} 天。"
            "超过 7 天建议人工核对，超过 21 天百分位判断可能失真。"
            if status != "fresh"
            else f"估值历史最新日期 {latest_overall.strftime('%Y-%m-%d')}，数据较新。"
        ),
    }


def fetch_live_data():
    try:
        assets = load_assets()
        quotes = fetch_quotes(assets)
        if not quotes:
            raise RuntimeError("quote source returned no usable records")

        result = {}
        quote_times = []
        fetch_errors = {}
        for asset in assets:
            code = str(asset["code"])
            quote = quotes.get(code)
            if not quote:
                raise RuntimeError(f"quote source returned no usable record for {code}")
            as_of = parse_quote_time(quote["price_as_of"].replace("-", "").replace(":", "").replace(" ", ""))
            as_of = as_of or datetime.now()
            if quote["price_as_of"]:
                quote_times.append(quote["price_as_of"])
            events, fetch_error = fetch_distribution_events(code)
            if fetch_error:
                fetch_errors[code] = fetch_error
            distributions = trailing_distribution_summary(
                events, quote["price"], as_of
            )
            result[code] = {**quote, **distributions}

        data_quality = build_data_quality_report(assets, result, fetch_errors)
        valuation_freshness = valuation_freshness_report()
        output = {
            "status": "success",
            "timestamp": max(quote_times) if quote_times else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": result,
            "methodology": {
                "price": "exchange quote snapshot",
                "yield": "cash distributions with ex-dates in the trailing 365 days divided by latest price",
                "fallback": "null yield means no verified trailing cash distribution; the UI may show a clearly labelled planning assumption",
            },
            "data_quality": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "assets_checked": len(assets),
                "unverified_stable_cashflow_count": sum(
                    1 for alert in data_quality if alert["severity"] == "warning"
                ),
                "fetch_error_count": sum(1 for alert in data_quality if alert["severity"] == "error"),
                "alerts": data_quality,
            },
            "valuation_freshness": valuation_freshness,
        }

        with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=4)

        print("Live data updated successfully at:", output["timestamp"])
        print(f"Updated {len(result)} verified quote records.")
        warnings = output["data_quality"]["alerts"]
        if warnings:
            print(f"⚠️ 数据质量告警 {len(warnings)} 条：")
            for alert in warnings:
                print(
                    f"  [{alert['severity']}] {alert['code']} {alert['name']} "
                    f"({alert['income_type']}): {alert['reason']}"
                )
        if valuation_freshness.get("status") in ("stale", "aging", "missing", "error"):
            print(f"⚠️ 估值数据新鲜度：{valuation_freshness.get('detail', valuation_freshness.get('status'))}")
        return True
    except Exception as error:
        print("Error fetching live data:", error)
        return False


if __name__ == "__main__":
    raise SystemExit(0 if fetch_live_data() else 1)

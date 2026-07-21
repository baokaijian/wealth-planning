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
    try:
        html = fetch_text(DIVIDEND_URL.format(code))
    except Exception:
        return []

    pattern = re.compile(
        r"<tr><td>\d{4}年</td><td>(\d{4}-\d{2}-\d{2})</td>"
        r"<td>(\d{4}-\d{2}-\d{2})</td><td>每份派现金([0-9.]+)元</td>"
    )
    events = []
    for registration_date, ex_date, amount in pattern.findall(html):
        events.append(
            {
                "registration_date": registration_date,
                "ex_date": ex_date,
                "cash_per_unit": float(amount),
            }
        )
    return events


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


def fetch_live_data():
    try:
        assets = load_assets()
        quotes = fetch_quotes(assets)
        if not quotes:
            raise RuntimeError("quote source returned no usable records")

        result = {}
        quote_times = []
        for asset in assets:
            code = str(asset["code"])
            quote = quotes.get(code)
            if not quote:
                raise RuntimeError(f"quote source returned no usable record for {code}")
            as_of = parse_quote_time(quote["price_as_of"].replace("-", "").replace(":", "").replace(" ", ""))
            as_of = as_of or datetime.now()
            if quote["price_as_of"]:
                quote_times.append(quote["price_as_of"])
            distributions = trailing_distribution_summary(
                fetch_distribution_events(code), quote["price"], as_of
            )
            result[code] = {**quote, **distributions}

        output = {
            "status": "success",
            "timestamp": max(quote_times) if quote_times else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": result,
            "methodology": {
                "price": "exchange quote snapshot",
                "yield": "cash distributions with ex-dates in the trailing 365 days divided by latest price",
                "fallback": "null yield means no verified trailing cash distribution; the UI may show a clearly labelled planning assumption",
            },
        }

        with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=4)

        print("Live data updated successfully at:", output["timestamp"])
        print(f"Updated {len(result)} verified quote records.")
        return True
    except Exception as error:
        print("Error fetching live data:", error)
        return False


if __name__ == "__main__":
    raise SystemExit(0 if fetch_live_data() else 1)

"""Indian equity fundamental snapshots. Pure normalization and KPI math.

Provenance: NSE for security/index membership only; Yahoo Finance via yfinance
for statements and market quotes; Screener.in is linked as an independent
consolidated-report reference, never scraped or silently merged.

No index-weight estimation, leadership rankings or investment recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "india_financials"
MONEY_METRICS = {
    "revenue", "gross_profit", "operating_income", "ebitda", "net_income",
    "total_assets", "total_liabilities", "equity", "current_assets", "current_liabilities",
    "cash", "total_debt", "long_term_debt", "current_debt", "goodwill", "other_intangibles",
    "operating_cash_flow", "capital_expenditure", "free_cash_flow", "dividends_paid",
    "repurchases", "interest_expense", "preferred_equity", "inventory", "income_tax_expense",
}
ALIAS = {
    "revenue": ("Total Revenue", "Operating Revenue"),
    "gross_profit": ("Gross Profit",),
    "operating_income": ("Operating Income",),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "net_income": ("Net Income Common Stockholders", "Net Income", "Net Income Continuous Operations"),
    "diluted_eps": ("Diluted EPS", "Basic EPS"),
    "interest_expense": ("Interest Expense", "Interest Expense Non Operating"),
    "income_tax_expense": ("Tax Provision",),
    "total_assets": ("Total Assets",),
    "total_liabilities": ("Total Liabilities Net Minority Interest", "Total Liabilities"),
    "equity": ("Stockholders Equity", "Common Stock Equity"),
    "current_assets": ("Current Assets",),
    "current_liabilities": ("Current Liabilities",),
    "cash": ("Cash And Cash Equivalents", "Cash And Cash Equivalents And Short Term Investments"),
    "total_debt": ("Total Debt",),
    "long_term_debt": ("Long Term Debt", "Long Term Debt And Capital Lease Obligation"),
    "current_debt": ("Current Debt", "Current Debt And Capital Lease Obligation"),
    "goodwill": ("Goodwill",),
    "other_intangibles": ("Other Intangible Assets",),
    "preferred_equity": ("Preferred Stock Equity",),
    "inventory": ("Inventory",),
    "shares_statement": ("Ordinary Shares Number",),
    "operating_cash_flow": ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities"),
    "capital_expenditure": ("Capital Expenditure", "Capital Expenditures"),
    "free_cash_flow": ("Free Cash Flow",),
    "dividends_paid": ("Cash Dividends Paid", "Common Stock Dividend Paid"),
    "repurchases": ("Repurchase Of Capital Stock", "Common Stock Payments"),
}
INCOME = {"revenue", "gross_profit", "operating_income", "ebitda", "net_income", "diluted_eps", "interest_expense", "income_tax_expense"}
BALANCE = {"total_assets", "total_liabilities", "equity", "current_assets", "current_liabilities", "cash", "total_debt", "long_term_debt", "current_debt", "goodwill", "other_intangibles", "preferred_equity", "inventory", "shares_statement"}
CASHFLOW = {"operating_cash_flow", "capital_expenditure", "free_cash_flow", "dividends_paid", "repurchases"}
PERCENT_KPIS = {"gross_margin", "operating_margin", "net_margin", "fcf_margin", "roe", "roa", "revenue_yoy", "earnings_yoy", "eps_yoy", "revenue_3y_cagr", "revenue_5y_cagr", "fcf_yoy", "fcf_yield", "earnings_yield"}
RATIO_KPIS = {"current_ratio", "debt_to_equity", "net_debt_to_ebitda", "interest_coverage", "cash_conversion", "pe", "pb", "price_to_sales", "ev_to_ebitda"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_symbol(symbol: str) -> str:
    """Do not allow arbitrary URL/path input or Yahoo exchange confusion."""
    symbol = str(symbol or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.&-]{0,29}", symbol):
        raise ValueError(f"Invalid NSE symbol: {symbol!r}")
    return symbol


def yahoo_symbol(symbol: str) -> str:
    return safe_symbol(symbol) + ".NS"


def screener_url(symbol: str) -> str:
    from urllib.parse import quote
    return "https://www.screener.in/company/" + quote(safe_symbol(symbol), safe="") + "/consolidated/"


def company_file(company_key: str, root: Path = DATA) -> Path:
    if not company_key:
        raise ValueError("Company identity is required")
    return Path(root) / "companies" / (sha256(company_key.encode("utf-8")).hexdigest()[:20] + ".json")


def _number(value):
    if value is None:
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def _datestr(value) -> str:
    try:
        dt = pd.Timestamp(value)
        return dt.date().isoformat() if not pd.isna(dt) else ""
    except (TypeError, ValueError, OverflowError):
        return ""


def normalize_sheet(sheet, metric_keys: set[str]) -> dict:
    """Normalize a Yahoo sheet into period -> metric -> numeric (raw INR) values.

    Do not treat missing rows as zero. Invalid dates and nonnumerics are skipped.
    """
    if sheet is None or not isinstance(sheet, pd.DataFrame) or sheet.empty:
        return {}
    frame = sheet.copy()
    frame.index = [str(label).strip() for label in frame.index]
    out: dict[str, dict] = {}
    for col in frame.columns:
        period = _datestr(col)
        if not period:
            continue
        row = {}
        for name in metric_keys:
            for alias in ALIAS[name]:
                if alias in frame.index:
                    value = frame.loc[alias, col]
                    if isinstance(value, pd.Series):
                        value = value.iloc[0] if len(value) else None
                    result = _number(value)
                    if result is not None:
                        row[name] = result
                        break
        if row:
            out[period] = row
    return dict(sorted(out.items(), reverse=True))


def normalize_yahoo_statements(annual_income, annual_balance, annual_cashflow,
                               quarterly_income, quarterly_balance, quarterly_cashflow) -> dict:
    return {
        "annual": {
            "income": normalize_sheet(annual_income, INCOME),
            "balance": normalize_sheet(annual_balance, BALANCE),
            "cashflow": normalize_sheet(annual_cashflow, CASHFLOW),
        },
        "quarterly": {
            "income": normalize_sheet(quarterly_income, INCOME),
            "balance": normalize_sheet(quarterly_balance, BALANCE),
            "cashflow": normalize_sheet(quarterly_cashflow, CASHFLOW),
        },
    }


def statement_coverage(payload: dict, frequency: str = "annual") -> dict:
    """Expose what Yahoo actually returned; retrieval alone is not coverage.

    Counts refer to periods containing one or more mapped statement rows.
    No missing values are converted to zeros.
    """
    group = ((payload.get("statements") or {}).get(frequency) or {})
    core = {
        "income": ("revenue", "net_income", "operating_income"),
        "balance": ("total_assets", "equity", "total_liabilities"),
        "cashflow": ("operating_cash_flow", "free_cash_flow"),
    }
    sections = {name: (group.get(name) or {}) for name in core}
    key_periods = {
        name: sorted([date for date, values in sections[name].items()
                      if any(values.get(k) is not None for k in keys)], reverse=True)
        for name, keys in core.items()
    }
    return {
        "core_periods": key_periods,
        "income_periods": len(key_periods["income"]),
        "balance_periods": len(key_periods["balance"]),
        "cashflow_periods": len(key_periods["cashflow"]),
        "income_metric_rows": sum(len(x) for x in sections["income"].values()),
        "balance_metric_rows": sum(len(x) for x in sections["balance"].values()),
        "cashflow_metric_rows": sum(len(x) for x in sections["cashflow"].values()),
        "best_periods": sorted(set().union(*key_periods.values()), reverse=True),
    }


def asof_row(section: dict, date: str, *, tolerance_days: int = 65) -> tuple[dict, str]:
    """Avoid combining data from unrelated fiscal periods."""
    if date in section:
        return section[date], date
    try:
        anchor = pd.Timestamp(date)
        candidates = [(abs((pd.Timestamp(k) - anchor).days), k) for k in section]
    except (ValueError, TypeError):
        return {}, ""
    if not candidates:
        return {}, ""
    days, key = min(candidates)
    return (section[key], key) if days <= tolerance_days else ({}, "")


def safe_ratio(a, b):
    a, b = _number(a), _number(b)
    return a / b if a is not None and b is not None and b != 0 else None


def growth(new, old):
    a, b = _number(new), _number(old)
    # Negative or zero base makes standard YoY% ambiguous; do not mislead.
    return (a / b) - 1 if a is not None and b is not None and b > 0 else None


def _previous_period(rows: dict, current: str, years: int) -> dict:
    try:
        current_ts = pd.Timestamp(current)
        target = current_ts - pd.DateOffset(years=years)
        candidates = [(abs((pd.Timestamp(k) - target).days), k) for k in rows if k != current]
        if candidates:
            days, key = min(candidates)
            if days <= 65:
                return rows[key]
    except (ValueError, TypeError):
        pass
    return {}


def _cagr(new, old, years):
    a, b = _number(new), _number(old)
    return (a / b) ** (1.0 / years) - 1 if a is not None and b is not None and a > 0 and b > 0 else None


def build_kpis(payload: dict, frequency: str = "annual", period: str | None = None) -> dict:
    """All values are nullable. Percent metrics are decimal fractions, not 0..100."""
    statements = payload.get("statements") or {}
    group = statements.get(frequency) or {}
    income, balance, cashflow = (group.get(section) or {} for section in ("income", "balance", "cashflow"))
    dates = sorted(set(income) | set(balance) | set(cashflow), reverse=True)
    if not dates:
        return {"period": "", "frequency": frequency, "metrics": {}, "source_periods": {}}
    anchor = period or (sorted(income, reverse=True)[0] if income else dates[0])
    if anchor not in dates:
        raise ValueError(f"Period {anchor} not found")
    tolerance = 18 if frequency == 'quarterly' else 45
    inc, inc_date = asof_row(income, anchor, tolerance_days=tolerance)
    bal, bal_date = asof_row(balance, anchor, tolerance_days=tolerance)
    cf, cf_date = asof_row(cashflow, anchor, tolerance_days=tolerance)
    result = {**inc, **bal, **cf}
    if "capital_expenditure" in result:
        result["capital_expenditure"] = abs(result["capital_expenditure"])
    if "dividends_paid" in result:
        result["dividends_paid"] = abs(result["dividends_paid"])
    if "repurchases" in result:
        result["repurchases"] = abs(result["repurchases"])
    if result.get("free_cash_flow") is None and result.get("operating_cash_flow") is not None and result.get("capital_expenditure") is not None:
        result["free_cash_flow"] = result["operating_cash_flow"] - result["capital_expenditure"]
    if result.get("total_debt") is not None and result.get("cash") is not None:
        result["net_debt"] = result["total_debt"] - result["cash"]
    if result.get("equity") is None and result.get("total_assets") is not None and result.get("total_liabilities") is not None:
        result["book_equity_all_classes"] = result["total_assets"] - result["total_liabilities"]
    # Shares are from statement period when available; current quote shares are
    # a deliberately disclosed fallback with a different reporting date.
    quote = payload.get("quote") or {}
    shares = result.get("shares_statement")
    result["share_basis"] = "reporting_period" if shares and shares > 0 else "current_quote"
    if not shares or shares <= 0:
        shares = _number(quote.get("shares_outstanding"))
    result["shares_outstanding"] = shares if shares and shares > 0 else None
    if shares and shares > 0:
        if result.get("equity") is not None:
            result["book_value_per_share"] = result["equity"] / shares
            if result.get("goodwill") is not None and result.get("other_intangibles") is not None:
                result["tangible_book_per_share"] = (result["equity"] - result["goodwill"] - result["other_intangibles"]) / shares
        if result.get("current_assets") is not None and result.get("total_liabilities") is not None and result.get("preferred_equity") is not None:
            result["ncav_per_share"] = (result["current_assets"] - result["total_liabilities"] - result["preferred_equity"]) / shares
        if result.get("free_cash_flow") is not None:
            result["fcf_per_share"] = result["free_cash_flow"] / shares
    for key, top, bottom in (
        ("gross_margin", "gross_profit", "revenue"),
        ("operating_margin", "operating_income", "revenue"),
        ("net_margin", "net_income", "revenue"),
        ("fcf_margin", "free_cash_flow", "revenue"),
        ("roe", "net_income", "equity"),
        ("roa", "net_income", "total_assets"),
        ("current_ratio", "current_assets", "current_liabilities"),
        ("debt_to_equity", "total_debt", "equity"),
        ("net_debt_to_ebitda", "net_debt", "ebitda"),
        ("interest_coverage", "operating_income", "interest_expense"),
        ("cash_conversion", "operating_cash_flow", "net_income"),
    ):
        den = result.get(bottom)
        if key == 'interest_coverage' and den is not None:
            den = abs(den)
        result[key] = safe_ratio(result.get(top), den) if den is not None and den > 0 else None
    if frequency == "annual" and result.get("diluted_eps") is not None and result.get("diluted_eps") > 0 and result.get("book_value_per_share") is not None and result["book_value_per_share"] > 0:
        result["graham_number"] = math.sqrt(22.5 * result["diluted_eps"] * result["book_value_per_share"])
    if frequency == "annual" and inc_date:
        last_year = _previous_period(income, inc_date, 1)
        old3 = _previous_period(income, inc_date, 3)
        old5 = _previous_period(income, inc_date, 5)
        result["revenue_yoy"] = growth(inc.get("revenue"), last_year.get("revenue"))
        result["earnings_yoy"] = growth(inc.get("net_income"), last_year.get("net_income"))
        result["eps_yoy"] = growth(inc.get("diluted_eps"), last_year.get("diluted_eps"))
        result["revenue_3y_cagr"] = _cagr(inc.get("revenue"), old3.get("revenue"), 3)
        result["revenue_5y_cagr"] = _cagr(inc.get("revenue"), old5.get("revenue"), 5)
        last_cf = _previous_period(cashflow, cf_date, 1) if cf_date else {}
        old_fcf = last_cf.get("free_cash_flow")
        if old_fcf is None and last_cf.get("operating_cash_flow") is not None and last_cf.get("capital_expenditure") is not None:
            old_fcf = last_cf["operating_cash_flow"] - abs(last_cf["capital_expenditure"])
        result["fcf_yoy"] = growth(result.get("free_cash_flow"), old_fcf)
    price = _number(quote.get("price"))
    mcap = _number(quote.get("market_cap"))
    result["price"] = price
    result["market_cap"] = mcap
    # Financial currency must match quote currency, no implicit FX conversion.
    currency = (payload.get("currency") or "").upper()
    quote_currency = (quote.get("currency") or "").upper()
    comparable = bool(currency and quote_currency and currency == quote_currency)
    result["quote_currency_comparable"] = comparable
    if comparable and frequency == "annual":
        result["pe"] = safe_ratio(price, result.get("diluted_eps")) if result.get("diluted_eps", 0) and result["diluted_eps"] > 0 else None
        result["pb"] = safe_ratio(price, result.get("book_value_per_share")) if result.get("book_value_per_share", 0) and result["book_value_per_share"] > 0 else None
        result["price_to_sales"] = safe_ratio(mcap, result.get("revenue")) if result.get("revenue", 0) and result["revenue"] > 0 else None
        result["earnings_yield"] = safe_ratio(result.get("net_income"), mcap) if mcap and mcap > 0 else None
        result["fcf_yield"] = safe_ratio(result.get("free_cash_flow"), mcap) if mcap and mcap > 0 else None
        if mcap is not None and result.get("total_debt") is not None and result.get("cash") is not None:
            result["enterprise_value"] = mcap + result["total_debt"] - result["cash"]
            result["ev_to_ebitda"] = safe_ratio(result["enterprise_value"], result.get("ebitda")) if result.get("ebitda", 0) and result["ebitda"] > 0 else None
    return {"period": anchor, "frequency": frequency, "metrics": result,
            "source_periods": {"income": inc_date, "balance": bal_date, "cashflow": cf_date}}


def equity_dcf_proxy(fcf, shares, growth_pct=7.0, discount_pct=13.0, terminal_pct=4.0, years=5):
    """Illustrative equity-FCF proxy; not certified FCFE or an enterprise DCF."""
    cash, shares = _number(fcf), _number(shares)
    growth, discount, terminal = growth_pct / 100, discount_pct / 100, terminal_pct / 100
    if cash is None or shares is None or cash <= 0 or shares <= 0 or discount <= terminal or discount <= 0 or years < 1:
        return None
    pv = sum(cash * (1 + growth) ** n / (1 + discount) ** n for n in range(1, years + 1))
    terminal_cash = cash * (1 + growth) ** years * (1 + terminal)
    pv += (terminal_cash / (discount - terminal)) / (1 + discount) ** years
    return pv / shares


def liquidation_proxy(assets, cash, liabilities, shares, recovery_pct=55.0, costs_pct=5.0, preferred_claim=None):
    """Simplified hypothetical, not an appraised liquidation value."""
    a, c, l, s = map(_number, (assets, cash, liabilities, shares))
    if any(x is None for x in (a, c, l, s)) or s <= 0 or a < c or c < 0:
        return None
    pref = _number(preferred_claim)
    # Unknown preferred claim -> cannot assert exact common equity recovery.
    if pref is None:
        return None
    proceeds = c + (a - c) * (recovery_pct / 100)
    net = proceeds - l - pref - proceeds * (costs_pct / 100)
    return net / s


def summary_row(payload: dict) -> dict:
    kpi = build_kpis(payload)
    m = kpi["metrics"]
    keys = ["revenue", "net_income", "diluted_eps", "gross_margin", "operating_margin",
            "net_margin", "roe", "roa", "revenue_yoy", "earnings_yoy", "revenue_3y_cagr",
            "revenue_5y_cagr", "operating_cash_flow", "free_cash_flow", "fcf_margin",
            "total_assets", "total_liabilities", "equity", "cash", "total_debt", "net_debt",
            "current_ratio", "debt_to_equity", "cash_conversion", "book_value_per_share",
            "tangible_book_per_share", "graham_number", "market_cap", "price", "pe", "pb",
            "fcf_yield", "enterprise_value", "ev_to_ebitda"]
    return {"company_key": payload.get("company_key", ""), "symbol": payload.get("symbol", ""),
            "company_name": payload.get("company_name", ""), "isin": payload.get("isin", ""),
            "industry": payload.get("industry", ""), "sector": payload.get("sector", ""),
            "yahoo_ticker": payload.get("yahoo_ticker", ""), "financial_currency": payload.get("currency", ""),
            "quote_currency": (payload.get("quote") or {}).get("currency", ""),
            "financial_period": kpi["period"], "income_period": kpi["source_periods"].get("income", ""),
            "balance_period": kpi["source_periods"].get("balance", ""),
            "cashflow_period": kpi["source_periods"].get("cashflow", ""),
            "quote_asof": (payload.get("quote") or {}).get("asof_utc", ""),
            "retrieved_utc": payload.get("retrieved_utc", ""),
            "available_key_metrics": sum(m.get(key) is not None for key in ("revenue", "net_income", "total_assets", "operating_cash_flow", "price")),
            **{key: m.get(key) for key in keys}}


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_company(company_key: str, root: Path = DATA) -> dict | None:
    path = company_file(company_key, root)
    if not path.is_file():
        return None
    try:
        data = load_json(path)
    except (OSError, ValueError):
        return None
    if data.get("company_key") != company_key:
        return None
    return data

AGGREGATE_FIELDS = [
    'group_type', 'group_name', 'index_slug', 'parent_universe', 'constituents',
    'companies_with_snapshots', 'annual_income_coverage', 'annual_balance_coverage',
    'annual_cashflow_coverage', 'price_coverage', 'pct_with_income',
    'median_revenue_yoy', 'n_revenue_yoy', 'median_operating_margin', 'n_operating_margin',
    'median_net_margin', 'n_net_margin', 'median_roe', 'n_roe',
    'median_fcf_margin', 'n_fcf_margin', 'median_debt_to_equity', 'n_debt_to_equity',
    'median_pe', 'n_pe', 'median_fcf_yield', 'n_fcf_yield',
]


def aggregate_member_financials(member_rows: list[dict], financials_by_key: dict[str, dict],
                                group_type: str, group_name: str, index_slug: str = '',
                                parent_universe: str = '') -> dict:
    """Descriptive unweighted medians on unique company identifiers only.

    A company appearing in multiple overlapping source indices is counted once
    within a factor family, not once per membership. Data coverage denominators
    ALWAYS include all verified NSE constituents in the group.
    """
    keys = {r.get('company_key') for r in member_rows if r.get('company_key')}
    rows = [financials_by_key[key] for key in keys if key in financials_by_key]
    available = lambda key: sum(_number(row.get(key)) is not None for row in rows)
    result = {
        'group_type': group_type, 'group_name': group_name, 'index_slug': index_slug,
        'parent_universe': parent_universe, 'constituents': len(keys),
        'companies_with_snapshots': len(rows),
        'annual_income_coverage': sum(bool(r.get('income_period')) for r in rows),
        'annual_balance_coverage': sum(bool(r.get('balance_period')) for r in rows),
        'annual_cashflow_coverage': sum(bool(r.get('cashflow_period')) for r in rows),
        'price_coverage': available('price'),
        'pct_with_income': 100 * available('revenue') / len(keys) if keys else None,
    }
    for metric in ('revenue_yoy', 'operating_margin', 'net_margin', 'roe', 'fcf_margin',
                   'debt_to_equity', 'pe', 'fcf_yield'):
        values = sorted((_number(row.get(metric)) for row in rows if _number(row.get(metric)) is not None))
        # Median-based only; no pseudo index weights, no aggregate investment return.
        mid = len(values) // 2
        result['median_' + metric] = ((values[mid - 1] + values[mid]) / 2 if len(values) % 2 == 0
                                       else values[mid]) if values else None
        result['n_' + metric] = len(values)
    return result

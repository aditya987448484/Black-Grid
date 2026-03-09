"""Fundamental analysis service — SEC data + yfinance fallback for all tickers."""

from __future__ import annotations

import asyncio
from typing import Optional


async def fetch_fundamentals_yf(ticker: str) -> dict:
    """Fetch real fundamentals via yfinance for any US-listed ticker."""
    try:
        import yfinance as yf

        def _get_info():
            t = yf.Ticker(ticker)
            return t.info

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _get_info)

        if not info or info.get("quoteType") == "NONE":
            return _empty_fundamentals(ticker)

        # yfinance returns margins as fractions (0.25 = 25%), keep as-is for formatting
        result = {
            "revenue": info.get("totalRevenue"),
            "netIncome": info.get("netIncomeToCommon"),
            "eps": info.get("trailingEps"),
            "forwardEps": info.get("forwardEps"),
            "peRatio": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "pbRatio": info.get("priceToBook"),
            "evToEbitda": info.get("enterpriseToEbitda"),
            "operatingCashFlow": info.get("operatingCashflow"),
            "freeCashFlow": info.get("freeCashflow"),
            "totalAssets": info.get("totalAssets"),
            "totalLiabilities": info.get("totalDebt"),
            "totalDebt": info.get("totalDebt"),
            "cashAndEquivalents": info.get("totalCash"),
            "grossMargin": info.get("grossMargins"),       # fraction (0.45 = 45%)
            "operatingMargin": info.get("operatingMargins"),
            "profitMargin": info.get("profitMargins"),
            "revenueGrowth": info.get("revenueGrowth"),     # fraction
            "earningsGrowth": info.get("earningsGrowth"),
            "returnOnEquity": info.get("returnOnEquity"),   # fraction
            "returnOnAssets": info.get("returnOnAssets"),
            "dividendYield": info.get("dividendYield"),     # fraction
            "beta": info.get("beta"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "marketCap": info.get("marketCap"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "fullName": info.get("longName"),
            "description": info.get("longBusinessSummary"),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
            "website": info.get("website"),
        }

        has_data = any(v is not None for k, v in result.items()
                       if k not in ("sector", "industry", "fullName", "description", "country", "website"))
        if has_data:
            rev_str = f"${result['revenue']/1e9:.1f}B" if result.get("revenue") else "N/A"
            print(f"[fundamentals:yf] Got data for {ticker}: revenue={rev_str}, sector={result.get('sector')}")
        return result

    except ImportError:
        print("[fundamentals:yf] yfinance not installed")
        return _empty_fundamentals(ticker)
    except Exception as e:
        print(f"[fundamentals:yf] Error {ticker}: {e}")
        return _empty_fundamentals(ticker)


def build_fundamental_summary(sec_data: Optional[dict], ticker: str) -> dict:
    """Build normalized fundamental summary from SEC data."""
    if not sec_data:
        return _empty_fundamentals(ticker)

    revenue = sec_data.get("revenue")
    net_income = sec_data.get("netIncome")
    eps = sec_data.get("eps")
    ocf = sec_data.get("operatingCashFlow")
    assets = sec_data.get("totalAssets")
    liabilities = sec_data.get("totalLiabilities")
    gross_profit = sec_data.get("grossProfit")
    operating_income = sec_data.get("operatingIncome")
    equity = sec_data.get("totalEquity")
    long_term_debt = sec_data.get("longTermDebt")
    current_assets = sec_data.get("currentAssets")
    current_liabilities = sec_data.get("currentLiabilities")

    # Profitability margins
    net_margin = (net_income / revenue * 100) if revenue and net_income else None
    gross_margin = (gross_profit / revenue * 100) if revenue and gross_profit else None
    operating_margin = (operating_income / revenue * 100) if revenue and operating_income else None

    # Balance sheet ratios
    debt_ratio = (liabilities / assets * 100) if assets and liabilities else None
    current_ratio = (current_assets / current_liabilities) if current_assets and current_liabilities else None
    debt_to_equity = (liabilities / equity) if equity and liabilities else None

    roe = (net_income / equity * 100) if equity and net_income else None

    return {
        "revenue": revenue,
        "netIncome": net_income,
        "eps": eps,
        "operatingCashFlow": ocf,
        "totalAssets": assets,
        "totalLiabilities": liabilities,
        "grossProfit": gross_profit,
        "operatingIncome": operating_income,
        "totalEquity": equity,
        "longTermDebt": long_term_debt,
        "currentAssets": current_assets,
        "currentLiabilities": current_liabilities,
        "profitMargin": round(net_margin, 2) if net_margin else None,
        "grossMargin": round(gross_margin, 2) if gross_margin else None,
        "operatingMargin": round(operating_margin, 2) if operating_margin else None,
        "debtRatio": round(debt_ratio, 2) if debt_ratio else None,
        "currentRatio": round(current_ratio, 2) if current_ratio else None,
        "debtToEquity": round(debt_to_equity, 2) if debt_to_equity else None,
        "returnOnEquity": round(roe, 2) if roe else None,
    }


def _empty_fundamentals(ticker: str) -> dict:
    """Return genuinely empty fundamentals — never fake data."""
    return {
        "revenue": None, "netIncome": None, "eps": None, "forwardEps": None,
        "peRatio": None, "forwardPE": None, "pbRatio": None, "evToEbitda": None,
        "operatingCashFlow": None, "freeCashFlow": None, "totalAssets": None,
        "totalLiabilities": None, "totalDebt": None, "cashAndEquivalents": None,
        "grossMargin": None, "operatingMargin": None, "profitMargin": None,
        "revenueGrowth": None, "earningsGrowth": None,
        "returnOnEquity": None, "returnOnAssets": None,
        "dividendYield": None, "beta": None,
        "fiftyTwoWeekHigh": None, "fiftyTwoWeekLow": None,
        "marketCap": None, "sector": None, "industry": None,
        "fullName": None, "description": None, "employees": None,
        "country": None, "website": None,
    }

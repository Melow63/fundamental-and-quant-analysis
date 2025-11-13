import yfinance as yf
import pandas as pd

# --- Settings ---
TICKER = "NVDA"
pd.options.mode.chained_assignment = None


# --- Helpers ---
def get_growth(financials, metric):
    try:
        if metric not in financials.index:
            return None
        values = financials.loc[metric].dropna()
        if len(values) > 1:
            if values.index[0] == "TTM" and len(values) > 2:
                latest = values.iloc[1]
                previous = values.iloc[2]
            else:
                latest = values.iloc[0]
                previous = values.iloc[1]
            return round(((latest - previous) / previous) * 100, 2)
    except Exception as e:
        print(f"Error in growth calculation ({metric}):", e)
    return None


def get_fundamental_data(ticker):
    stock = yf.Ticker(ticker)
    try:
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
    except Exception as e:
        print("Data retrieval error:", e)
        return {}

    for df in [financials, balance_sheet, cashflow]:
        df.index = df.index.astype(str).str.replace(" ", "").str.strip()

    try:
        current_price = stock.history(period="1d")["Close"].iloc[-1]
    except Exception:
        current_price = None

    equity_columns = ["TotalStockholdersEquity", "StockholdersEquity", "CommonStockEquity", "TotalEquityGrossMinorityInterest"]
    equity_value = next((balance_sheet.loc[col].iloc[0] for col in equity_columns if col in balance_sheet.index), None)
    shares_outstanding = balance_sheet.loc["OrdinarySharesNumber"].iloc[0] if "OrdinarySharesNumber" in balance_sheet.index else None
    pb_ratio = round(current_price / (equity_value / shares_outstanding), 2) if equity_value and shares_outstanding and current_price else None

    revenue_growth = get_growth(financials, "TotalRevenue")
    eps_growth = get_growth(financials, "DilutedEPS")
    fcf_growth = get_growth(cashflow, "FreeCashFlow")

    data = {
        "EPS": round(financials.loc["DilutedEPS"].iloc[0], 2) if "DilutedEPS" in financials.index else None,
        "P/E": round(current_price / financials.loc["DilutedEPS"].iloc[0], 2) if "DilutedEPS" in financials.index and current_price else None,
        "P/B": pb_ratio,
        "ROE": round(financials.loc["NetIncome"].iloc[0] / equity_value, 2) if "NetIncome" in financials.index and equity_value else None,
        "ROA": round(financials.loc["NetIncome"].iloc[0] / balance_sheet.loc["TotalAssets"].iloc[0], 2) if "NetIncome" in financials.index and "TotalAssets" in balance_sheet.index else None,
        "EBITDA (bn)": round(financials.loc["EBITDA"].iloc[0] / 1e9, 2) if "EBITDA" in financials.index else None,
        "Debt/EBITDA": round(balance_sheet.loc["TotalDebt"].iloc[0] / financials.loc["EBITDA"].iloc[0], 2) if "TotalDebt" in balance_sheet.index and "EBITDA" in financials.index else None,
        "Current Ratio": round(balance_sheet.loc["CurrentAssets"].iloc[0] / balance_sheet.loc["CurrentLiabilities"].iloc[0], 2) if "CurrentAssets" in balance_sheet.index and "CurrentLiabilities" in balance_sheet.index else None,
        "Free Cash Flow (bn)": round(cashflow.loc["FreeCashFlow"].iloc[0] / 1e9, 2) if "FreeCashFlow" in cashflow.index else None,
        "EPS Growth (%)": eps_growth,
        "Revenue Growth (%)": revenue_growth,
        "FCF Growth (%)": fcf_growth,
    }
    return data


def interpret_data(data):
    return {
        "EPS": "Consistent earnings" if data.get("EPS") else "Data unavailable",
        "P/E": "Reasonable valuation (<20)" if data.get("P/E") and data["P/E"] < 20 else "Potentially overvalued",
        "P/B": "Undervalued (<5)" if data.get("P/B") and data["P/B"] < 5 else "Overvalued",
        "ROE": "Strong profitability (>15%)" if data.get("ROE") and data["ROE"] > 0.15 else "Weak profitability",
        "ROA": "Efficient use of assets (>5%)" if data.get("ROA") and data["ROA"] > 0.05 else "Low efficiency",
        "EBITDA (bn)": "Healthy operating margin" if data.get("EBITDA (bn)") else "Data unavailable",
        "Debt/EBITDA": "Controlled leverage (<3)" if data.get("Debt/EBITDA") and data["Debt/EBITDA"] < 3 else "High leverage",
        "Current Ratio": "Safe liquidity (>1.5)" if data.get("Current Ratio") and data["Current Ratio"] > 1.5 else "Fragile liquidity",
        "Free Cash Flow (bn)": "Positive FCF" if data.get("Free Cash Flow (bn)") else "Data unavailable",
        "EPS Growth (%)": "Healthy earnings growth (>5%)" if data.get("EPS Growth (%)") and data["EPS Growth (%)"] > 5 else "Low EPS growth",
        "Revenue Growth (%)": "Strong revenue momentum (>10%)" if data.get("Revenue Growth (%)") and data["Revenue Growth (%)"] > 10 else "Low revenue growth",
        "FCF Growth (%)": "Strong FCF expansion (>10%)" if data.get("FCF Growth (%)") and data["FCF Growth (%)"] > 10 else "Weak FCF growth",
    }


def investment_score(data):
    score = 0

    if data.get("P/E") is not None:
        score += 1.5 if data["P/E"] < 20 else -1 if data["P/E"] > 30 else 0
    if data.get("P/B") is not None:
        score += 1.5 if data["P/B"] < 5 else -1 if data["P/B"] > 10 else 0

    score += 2.5 if data.get("ROE") and data["ROE"] > 0.15 else 0
    score += 1.5 if data.get("ROA") and data["ROA"] > 0.05 else 0

    if data.get("Debt/EBITDA") is not None:
        if data["Debt/EBITDA"] < 1:
            score += 1
        elif data["Debt/EBITDA"] < 3:
            score += 2
        elif data["Debt/EBITDA"] > 5:
            score -= 2

    score += 1 if data.get("Current Ratio") and data["Current Ratio"] > 1.5 else 0
    score += 2 if data.get("Free Cash Flow (bn)") and data["Free Cash Flow (bn)"] > 0 else 0

    score += 3 if data.get("EPS Growth (%)") and data["EPS Growth (%)"] > 5 else 0
    score += 3 if data.get("Revenue Growth (%)") and data["Revenue Growth (%)"] > 10 else 0
    score += 2 if data.get("FCF Growth (%)") and data["FCF Growth (%)"] > 15 else 0

    if data.get("EPS") and data["EPS"] < 0:
        score -= 2

    # Growth synergy bonus
    growth_flags = sum([
        data.get("EPS Growth (%)") and data["EPS Growth (%)"] > 20,
        data.get("Revenue Growth (%)") and data["Revenue Growth (%)"] > 20,
        data.get("FCF Growth (%)") and data["FCF Growth (%)"] > 20,
    ])
    score += 1 if growth_flags >= 2 else 0

    # Simultaneous revenue and FCF decline penalty
    if (data.get("Revenue Growth (%)") and data["Revenue Growth (%)"] < 0) and \
       (data.get("FCF Growth (%)") and data["FCF Growth (%)"] < 0):
        score -= 2

    return min(max(score, 0), 20)


def investment_recommendation(score):
    if score >= 16:
        return " High-quality stock with strong profitability and growth."
    elif score >= 12:
        return " Solid fundamentals, but monitor valuation or debt."
    elif score >= 8:
        return " Average performance with potential red flags."
    else:
        return " Risky profile: weak fundamentals or poor growth."


def analyze_stock(ticker):
    print(f"\n Fundamental Analysis — {ticker.upper()}\n")
    data = get_fundamental_data(ticker)
    if not data:
        print(" Unable to retrieve financial data.")
        return None

    interpretation = interpret_data(data)
    score = investment_score(data)
    recommendation = investment_recommendation(score)

    data["Investment Score"] = score
    interpretation["Investment Score"] = f"{score}/20"
    interpretation["Recommendation"] = recommendation

    df = pd.DataFrame({
        "Indicator": list(data.keys()),
        "Value": [round(v, 2) if isinstance(v, (int, float)) else v for v in data.values()],
        "Interpretation": [interpretation.get(k, "Data unavailable") for k in data.keys()]
    })

    pd.set_option('display.colheader_justify', 'center')
    print(df.to_string(index=False, col_space=[25, 12, 40]))

    print("\n Final Recommendation:")
    print(recommendation)
    return df


df = analyze_stock(TICKER)



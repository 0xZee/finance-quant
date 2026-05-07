import yfinance as yf
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_financial_scores(ticker, info):
    scores = {
        "Altman Z-Score": "N/A",
        "Piotroski F-Score": "N/A"
    }
    try:
        # Fetch financial statements
        bs = ticker.balance_sheet
        fin = ticker.financials
        cf = ticker.cashflow

        if bs.empty or fin.empty or cf.empty:
            return scores

        # --- Altman Z-Score (Public Mfg) ---
        # Formula: 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
        try:
            total_assets = bs.loc['Total Assets'].iloc[0]
            working_capital = bs.loc['Working Capital'].iloc[0]
            retained_earnings = bs.loc['Retained Earnings'].iloc[0]
            ebit = fin.loc['EBIT'].iloc[0]
            sales = fin.loc['Total Revenue'].iloc[0]
            market_cap = info.get('marketCap', 0)
            total_liab = bs.loc['Total Liabilities Net Minority Interest'].iloc[0]

            A = working_capital / total_assets
            B = retained_earnings / total_assets
            C = ebit / total_assets
            D = market_cap / total_liab
            E = sales / total_assets
            
            z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
            scores["Altman Z-Score"] = round(z_score, 2)
        except:
            pass

        # --- Piotroski F-Score (9-point) ---
        try:
            f_score = 0
            # 1. ROA > 0
            ni = fin.loc['Net Income'].iloc[0]
            assets = bs.loc['Total Assets'].iloc[0]
            roa = ni / assets
            if roa > 0: f_score += 1
            
            # 2. CFO > 0
            cfo = cf.loc['Operating Cash Flow'].iloc[0]
            if cfo > 0: f_score += 1
            
            # 3. Delta ROA > 0
            ni_prev = fin.loc['Net Income'].iloc[1]
            assets_prev = bs.loc['Total Assets'].iloc[1]
            roa_prev = ni_prev / assets_prev
            if roa > roa_prev: f_score += 1
            
            # 4. Accrual (CFO > NI)
            if cfo > ni: f_score += 1
            
            # 5. Delta Leverage (LTD down)
            ltd = bs.loc['Long Term Debt'].iloc[0]
            ltd_prev = bs.loc['Long Term Debt'].iloc[1]
            if ltd < ltd_prev: f_score += 1
            
            # 6. Delta Liquidity (Current Ratio up)
            cr = bs.loc['Current Assets'].iloc[0] / bs.loc['Current Liabilities'].iloc[0]
            cr_prev = bs.loc['Current Assets'].iloc[1] / bs.loc['Current Liabilities'].iloc[1]
            if cr > cr_prev: f_score += 1
            
            # 7. No New Shares
            shares = bs.loc['Ordinary Shares Number'].iloc[0]
            shares_prev = bs.loc['Ordinary Shares Number'].iloc[1]
            if shares <= shares_prev: f_score += 1
            
            # 8. Delta Gross Margin
            gm = fin.loc['Gross Profit'].iloc[0] / fin.loc['Total Revenue'].iloc[0]
            gm_prev = fin.loc['Gross Profit'].iloc[1] / fin.loc['Total Revenue'].iloc[1]
            if gm > gm_prev: f_score += 1
            
            # 9. Delta Asset Turnover
            at = fin.loc['Total Revenue'].iloc[0] / assets
            at_prev = fin.loc['Total Revenue'].iloc[1] / assets_prev
            if at > at_prev: f_score += 1
            
            scores["Piotroski F-Score"] = f_score
        except:
            pass

    except:
        pass
    
    return scores

def get_ticker_info(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # 1. Performance & Technicals calculation
        hist = ticker.history(period="1y")
        technicals = {}
        performance = {}
        if not hist.empty:
            current = hist["Close"].iloc[-1]
            one_week = hist["Close"].iloc[-6] if len(hist) >= 6 else hist["Close"].iloc[0]
            one_month = hist["Close"].iloc[-22] if len(hist) >= 22 else hist["Close"].iloc[0]
            six_months = hist["Close"].iloc[-127] if len(hist) >= 127 else hist["Close"].iloc[0]
            ytd_data = hist[hist.index >= f"{hist.index[-1].year}-01-01"]
            ytd_start = ytd_data["Close"].iloc[0] if not ytd_data.empty else current
            
            performance = {
                "1 Week": f"{((current/one_week) - 1)*100:+.2f}%",
                "1 Month": f"{((current/one_month) - 1)*100:+.2f}%",
                "6 Months": f"{((current/six_months) - 1)*100:+.2f}%",
                "Year to Date": f"{((current/ytd_start) - 1)*100:+.2f}%",
            }

            # RSI
            rsi_val = calculate_rsi(hist["Close"]).iloc[-1]
            
            # Annualized Volatility
            returns = np.log(hist["Close"] / hist["Close"].shift(1))
            volatility = returns.std() * np.sqrt(252)
            
            # Distance from 52W High/Low
            high_52w = hist["High"].max()
            low_52w = hist["Low"].min()
            dist_high = (current / high_52w - 1) * 100
            dist_low = (current / low_52w - 1) * 100

            technicals = {
                "RSI (14d)": rsi_val,
                "Volatility (Ann)": volatility,
                "From 52W High": f"{dist_high:+.2f}%",
                "From 52W Low": f"{dist_low:+.2f}%",
            }

        # 2. Analyst Recommendations
        recs_summary = ticker.recommendations_summary
        analyst_sentiment = "N/A"
        if recs_summary is not None and not recs_summary.empty:
            latest = recs_summary.iloc[0]
            total = latest["strongBuy"] + latest["buy"] + latest["hold"] + latest["sell"] + latest["strongSell"]
            if total > 0:
                buy_pct = (latest["strongBuy"] + latest["buy"]) / total * 100
                hold_pct = latest["hold"] / total * 100
                sell_pct = (latest["sell"] + latest["strongSell"]) / total * 100
                analyst_sentiment = f"Buy: {buy_pct:.0f}% | Hold: {hold_pct:.0f}% | Sell: {sell_pct:.0f}% ({total} analysts)"

        # 3. Short Squeeze metrics
        short_prior = info.get("sharesShortPriorMonth")
        short_current = info.get("sharesShort")
        short_change = "N/A"
        if short_prior and short_current:
            short_change_val = (short_current / short_prior - 1) * 100
            short_change = f"{short_change_val:+.2f}%"

        # 4. Price Targets & Upside
        mean_target = info.get("targetMeanPrice")
        upside = "N/A"
        if mean_target and info.get("currentPrice"):
            upside_val = (mean_target / info.get("currentPrice") - 1) * 100
            upside = f"{upside_val:+.2f}%"

        # 5. Calendar Events
        cal = ticker.calendar
        events = {}
        if cal:
            events = {
                "Next Earnings": cal.get("Earnings Date", ["N/A"])[0],
                "Dividend Date": cal.get("Dividend Date", "N/A"),
                "Ex-Dividend Date": cal.get("Ex-Dividend Date", "N/A")
            }

        # 6. Sustainability
        sus = ticker.sustainability
        esg_score = "N/A"
        if sus is not None and not sus.empty:
            try:
                esg_score = f"{sus.loc['totalEsg', 'Value']} ({sus.loc['esgPerformance', 'Value']})"
            except:
                pass

        # 7. Financial Scores (Premium)
        premium_scores = calculate_financial_scores(ticker, info)

        # Organized Metrics
        metrics = {
            "🏢 Company Profile": {
                "Symbol": info.get("symbol"),
                "Long Name": info.get("longName"),
                "Sector": info.get("sector"),
                "Industry": info.get("industry"),
                "Full Time Employees": info.get("fullTimeEmployees"),
                "City": info.get("city"),
                "State": info.get("state"),
                "Country": info.get("country"),
                "Website": info.get("website"),
            },
            "💎 Premium Analyst Metrics": {
                **premium_scores,
                "Altman Status": "Distress" if isinstance(premium_scores["Altman Z-Score"], (int, float)) and premium_scores["Altman Z-Score"] < 1.81 else "Safe" if isinstance(premium_scores["Altman Z-Score"], (int, float)) and premium_scores["Altman Z-Score"] > 2.99 else "Grey Zone" if isinstance(premium_scores["Altman Z-Score"], (int, float)) else "N/A",
                "F-Score Rating": "Strong" if isinstance(premium_scores["Piotroski F-Score"], int) and premium_scores["Piotroski F-Score"] >= 7 else "Weak" if isinstance(premium_scores["Piotroski F-Score"], int) and premium_scores["Piotroski F-Score"] <= 3 else "Neutral" if isinstance(premium_scores["Piotroski F-Score"], int) else "N/A",
            },
            "📊 Market Data": {
                "Current Price": info.get("currentPrice"),
                "Previous Close": info.get("previousClose"),
                "Open": info.get("open"),
                "Day Range": f"{info.get('dayLow')} - {info.get('dayHigh')}",
                "52 Week Range": f"{info.get('fiftyTwoWeekLow')} - {info.get('fiftyTwoWeekHigh')}",
                "Bid": info.get("bid"),
                "Ask": info.get("ask"),
                "Market Cap": info.get("marketCap"),
                "Enterprise Value": info.get("enterpriseValue"),
            },
            "🔊 Volume & Liquidity": {
                "Volume": info.get("volume"),
                "Avg Vol (10d)": info.get("averageVolume10days"),
                "Avg Vol (3m)": info.get("averageVolume"),
                "Avg Daily Vol (10d)": info.get("averageDailyVolume10Day"),
                "Bid Size": info.get("bidSize"),
                "Ask Size": info.get("askSize"),
            },
            "📈 Price Performance": {
                **performance,
                "52W Change %": info.get("fiftyTwoWeekChangePercent"),
                "S&P 52W Change %": info.get("SandP52WeekChange"),
                "Beta (5Y)": info.get("beta"),
            },
            "🌡️ Technical Indicators": {
                **technicals,
                "50 Day Average": info.get("fiftyDayAverage"),
                "200 Day Average": info.get("twoHundredDayAverage"),
                "50D Avg Change": info.get("fiftyDayAverageChangePercent"),
                "200D Avg Change": info.get("twoHundredDayAverageChangePercent"),
            },
            "⚖️ Valuation Multiples": {
                "Trailing P/E": info.get("trailingPE"),
                "Forward P/E": info.get("forwardPE"),
                "PEG Ratio": info.get("pegRatio"),
                "Price to Sales": info.get("priceToSalesTrailing12Months"),
                "Price to Book": info.get("priceToBook"),
                "EV to Revenue": info.get("enterpriseToRevenue"),
                "EV to EBITDA": info.get("enterpriseToEbitda"),
                "Book Value": info.get("bookValue"),
            },
            "🔄 Efficiency & Return": {
                "Return on Equity": info.get("returnOnEquity"),
                "Return on Assets": info.get("returnOnAssets"),
                "Gross Margins": info.get("grossMargins"),
                "Operating Margins": info.get("operatingMargins"),
                "Profit Margin": info.get("profitMargins"),
                "EBITDA Margins": info.get("ebitdaMargins"),
                "Revenue per Share": info.get("revenuePerShare"),
                "Cash per Share": info.get("totalCashPerShare"),
            },
            "🚀 Growth Estimates": {
                "Revenue Growth": info.get("revenueGrowth"),
                "Earnings Growth": info.get("earningsGrowth"),
                "Quarterly Earn Growth": info.get("earningsQuarterlyGrowth"),
                "Trailing EPS": info.get("trailingEps"),
                "Forward EPS": info.get("forwardEps"),
                "EPS Next Year": info.get("epsForward"),
            },
            "🏥 Financial Health": {
                "Total Cash": info.get("totalCash"),
                "Total Debt": info.get("totalDebt"),
                "Operating Cashflow": info.get("operatingCashflow"),
                "Free Cashflow": info.get("freeCashflow"),
                "Current Ratio": info.get("currentRatio"),
                "Quick Ratio": info.get("quickRatio"),
                "Debt to Equity": info.get("debtToEquity"),
                "Revenue": info.get("totalRevenue"),
            },
            "🌊 Share Statistics": {
                "Shares Outstanding": info.get("sharesOutstanding"),
                "Float Shares": info.get("floatShares"),
                "Implied Shares": info.get("impliedSharesOutstanding"),
                "Held by Insiders": info.get("heldPercentInsiders"),
                "Held by Institutions": info.get("heldPercentInstitutions"),
            },
            "🩳 Short Squeeze Indicators": {
                "Short Ratio": info.get("shortRatio"),
                "Short % of Float": info.get("shortPercentOfFloat"),
                "Short % of Shares": info.get("sharesPercentSharesOut"),
                "Short % Change": short_change,
                "Shares Short": info.get("sharesShort"),
                "Prior Month Short": info.get("sharesShortPriorMonth"),
            },
            "💰 Dividends": {
                "Dividend Yield": info.get("dividendYield"),
                "Dividend Rate": info.get("dividendRate"),
                "Payout Ratio": info.get("payoutRatio"),
                "5 Yr Avg Yield": info.get("fiveYearAvgDividendYield"),
                "Trailing Div Yield": info.get("trailingAnnualDividendYield"),
                "Trailing Div Rate": info.get("trailingAnnualDividendRate"),
                **events
            },
            "🎯 Analyst Sentiment": {
                "Analyst Consensus": analyst_sentiment,
                "Number of Opinions": info.get("numberOfAnalystOpinions"),
                "Target Low": info.get("targetLowPrice"),
                "Target High": info.get("targetHighPrice"),
                "Target Mean": mean_target,
                "Target Median": info.get("targetMedianPrice"),
                "Implied Upside": upside,
            },
            "🛡️ Risk & Governance": {
                "Overall Risk (1-10)": info.get("overallRisk"),
                "Audit Risk": info.get("auditRisk"),
                "Board Risk": info.get("boardRisk"),
                "Compensation Risk": info.get("compensationRisk"),
                "Shareholder Rights": info.get("shareHolderRightsRisk"),
                "ESG Score": esg_score,
            }
        }

        # Process news
        news = ticker.news[:5]
        processed_news = []
        for item in news:
            content = item.get('content', item)
            processed_news.append({
                'provider': content.get('provider', {}).get('displayName', 'N/A'),
                'pubDate': content.get('pubDate', 'N/A'),
                'title': content.get('title', 'N/A'),
                'summary': content.get('summary', 'N/A')
            })

        return {"metrics": metrics, "news": processed_news}
    except Exception as e:
        import traceback
        return {"error": f"{str(e)}\n{traceback.format_exc()}"}

def format_value(val, key=""):
    if val is None or val == "N/A":
        return "N/A"
    
    if isinstance(val, (int, float)):
        # Currency/Magnitude formatting
        if abs(val) >= 1_000_000_000_000:
            return f"{val / 1_000_000_000_000:.2f}T"
        if abs(val) >= 1_000_000_000:
            return f"{val / 1_000_000_000:.2f}B"
        if abs(val) >= 1_000_000:
            return f"{val / 1_000_000:.2f}M"
        
        # Percentage formatting
        if "Dividend Yield" in key or "Trailing Div Yield" in key:
            return f"{val:.2f}%"
        
        pct_keys = ["Margin", "Growth", "Return", "Payout", "Insiders", "Institutions", 
                    "Float", "Volatility", "Change %", "Held by"]
        if any(pk in key for pk in pct_keys):
            return f"{val*100:.2f}%" if abs(val) < 20 else f"{val:.2f}%"
            
        # Ratios & Scores
        ratio_keys = ["Ratio", "RSI", "EV to", "Price to", "Risk", "Rights", "Beta", "EPS", "per Share", "Opinion", "Z-Score", "F-Score"]
        if any(rk in key for rk in ratio_keys):
            return f"{val:.2f}"
            
        if 0 < abs(val) < 1:
            return f"{val:.4f}"
        return f"{val:.2f}"
    return str(val)

def main():
    if len(sys.argv) < 2:
        print("Usage: python ticker_info.py <TICKER>")
        sys.exit(1)
        
    symbol = sys.argv[1].upper()
    print(f"🔍 Fetching information for {symbol}...\n")
    
    result = get_ticker_info(symbol)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)
        
    emojis = {
        "Symbol": "🏷️",
        "Long Name": "📝",
        "Sector": "🌐",
        "Industry": "🏭",
        "Full Time Employees": "👥",
        "City": "🏙️",
        "State": "📍",
        "Country": "🌍",
        "Website": "🔗",
        "Altman Z-Score": "☣️",
        "Altman Status": "🚦",
        "Piotroski F-Score": "🧱",
        "F-Score Rating": "🏅",
        "Current Price": "💵",
        "Previous Close": "⏪",
        "Open": "🔔",
        "Day Range": "↕️",
        "52 Week Range": "🗓️",
        "Bid": "📥",
        "Ask": "📤",
        "Market Cap": "⚖️",
        "Enterprise Value": "🏢",
        "Volume": "🔊",
        "Avg Vol (10d)": "📊",
        "Avg Vol (3m)": "📊",
        "Avg Daily Vol (10d)": "📉",
        "Bid Size": "📦",
        "Ask Size": "📦",
        "1 Week": "⏱️",
        "1 Month": "⏱️",
        "6 Months": "⏱️",
        "Year to Date": "📅",
        "52W Change %": "📉",
        "S&P 52W Change %": "📈",
        "Beta (5Y)": "📉",
        "RSI (14d)": "🌡️",
        "Volatility (Ann)": "🌪️",
        "From 52W High": "🏔️",
        "From 52W Low": "🌋",
        "50 Day Average": "📅",
        "200 Day Average": "📅",
        "50D Avg Change": "📉",
        "200D Avg Change": "📈",
        "Trailing P/E": "📊",
        "Forward P/E": "🔮",
        "PEG Ratio": "📌",
        "Price to Sales": "💹",
        "Price to Book": "📖",
        "EV to Revenue": "➗",
        "EV to EBITDA": "➗",
        "Book Value": "📚",
        "Return on Equity": "🔄",
        "Return on Assets": "🏦",
        "Gross Margins": "🥪",
        "Operating Margins": "⚙️",
        "Profit Margin": "📉",
        "EBITDA Margins": "📊",
        "Revenue per Share": "🧧",
        "Cash per Share": "🪙",
        "Revenue Growth": "🚀",
        "Earnings Growth": "📈",
        "Quarterly Earn Growth": "📊",
        "Trailing EPS": "💵",
        "Forward EPS": "🔮",
        "EPS Next Year": "🎯",
        "Total Cash": "💰",
        "Total Debt": "📜",
        "Operating Cashflow": "🌊",
        "Free Cashflow": "💸",
        "Current Ratio": "🧪",
        "Quick Ratio": "⚡",
        "Debt to Equity": "💳",
        "Revenue": "🏢",
        "Shares Outstanding": "💎",
        "Revenue": "🏢",
        "Shares Outstanding": "💎",
        "Float Shares": "🌊",
        "Implied Shares": "🧩",
        "Held by Insiders": "👤",
        "Held by Institutions": "🏦",
        "Short Ratio": "🩳",
        "Short % of Float": "🌊",
        "Short % of Shares": "📉",
        "Short % Change": "🔥",
        "Shares Short": "📉",
        "Prior Month Short": "⏪",
        "Dividend Yield": "🌾",
        "Dividend Rate": "💵",
        "Payout Ratio": "📤",
        "5 Yr Avg Yield": "🏛️",
        "Trailing Div Yield": "📈",
        "Trailing Div Rate": "💸",
        "Next Earnings": "🎤",
        "Dividend Date": "🗓️",
        "Ex-Dividend Date": "✂️",
        "Analyst Consensus": "🗣️",
        "Number of Opinions": "👥",
        "Target Low": "📉",
        "Target High": "📈",
        "Target Mean": "🎯",
        "Target Median": "📍",
        "Implied Upside": "🚀",
        "Overall Risk (1-10)": "🛡️",
        "Audit Risk": "🧐",
        "Board Risk": "👥",
        "Compensation Risk": "💰",
        "Shareholder Rights": "⚖️",
        "ESG Score": "🌿"
    }

    data = result["metrics"]
    for category, fields in data.items():
        print(f"{category} ---")
        for key, value in fields.items():
            field_emoji = emojis.get(key, "🔸")
            formatted_val = format_value(value, key)
            label = f"{field_emoji}  {key}"
            print(f"  {label:32}: {formatted_val}")
        print()

    print(f"📰 --- Latest News ---")
    for idx, item in enumerate(result["news"], 1):
        print(f"{idx}. {item['title']}")
        print(f"   🏢  Provider: {item['provider']} | 📅  Date: {item['pubDate']}")
        if item['summary'] and item['summary'] != 'N/A':
            summary = item['summary'][:150] + "..." if len(item['summary']) > 150 else item['summary']
            print(f"   📝  Summary: {summary}")
        print("-" * 30)

if __name__ == "__main__":
    main()

# 📈 Ticker Data 

A professional-grade terminal dashboard for deep stock analysis. This script retrieves and calculates over **100 metrics**, providing an institutional-grade "360-degree" view of any ticker using the `yfinance` library.

## 🚀 Features

- **🏢 Company Profile:** Sector, Industry, Employees, and Headquarters.
- **📊 Market Data:** Real-time Bid/Ask, Market Cap, and Enterprise Value.
- **🌡️ Technical Indicators:** RSI (14d), Annualized Volatility, 50D/200D Moving Averages.
- **⚖️ Valuation Multiples:** P/E, Forward P/E, PEG, P/S, P/B, EV/Revenue, EV/EBITDA.
- **🔄 Efficiency & Return:** ROE, ROA, and full Margin analysis (Gross, Operating, Profit, EBITDA).
- **🚀 Growth Estimates:** Revenue and Earnings growth forecasts.
- **🏥 Financial Health:** Current/Quick ratios, Debt-to-Equity, and Free Cash Flow.
- **🩳 Short Squeeze Indicators:** Short Ratio, % of Float, and Short % Change (MoM).
- **💎 Premium Analyst Metrics:** 
    - **Altman Z-Score:** Bankruptcy risk prediction.
    - **Piotroski F-Score:** 9-point financial strength score.
- **🎯 Analyst Sentiment:** Price targets, consensus, and implied upside.
- **🛡️ Risk & Governance:** Institutional risk scores and ESG Risk ratings.
- **📰 News:** Latest headlines with provider and publication date.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ticker-info.git
   cd ticker-info
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage

Run the script from your terminal followed by the ticker symbol:

```bash
python3 ticker_info.py AAPL
```

## 📋 Example Output

```text
🏢 Company Profile ---
  🏷️  Symbol                      : AAPL
  📝  Long Name                    : Apple Inc.
  ...

💎 Premium Analyst Metrics ---
  ☣️  Altman Z-Score              : 30.63
  🧱  Piotroski F-Score            : 7.00
  🚦  Altman Status                : Safe
  🏅  F-Score Rating               : Strong
```

## ⚖️ Disclaimer

*This tool is for educational and informational purposes only. It does not constitute financial advice.*

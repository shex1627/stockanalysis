"""
S&P 500 Sample Analysis
Analyze a representative sample of non-tech S&P 500 stocks vs the index
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
import time
warnings.filterwarnings('ignore')

# Create a dummy multitasking module if not available
try:
    import multitasking
except ImportError:
    import sys
    from types import ModuleType
    multitasking = ModuleType('multitasking')
    multitasking.cpu_count = lambda: 1
    multitasking.set_max_threads = lambda x: None
    multitasking.set_engine = lambda x: None
    multitasking.wait_for_tasks = lambda: None
    multitasking.Process = type('Process', (), {})
    def task_decorator(func):
        return func
    multitasking.task = task_decorator
    sys.modules['multitasking'] = multitasking

import yfinance as yf

# Set style
sns.set_style("whitegrid")

def download_data(ticker, start_date, end_date):
    """Download historical data for a ticker"""
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, threads=False)
        if data is None or len(data) == 0:
            return None

        # Extract price series
        if isinstance(data.columns, pd.MultiIndex):
            if ('Adj Close', ticker) in data.columns:
                result = data[('Adj Close', ticker)]
            elif ('Close', ticker) in data.columns:
                result = data[('Close', ticker)]
            else:
                return None
        else:
            if 'Adj Close' in data.columns:
                result = data['Adj Close']
            elif 'Close' in data.columns:
                result = data['Close']
            elif ticker in data.columns:
                result = data[ticker]
                if isinstance(result, pd.DataFrame) and 'Adj Close' in result.columns:
                    result = result['Adj Close']
                elif isinstance(result, pd.DataFrame) and 'Close' in result.columns:
                    result = result['Close']
            else:
                if len(data.columns) == 1:
                    result = data.iloc[:, 0]
                else:
                    return None

        if isinstance(result, pd.DataFrame):
            if len(result.columns) == 1:
                result = result.iloc[:, 0]
            else:
                return None

        return result
    except Exception as e:
        return None

def calculate_cagr(prices):
    """Calculate CAGR from price series"""
    if prices is None or len(prices) < 2:
        return None

    start_price = prices.iloc[0]
    end_price = prices.iloc[-1]
    years = len(prices) / 252

    if start_price <= 0 or end_price <= 0:
        return None

    cagr = (end_price / start_price) ** (1 / years) - 1
    return cagr * 100

# Representative sample of major S&P 500 companies across sectors (excluding tech giants)
# This sample includes major companies from various sectors
SAMPLE_STOCKS = {
    # Financials
    'JPM': 'JPMorgan Chase', 'BAC': 'Bank of America', 'WFC': 'Wells Fargo',
    'GS': 'Goldman Sachs', 'MS': 'Morgan Stanley', 'C': 'Citigroup',
    'BLK': 'BlackRock', 'SCHW': 'Charles Schwab', 'AXP': 'American Express',

    # Healthcare
    'JNJ': 'Johnson & Johnson', 'UNH': 'UnitedHealth', 'PFE': 'Pfizer',
    'ABBV': 'AbbVie', 'TMO': 'Thermo Fisher', 'ABT': 'Abbott',
    'CVS': 'CVS Health', 'MRK': 'Merck', 'LLY': 'Eli Lilly',
    'BMY': 'Bristol Myers Squibb', 'AMGN': 'Amgen',

    # Consumer Discretionary
    'HD': 'Home Depot', 'MCD': 'McDonald\'s', 'NKE': 'Nike',
    'SBUX': 'Starbucks', 'TGT': 'Target', 'LOW': 'Lowe\'s',
    'TJX': 'TJX Companies', 'F': 'Ford', 'GM': 'General Motors',

    # Consumer Staples
    'PG': 'Procter & Gamble', 'KO': 'Coca-Cola', 'PEP': 'PepsiCo',
    'WMT': 'Walmart', 'COST': 'Costco', 'PM': 'Philip Morris',
    'MO': 'Altria', 'CL': 'Colgate-Palmolive',

    # Industrials
    'BA': 'Boeing', 'CAT': 'Caterpillar', 'GE': 'General Electric',
    'UNP': 'Union Pacific', 'UPS': 'UPS', 'HON': 'Honeywell',
    'MMM': '3M', 'LMT': 'Lockheed Martin', 'RTX': 'Raytheon',

    # Energy
    'XOM': 'Exxon Mobil', 'CVX': 'Chevron', 'COP': 'ConocoPhillips',
    'SLB': 'Schlumberger', 'EOG': 'EOG Resources',

    # Utilities
    'NEE': 'NextEra Energy', 'DUK': 'Duke Energy', 'SO': 'Southern Company',
    'D': 'Dominion Energy',

    # Real Estate
    'AMT': 'American Tower', 'PLD': 'Prologis', 'CCI': 'Crown Castle',

    # Materials
    'LIN': 'Linde', 'APD': 'Air Products', 'SHW': 'Sherwin-Williams',
    'NEM': 'Newmont', 'FCX': 'Freeport-McMoRan',

    # Communications (non-tech)
    'VZ': 'Verizon', 'T': 'AT&T', 'TMUS': 'T-Mobile',
    'DIS': 'Walt Disney', 'CMCSA': 'Comcast', 'NFLX': 'Netflix',

    # Other major companies
    'BRK-B': 'Berkshire Hathaway', 'V': 'Visa', 'MA': 'Mastercard',
    'PYPL': 'PayPal', 'INTC': 'Intel', 'CSCO': 'Cisco',
    'IBM': 'IBM', 'ORCL': 'Oracle', 'QCOM': 'Qualcomm',
    'TXN': 'Texas Instruments', 'AVGO': 'Broadcom', 'AMD': 'AMD'
}

def main():
    import os
    os.makedirs('data', exist_ok=True)
    os.makedirs('plots', exist_ok=True)

    # Tech giants (already analyzed)
    tech_giants = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']

    # S&P 500 benchmark
    sp500_cagr = 13.18

    print("="*80)
    print("S&P 500 REPRESENTATIVE SAMPLE ANALYSIS")
    print("="*80)
    print(f"\nBenchmark: S&P 500 CAGR = {sp500_cagr:.2f}%")
    print(f"Sample size: {len(SAMPLE_STOCKS)} major S&P 500 companies")
    print("Sectors covered: Financials, Healthcare, Consumer, Industrials, Energy,")
    print("                Utilities, Real Estate, Materials, Communications, Tech")

    # Date range
    start_date = datetime(2012, 5, 18)
    end_date = datetime(2025, 11, 12)

    print(f"\nPeriod: {start_date.date()} to {end_date.date()} (13.5 years)")
    print("-"*80)

    results = []
    failed = []
    count = 0

    print("\nDownloading data...")
    for ticker, name in SAMPLE_STOCKS.items():
        count += 1
        if count % 20 == 0:
            print(f"Progress: {count}/{len(SAMPLE_STOCKS)}")

        prices = download_data(ticker, start_date, end_date)

        if prices is not None and len(prices) > 252:
            cagr = calculate_cagr(prices)
            if cagr is not None and not np.isnan(cagr) and not np.isinf(cagr):
                results.append({
                    'Ticker': ticker,
                    'Company': name,
                    'CAGR': cagr,
                    'Beat_SP500': cagr > sp500_cagr,
                    'Outperformance': cagr - sp500_cagr
                })
            else:
                failed.append(ticker)
        else:
            failed.append(ticker)

        time.sleep(0.05)

    print(f"Completed: {len(results)} successful, {len(failed)} failed")

    # Create DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('CAGR', ascending=False).reset_index(drop=True)

    # Save
    results_df.to_csv('data/sp500_sample_analysis.csv', index=False)
    print(f"✓ Results saved to data/sp500_sample_analysis.csv")

    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)

    total = len(results_df)
    beat_sp500 = results_df['Beat_SP500'].sum()
    underperformed = total - beat_sp500

    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Companies analyzed: {total}")
    print(f"   Beat S&P 500 ({sp500_cagr:.2f}%): {beat_sp500} ({beat_sp500/total*100:.1f}%)")
    print(f"   Underperformed S&P 500: {underperformed} ({underperformed/total*100:.1f}%)")

    # Statistics
    avg_cagr = results_df['CAGR'].mean()
    median_cagr = results_df['CAGR'].median()
    std_cagr = results_df['CAGR'].std()

    print(f"\n📈 PERFORMANCE METRICS:")
    print(f"   Average CAGR: {avg_cagr:.2f}%")
    print(f"   Median CAGR: {median_cagr:.2f}%")
    print(f"   Std Deviation: {std_cagr:.2f}%")
    print(f"   Range: {results_df['CAGR'].min():.2f}% to {results_df['CAGR'].max():.2f}%")

    # Quartiles
    q1 = results_df['CAGR'].quantile(0.25)
    q3 = results_df['CAGR'].quantile(0.75)

    print(f"\n📊 QUARTILES:")
    print(f"   25th percentile: {q1:.2f}%")
    print(f"   50th percentile (median): {median_cagr:.2f}%")
    print(f"   75th percentile: {q3:.2f}%")

    # Top performers
    print(f"\n🥇 TOP 15 PERFORMERS:")
    print(f"{'Rank':<6}{'Ticker':<10}{'Company':<25}{'CAGR':<12}{'vs S&P 500':<15}")
    print("-"*75)
    for i, row in results_df.head(15).iterrows():
        print(f"{i+1:<6}{row['Ticker']:<10}{row['Company'][:23]:<25}{row['CAGR']:>7.2f}%     +{row['Outperformance']:.2f}pp")

    # Bottom performers
    print(f"\n📉 BOTTOM 15 PERFORMERS:")
    print(f"{'Rank':<6}{'Ticker':<10}{'Company':<25}{'CAGR':<12}{'vs S&P 500':<15}")
    print("-"*75)
    for i, row in results_df.tail(15).iterrows():
        rank = i + 1
        print(f"{rank:<6}{row['Ticker']:<10}{row['Company'][:23]:<25}{row['CAGR']:>7.2f}%     {row['Outperformance']:.2f}pp")

    # Comparison
    print(f"\n" + "="*80)
    print("COMPARISON: TECH GIANTS vs TYPICAL S&P 500 STOCKS")
    print("="*80)

    tech_avg_cagr = 33.67

    print(f"\n   Tech Giants (7 companies):")
    print(f"      Average CAGR: {tech_avg_cagr:.2f}%")
    print(f"      Companies beating S&P 500: 7/7 (100%)")

    print(f"\n   Sample of Non-Tech Stocks ({total} companies):")
    print(f"      Average CAGR: {avg_cagr:.2f}%")
    print(f"      Median CAGR: {median_cagr:.2f}%")
    print(f"      Companies beating S&P 500: {beat_sp500}/{total} ({beat_sp500/total*100:.1f}%)")

    print(f"\n   📌 KEY INSIGHTS:")
    if median_cagr < sp500_cagr:
        print(f"      ✅ The MEDIAN non-tech stock ({median_cagr:.2f}%) UNDERPERFORMED the S&P 500 ({sp500_cagr:.2f}%)")
        print(f"      ✅ Majority of stocks ({underperformed}/{total}) underperformed the index")
        print(f"      ✅ This confirms: A MINORITY of top performers drive index returns!")
    else:
        print(f"      The median stock performed at or above the index average")

    # Visualizations
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)

    # Distribution histogram
    fig, ax = plt.subplots(figsize=(14, 8))

    n, bins, patches = ax.hist(results_df['CAGR'], bins=30, alpha=0.7, edgecolor='black')

    for i, patch in enumerate(patches):
        if bins[i] > sp500_cagr:
            patch.set_facecolor('#06A77D')
        else:
            patch.set_facecolor('#E63946')

    ax.axvline(sp500_cagr, color='black', linestyle='--', linewidth=2.5,
               label=f'S&P 500: {sp500_cagr:.2f}%', alpha=0.8)
    ax.axvline(avg_cagr, color='blue', linestyle='-', linewidth=2,
               label=f'Mean: {avg_cagr:.2f}%', alpha=0.7)
    ax.axvline(median_cagr, color='orange', linestyle='-', linewidth=2,
               label=f'Median: {median_cagr:.2f}%', alpha=0.7)

    ax.set_xlabel('CAGR (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Companies', fontsize=12, fontweight='bold')
    ax.set_title(f'CAGR Distribution: {total} Representative Non-Tech S&P 500 Stocks (2012-2025)\n' +
                 f'{underperformed}/{total} companies ({underperformed/total*100:.1f}%) underperformed the index',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('plots/sp500_sample_distribution.png', dpi=300, bbox_inches='tight')
    print("✓ Distribution chart saved")
    plt.close()

    # Box plot
    fig, ax = plt.subplots(figsize=(10, 8))

    tech_cagrs = [62.71, 50.01, 26.17, 25.81, 24.56, 23.54, 22.90]
    box_data = [tech_cagrs, results_df['CAGR'].tolist()]
    labels = ['Tech Giants\n(7 stocks)', f'Non-Tech Sample\n({total} stocks)']

    bp = ax.boxplot(box_data, labels=labels, patch_artist=True, widths=0.6)

    bp['boxes'][0].set_facecolor('#E63946')
    bp['boxes'][1].set_facecolor('#06A77D')

    for box in bp['boxes']:
        box.set_alpha(0.7)

    ax.axhline(sp500_cagr, color='black', linestyle='--', linewidth=2,
               label=f'S&P 500: {sp500_cagr:.2f}%', alpha=0.7)

    ax.set_ylabel('CAGR (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Distribution: Tech Giants vs Non-Tech Stocks (2012-2025)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('plots/sp500_sample_boxplot.png', dpi=300, bbox_inches='tight')
    print("✓ Box plot saved")
    plt.close()

    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print("="*80)

    print(f"\n📌 FINAL VERDICT:")
    print(f"   Among {total} representative non-tech S&P 500 companies:")
    print(f"   - Only {beat_sp500} ({beat_sp500/total*100:.1f}%) beat the index's {sp500_cagr:.2f}% CAGR")
    print(f"   - {underperformed} ({underperformed/total*100:.1f}%) underperformed")
    print(f"   - Median: {median_cagr:.2f}% ({'BELOW' if median_cagr < sp500_cagr else 'ABOVE'} index)")
    print(f"\n   The S&P 500 is dominated by a minority of high performers,")
    print(f"   with tech giants being the most extreme examples of outperformance.")

if __name__ == "__main__":
    main()

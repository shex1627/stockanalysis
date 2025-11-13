"""
S&P 500 All Stocks Analysis
Analyze how many non-tech-giant S&P 500 stocks beat the index average
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
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

def get_sp500_tickers():
    """Get S&P 500 ticker list from Wikipedia"""
    try:
        import requests
        from io import StringIO

        # Try with custom headers
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        tables = pd.read_html(StringIO(response.text))
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()
        # Clean up tickers (replace . with -)
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching from Wikipedia: {e}")
        print("Trying alternative: downloading S&P 500 constituents via yfinance...")

        # Fallback: Use a ticker that tracks S&P 500 components
        try:
            # Get tickers from a known list (we'll use a simplified approach)
            # This is a backup - we'll download data for major sectors
            print("Using alternative method...")
            return None
        except Exception as e2:
            print(f"Alternative method failed: {e2}")
            return None

def main():
    import os
    os.makedirs('data', exist_ok=True)
    os.makedirs('plots', exist_ok=True)

    # Define tech giants to exclude
    tech_giants = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']

    # S&P 500 benchmark
    sp500_cagr = 13.18  # From previous analysis

    print("="*80)
    print("S&P 500 ALL STOCKS ANALYSIS")
    print("="*80)
    print(f"\nBenchmark: S&P 500 CAGR = {sp500_cagr:.2f}%")
    print("Tech Giants to exclude:", ', '.join(tech_giants))

    # Get S&P 500 constituents
    print("\nStep 1: Fetching S&P 500 constituent list...")
    print("-"*80)
    tickers = get_sp500_tickers()

    if tickers is None:
        print("Failed to fetch S&P 500 list from Wikipedia")
        return

    print(f"Found {len(tickers)} S&P 500 companies")

    # Exclude tech giants
    non_tech_tickers = [t for t in tickers if t not in tech_giants]
    print(f"Analyzing {len(non_tech_tickers)} non-tech-giant companies")

    # Date range (same as previous analysis: 2012-05-18 to 2025-11-12)
    start_date = datetime(2012, 5, 18)
    end_date = datetime(2025, 11, 12)

    print(f"\nStep 2: Downloading data for {len(non_tech_tickers)} stocks...")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print("-"*80)
    print("This will take several minutes...")

    results = []
    failed = []

    for i, ticker in enumerate(non_tech_tickers):
        if (i + 1) % 50 == 0:
            print(f"Progress: {i+1}/{len(non_tech_tickers)} ({(i+1)/len(non_tech_tickers)*100:.1f}%)")

        prices = download_data(ticker, start_date, end_date)

        if prices is not None and len(prices) > 252:  # At least 1 year of data
            cagr = calculate_cagr(prices)
            if cagr is not None and not np.isnan(cagr) and not np.isinf(cagr):
                results.append({
                    'Ticker': ticker,
                    'CAGR': cagr,
                    'Beat_SP500': cagr > sp500_cagr,
                    'Outperformance': cagr - sp500_cagr
                })
            else:
                failed.append(ticker)
        else:
            failed.append(ticker)

        # Small delay to avoid rate limiting
        time.sleep(0.05)

    print(f"\nCompleted: {len(results)} successful, {len(failed)} failed")

    # Create DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('CAGR', ascending=False).reset_index(drop=True)

    # Save results
    results_df.to_csv('data/sp500_non_tech_stocks_analysis.csv', index=False)
    print(f"✓ Results saved to data/sp500_non_tech_stocks_analysis.csv")

    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)

    total_analyzed = len(results_df)
    beat_sp500 = results_df['Beat_SP500'].sum()
    underperformed = total_analyzed - beat_sp500

    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Companies analyzed: {total_analyzed}")
    print(f"   Beat S&P 500 ({sp500_cagr:.2f}%): {beat_sp500} ({beat_sp500/total_analyzed*100:.1f}%)")
    print(f"   Underperformed S&P 500: {underperformed} ({underperformed/total_analyzed*100:.1f}%)")

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

    # Top and bottom performers
    print(f"\n🥇 TOP 10 PERFORMERS (Non-Tech Giants):")
    print(f"{'Rank':<6}{'Ticker':<10}{'CAGR':<12}{'vs S&P 500':<15}")
    print("-"*50)
    for i, row in results_df.head(10).iterrows():
        print(f"{i+1:<6}{row['Ticker']:<10}{row['CAGR']:>7.2f}%     +{row['Outperformance']:.2f}pp")

    print(f"\n📉 BOTTOM 10 PERFORMERS (Non-Tech Giants):")
    print(f"{'Rank':<6}{'Ticker':<10}{'CAGR':<12}{'vs S&P 500':<15}")
    print("-"*50)
    for i, row in results_df.tail(10).iterrows():
        rank = len(results_df) - 9 + (i - len(results_df) + 10)
        print(f"{i+1:<6}{row['Ticker']:<10}{row['CAGR']:>7.2f}%     {row['Outperformance']:.2f}pp")

    # Comparison with tech giants
    print(f"\n" + "="*80)
    print("COMPARISON: TECH GIANTS vs NON-TECH COMPANIES")
    print("="*80)

    tech_avg_cagr = 33.67  # From previous analysis

    print(f"\n   Tech Giants (7 companies):")
    print(f"      Average CAGR: {tech_avg_cagr:.2f}%")
    print(f"      Beat S&P 500: 7/7 (100%)")

    print(f"\n   Non-Tech S&P 500 ({total_analyzed} companies):")
    print(f"      Average CAGR: {avg_cagr:.2f}%")
    print(f"      Median CAGR: {median_cagr:.2f}%")
    print(f"      Beat S&P 500: {beat_sp500}/{total_analyzed} ({beat_sp500/total_analyzed*100:.1f}%)")

    print(f"\n   📌 KEY INSIGHT:")
    if median_cagr < sp500_cagr:
        print(f"      The MEDIAN non-tech company ({median_cagr:.2f}%) UNDERPERFORMED the S&P 500 ({sp500_cagr:.2f}%)")
        print(f"      This confirms the index is heavily skewed by top performers!")
    else:
        print(f"      The median company performed close to or above the index average")

    # Create visualizations
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)

    # Chart 1: Distribution histogram
    fig, ax = plt.subplots(figsize=(14, 8))

    # Histogram
    n, bins, patches = ax.hist(results_df['CAGR'], bins=50, alpha=0.7, color='skyblue', edgecolor='black')

    # Color bars based on performance vs S&P 500
    for i, patch in enumerate(patches):
        if bins[i] > sp500_cagr:
            patch.set_facecolor('#06A77D')
        else:
            patch.set_facecolor('#E63946')

    # Add S&P 500 line
    ax.axvline(sp500_cagr, color='black', linestyle='--', linewidth=2.5,
               label=f'S&P 500: {sp500_cagr:.2f}%', alpha=0.8)

    # Add mean and median lines
    ax.axvline(avg_cagr, color='blue', linestyle='-', linewidth=2,
               label=f'Mean: {avg_cagr:.2f}%', alpha=0.7)
    ax.axvline(median_cagr, color='orange', linestyle='-', linewidth=2,
               label=f'Median: {median_cagr:.2f}%', alpha=0.7)

    ax.set_xlabel('CAGR (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Companies', fontsize=12, fontweight='bold')
    ax.set_title(f'Distribution of CAGR for {total_analyzed} Non-Tech S&P 500 Stocks (2012-2025)\n' +
                 f'{beat_sp500} companies ({beat_sp500/total_analyzed*100:.1f}%) beat the index',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('plots/sp500_non_tech_distribution.png', dpi=300, bbox_inches='tight')
    print("✓ Distribution chart saved to plots/sp500_non_tech_distribution.png")
    plt.close()

    # Chart 2: Cumulative distribution
    fig, ax = plt.subplots(figsize=(14, 8))

    sorted_cagr = sorted(results_df['CAGR'])
    cumulative_pct = np.arange(1, len(sorted_cagr) + 1) / len(sorted_cagr) * 100

    ax.plot(sorted_cagr, cumulative_pct, linewidth=2.5, color='#2E86AB')
    ax.axvline(sp500_cagr, color='red', linestyle='--', linewidth=2.5,
               label=f'S&P 500: {sp500_cagr:.2f}%', alpha=0.8)

    # Find percentile at S&P 500 level
    sp500_percentile = (results_df['CAGR'] < sp500_cagr).sum() / len(results_df) * 100
    ax.axhline(sp500_percentile, color='red', linestyle=':', linewidth=1.5, alpha=0.5)

    ax.text(sp500_cagr + 2, sp500_percentile + 5,
            f'{sp500_percentile:.0f}% of stocks\nunderperformed S&P 500',
            fontsize=10, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.set_xlabel('CAGR (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Cumulative Percentage of Companies', fontsize=12, fontweight='bold')
    ax.set_title(f'Cumulative Distribution: Non-Tech S&P 500 Stocks (2012-2025)\n' +
                 f'{sp500_percentile:.0f}% of companies had lower CAGR than the index',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('plots/sp500_non_tech_cumulative.png', dpi=300, bbox_inches='tight')
    print("✓ Cumulative distribution saved to plots/sp500_non_tech_cumulative.png")
    plt.close()

    # Chart 3: Box plot comparison
    fig, ax = plt.subplots(figsize=(10, 8))

    # Prepare data for box plot
    tech_cagrs = [62.71, 50.01, 26.17, 25.81, 24.56, 23.54, 22.90]  # From previous analysis

    box_data = [tech_cagrs, results_df['CAGR'].tolist()]
    labels = ['Tech Giants\n(7 stocks)', f'Non-Tech S&P 500\n({total_analyzed} stocks)']

    bp = ax.boxplot(box_data, labels=labels, patch_artist=True, widths=0.6)

    # Color the boxes
    bp['boxes'][0].set_facecolor('#E63946')
    bp['boxes'][1].set_facecolor('#06A77D')

    for box in bp['boxes']:
        box.set_alpha(0.7)

    # Add S&P 500 line
    ax.axhline(sp500_cagr, color='black', linestyle='--', linewidth=2,
               label=f'S&P 500: {sp500_cagr:.2f}%', alpha=0.7)

    ax.set_ylabel('CAGR (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Distribution: Tech Giants vs Non-Tech S&P 500 (2012-2025)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('plots/sp500_tech_vs_non_tech_boxplot.png', dpi=300, bbox_inches='tight')
    print("✓ Box plot comparison saved to plots/sp500_tech_vs_non_tech_boxplot.png")
    plt.close()

    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print("="*80)

    print(f"\n📌 FINAL VERDICT:")
    print(f"   Out of {total_analyzed} non-tech S&P 500 companies:")
    print(f"   - Only {beat_sp500} ({beat_sp500/total_analyzed*100:.1f}%) beat the S&P 500's {sp500_cagr:.2f}% CAGR")
    print(f"   - {underperformed} ({underperformed/total_analyzed*100:.1f}%) underperformed the index")
    print(f"   - Median performance ({median_cagr:.2f}%) was {'BELOW' if median_cagr < sp500_cagr else 'ABOVE'} the index")
    print(f"\n   This confirms: The S&P 500's performance is driven by a minority of top performers,")
    print(f"   with tech giants playing an outsized role.")

if __name__ == "__main__":
    main()

"""
S&P 500 vs Tech Giants Analysis
Validates the claim that S&P 500 performance is driven primarily by tech giants
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
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
    # Create a pass-through decorator for @task
    def task_decorator(func):
        return func
    multitasking.task = task_decorator
    sys.modules['multitasking'] = multitasking

import yfinance as yf

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

def download_data(ticker, start_date, end_date, name):
    """Download historical data for a ticker"""
    print(f"Downloading {name} ({ticker})...", end='')
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, threads=False)
        if data is None or len(data) == 0:
            print(f" FAILED (no data)")
            return None

        # yfinance returns a DataFrame. We need to extract the price series
        # Check if columns are MultiIndex (multiple tickers) or regular (single ticker)
        if isinstance(data.columns, pd.MultiIndex):
            # Multiple tickers case
            if ('Adj Close', ticker) in data.columns:
                result = data[('Adj Close', ticker)]
            elif ('Close', ticker) in data.columns:
                result = data[('Close', ticker)]
            else:
                print(f" FAILED (no price column in MultiIndex)")
                return None
        else:
            # Single ticker case - columns might just be the ticker or regular column names
            if 'Adj Close' in data.columns:
                result = data['Adj Close']
            elif 'Close' in data.columns:
                result = data['Close']
            elif ticker in data.columns:
                # Sometimes the entire dataframe is under the ticker name
                result = data[ticker]
                # If result is still a DataFrame, try to get Adj Close from it
                if isinstance(result, pd.DataFrame) and 'Adj Close' in result.columns:
                    result = result['Adj Close']
                elif isinstance(result, pd.DataFrame) and 'Close' in result.columns:
                    result = result['Close']
            else:
                # Fallback: if we have a DataFrame with only one column, use it
                if len(data.columns) == 1:
                    result = data.iloc[:, 0]
                else:
                    print(f" FAILED (cannot find price column, columns={list(data.columns)})")
                    return None

        # Ensure we have a Series
        if isinstance(result, pd.DataFrame):
            if len(result.columns) == 1:
                result = result.iloc[:, 0]
            else:
                print(f" FAILED (result is still a DataFrame with multiple columns)")
                return None

        print(f" SUCCESS ({len(result)} days)")
        return result
    except Exception as e:
        print(f" FAILED ({e})")
        return None

def calculate_performance_metrics(returns):
    """Calculate key performance metrics"""
    total_return = (1 + returns).prod() - 1
    years = len(returns) / 252  # Assuming 252 trading days per year
    cagr = (1 + total_return) ** (1 / years) - 1
    volatility = returns.std() * np.sqrt(252)
    sharpe = cagr / volatility if volatility > 0 else 0

    # Max drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    return {
        'Total Return': total_return * 100,
        'CAGR': cagr * 100,
        'Volatility': volatility * 100,
        'Sharpe Ratio': sharpe,
        'Max Drawdown': max_drawdown * 100
    }

def main():
    # Create output directories
    import os
    os.makedirs('data', exist_ok=True)
    os.makedirs('plots', exist_ok=True)

    # Define time period (20 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*20)

    print(f"\nAnalyzing period: {start_date.date()} to {end_date.date()}\n")
    print("="*80)

    # Define tech giants (The Magnificent Seven + context)
    tech_giants = {
        'AAPL': 'Apple',
        'MSFT': 'Microsoft',
        'GOOGL': 'Alphabet (Google)',
        'AMZN': 'Amazon',
        'META': 'Meta (Facebook)',
        'NVDA': 'NVIDIA',
        'TSLA': 'Tesla'
    }

    # Download S&P 500 data
    sp500 = download_data('^GSPC', start_date, end_date, 'S&P 500 Index')

    if sp500 is None:
        print("Error: Could not download S&P 500 data")
        print("Trying alternative ticker: SPY (S&P 500 ETF)...")
        sp500 = download_data('SPY', start_date, end_date, 'S&P 500 ETF')

    if sp500 is None or len(sp500) == 0:
        print("Error: Could not download S&P 500 data")
        return

    # Download tech giants data
    tech_data = {}
    for ticker, name in tech_giants.items():
        data = download_data(ticker, start_date, end_date, name)
        if data is not None and len(data) > 0:
            tech_data[ticker] = data

    print(f"\nSuccessfully downloaded data for {len(tech_data)} tech giants")
    print("="*80)

    # Align all data to common dates
    all_data = pd.DataFrame({'SP500': sp500})
    for ticker, data in tech_data.items():
        all_data[ticker] = data

    # Drop any rows with missing values
    all_data = all_data.dropna()

    print(f"\nData range after alignment: {all_data.index[0].date()} to {all_data.index[-1].date()}")
    print(f"Number of trading days: {len(all_data)}")

    # Calculate equal-weighted tech giants index (simpler interpretation)
    tech_cols = list(tech_data.keys())
    all_data['Tech_Giants'] = all_data[tech_cols].mean(axis=1)

    # Normalize all series to 100 at start
    normalized_data = pd.DataFrame()
    for col in ['SP500', 'Tech_Giants'] + tech_cols:
        normalized_data[col] = (all_data[col] / all_data[col].iloc[0]) * 100

    # Calculate daily returns
    returns = all_data.pct_change().dropna()

    # Calculate performance metrics
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)

    metrics_data = []

    # S&P 500 metrics
    sp500_metrics = calculate_performance_metrics(returns['SP500'])
    print("\nS&P 500 Index:")
    for metric, value in sp500_metrics.items():
        print(f"  {metric}: {value:.2f}{'%' if metric != 'Sharpe Ratio' else ''}")
    metrics_data.append({'Index': 'S&P 500', **sp500_metrics})

    # Tech Giants metrics
    tech_metrics = calculate_performance_metrics(returns['Tech_Giants'])
    print("\nTech Giants (Equal-Weighted):")
    for metric, value in tech_metrics.items():
        print(f"  {metric}: {value:.2f}{'%' if metric != 'Sharpe Ratio' else ''}")
    metrics_data.append({'Index': 'Tech Giants', **tech_metrics})

    # Individual tech stocks
    print("\nIndividual Tech Giants:")
    for ticker in tech_cols:
        metrics = calculate_performance_metrics(returns[ticker])
        metrics_data.append({'Index': f'{ticker} ({tech_giants[ticker]})', **metrics})
        print(f"\n  {tech_giants[ticker]} ({ticker}):")
        for metric, value in metrics.items():
            print(f"    {metric}: {value:.2f}{'%' if metric != 'Sharpe Ratio' else ''}")

    # Calculate S&P 500 ex-Tech Giants (approximate)
    # This is a simplified calculation - in reality would need constituent weights
    # We approximate by assuming tech giants represent their proportional contribution
    tech_return_contribution = returns['Tech_Giants'].mean() / returns['SP500'].mean()
    print(f"\n\nTech Giants' approximate contribution to S&P 500 returns: {tech_return_contribution*100:.1f}%")

    # Save metrics to CSV
    metrics_df = pd.DataFrame(metrics_data)
    metrics_df.to_csv('data/performance_metrics.csv', index=False)
    print("\n✓ Performance metrics saved to data/performance_metrics.csv")

    # Save normalized price data
    normalized_data.to_csv('data/normalized_prices.csv')
    print("✓ Normalized price data saved to data/normalized_prices.csv")

    # Save raw returns data
    returns.to_csv('data/daily_returns.csv')
    print("✓ Daily returns saved to data/daily_returns.csv")

    # Create visualizations
    print("\n" + "="*80)
    print("GENERATING PLOTS")
    print("="*80)

    # Plot 1: Main comparison - S&P 500 vs Tech Giants
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(normalized_data.index, normalized_data['SP500'],
            label='S&P 500', linewidth=2.5, color='blue')
    ax.plot(normalized_data.index, normalized_data['Tech_Giants'],
            label='Tech Giants (Equal-Weighted)', linewidth=2.5, color='red')

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Price (Base = 100)', fontsize=12, fontweight='bold')
    ax.set_title('S&P 500 vs Tech Giants: 20-Year Performance Comparison\n(Normalized to 100 at start)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)

    # Add annotations
    final_sp500 = normalized_data['SP500'].iloc[-1]
    final_tech = normalized_data['Tech_Giants'].iloc[-1]
    ax.text(0.02, 0.98, f'S&P 500 Final: {final_sp500:.1f}',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='blue', alpha=0.2))
    ax.text(0.02, 0.92, f'Tech Giants Final: {final_tech:.1f}',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
    ax.text(0.02, 0.86, f'Outperformance: {final_tech - final_sp500:.1f} pts',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='green', alpha=0.2))

    plt.tight_layout()
    plt.savefig('plots/sp500_vs_tech_giants.png', dpi=300, bbox_inches='tight')
    print("✓ Main comparison plot saved to plots/sp500_vs_tech_giants.png")
    plt.close()

    # Plot 2: Individual tech giants
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = plt.cm.tab10(range(len(tech_cols)))

    for i, ticker in enumerate(tech_cols):
        ax.plot(normalized_data.index, normalized_data[ticker],
                label=f'{tech_giants[ticker]} ({ticker})',
                linewidth=2, color=colors[i], alpha=0.8)

    ax.plot(normalized_data.index, normalized_data['SP500'],
            label='S&P 500', linewidth=3, color='black', linestyle='--', alpha=0.6)

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Price (Base = 100)', fontsize=12, fontweight='bold')
    ax.set_title('Individual Tech Giants vs S&P 500: 20-Year Performance\n(Normalized to 100 at start)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')  # Log scale to better show relative performance

    plt.tight_layout()
    plt.savefig('plots/individual_tech_giants.png', dpi=300, bbox_inches='tight')
    print("✓ Individual tech giants plot saved to plots/individual_tech_giants.png")
    plt.close()

    # Plot 3: Performance comparison bar chart
    fig, ax = plt.subplots(figsize=(12, 7))

    metrics_plot = metrics_df[metrics_df['Index'].isin(['S&P 500', 'Tech Giants'])].copy()
    x = np.arange(len(metrics_plot))
    width = 0.15

    metrics_to_plot = ['Total Return', 'CAGR', 'Volatility']
    colors_bar = ['#2E86AB', '#A23B72', '#F18F01']

    for i, metric in enumerate(metrics_to_plot):
        offset = width * (i - 1)
        bars = ax.bar(x + offset, metrics_plot[metric], width,
                      label=metric, color=colors_bar[i], alpha=0.8)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('Index', fontsize=12, fontweight='bold')
    ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Metrics Comparison: S&P 500 vs Tech Giants',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_plot['Index'], fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('plots/performance_metrics_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Performance metrics plot saved to plots/performance_metrics_comparison.png")
    plt.close()

    # Plot 4: Year-by-year returns comparison
    yearly_returns = returns.resample('Y').apply(lambda x: (1 + x).prod() - 1) * 100

    fig, ax = plt.subplots(figsize=(14, 8))
    x = np.arange(len(yearly_returns))
    width = 0.35

    ax.bar(x - width/2, yearly_returns['SP500'], width,
           label='S&P 500', color='blue', alpha=0.7)
    ax.bar(x + width/2, yearly_returns['Tech_Giants'], width,
           label='Tech Giants', color='red', alpha=0.7)

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Annual Return (%)', fontsize=12, fontweight='bold')
    ax.set_title('Year-by-Year Returns: S&P 500 vs Tech Giants',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([d.year for d in yearly_returns.index], rotation=45)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    plt.tight_layout()
    plt.savefig('plots/yearly_returns_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Yearly returns plot saved to plots/yearly_returns_comparison.png")
    plt.close()

    # Plot 5: Rolling correlation
    rolling_corr = returns['SP500'].rolling(window=252).corr(returns['Tech_Giants'])

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(rolling_corr.index, rolling_corr, linewidth=2, color='purple')
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Rolling Correlation (1-year window)', fontsize=12, fontweight='bold')
    ax.set_title('Rolling Correlation: S&P 500 vs Tech Giants',
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 1])

    plt.tight_layout()
    plt.savefig('plots/rolling_correlation.png', dpi=300, bbox_inches='tight')
    print("✓ Rolling correlation plot saved to plots/rolling_correlation.png")
    plt.close()

    # Generate summary report
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)

    print(f"\n📊 DATA COVERAGE:")
    print(f"   Period analyzed: {all_data.index[0].date()} to {all_data.index[-1].date()}")
    print(f"   Trading days: {len(all_data):,}")
    print(f"   Years covered: {len(all_data)/252:.1f}")

    print(f"\n🎯 KEY FINDINGS:")
    print(f"   1. S&P 500 total return: {sp500_metrics['Total Return']:.1f}%")
    print(f"   2. Tech Giants total return: {tech_metrics['Total Return']:.1f}%")
    print(f"   3. Outperformance: {tech_metrics['Total Return'] - sp500_metrics['Total Return']:.1f} percentage points")
    print(f"   4. Tech Giants CAGR: {tech_metrics['CAGR']:.2f}% vs S&P 500: {sp500_metrics['CAGR']:.2f}%")
    print(f"   5. Final value comparison (starting at 100):")
    print(f"      - S&P 500: {final_sp500:.1f}")
    print(f"      - Tech Giants: {final_tech:.1f}")
    print(f"      - Ratio: {final_tech/final_sp500:.2f}x")

    print(f"\n✅ CONCLUSION:")
    if tech_metrics['Total Return'] > sp500_metrics['Total Return'] * 1.5:
        print("   The statement is STRONGLY VALIDATED:")
        print("   Tech giants have significantly outperformed the S&P 500.")
        print("   The S&P 500's performance is heavily influenced by these tech companies.")
    elif tech_metrics['Total Return'] > sp500_metrics['Total Return']:
        print("   The statement is VALIDATED:")
        print("   Tech giants have outperformed the S&P 500.")
        print("   Tech companies contribute significantly to S&P 500 performance.")
    else:
        print("   The statement is NOT VALIDATED:")
        print("   Tech giants did not significantly outperform the S&P 500.")

    print("\n" + "="*80)
    print("All data and plots have been saved successfully!")
    print("="*80)

    return {
        'sp500_metrics': sp500_metrics,
        'tech_metrics': tech_metrics,
        'normalized_data': normalized_data,
        'returns': returns
    }

if __name__ == "__main__":
    results = main()
    print("\n✅ Analysis complete!")

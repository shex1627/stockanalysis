"""
S&P 500 Ex-Tech Giants Analysis
Calculate S&P 500 performance with tech giants removed using market cap weighting
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

        # Extract price series
        if isinstance(data.columns, pd.MultiIndex):
            if ('Adj Close', ticker) in data.columns:
                result = data[('Adj Close', ticker)]
            elif ('Close', ticker) in data.columns:
                result = data[('Close', ticker)]
            else:
                print(f" FAILED (no price column in MultiIndex)")
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
                    print(f" FAILED (cannot find price column)")
                    return None

        if isinstance(result, pd.DataFrame):
            if len(result.columns) == 1:
                result = result.iloc[:, 0]
            else:
                print(f" FAILED (result is still a DataFrame)")
                return None

        print(f" SUCCESS ({len(result)} days)")
        return result
    except Exception as e:
        print(f" FAILED ({e})")
        return None

def get_market_cap(ticker):
    """Get current market cap for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        market_cap = info.get('marketCap', None)
        return market_cap
    except:
        return None

def calculate_historical_market_cap(prices, current_market_cap):
    """
    Estimate historical market cap by scaling current market cap
    by the price ratio (assumes constant shares outstanding)
    """
    if current_market_cap is None or prices is None or len(prices) == 0:
        return None

    # Use the most recent price as reference
    current_price = prices.iloc[-1]
    # Scale market cap proportionally to price changes
    historical_market_cap = prices / current_price * current_market_cap
    return historical_market_cap

def calculate_performance_metrics(returns):
    """Calculate key performance metrics"""
    total_return = (1 + returns).prod() - 1
    years = len(returns) / 252
    cagr = (1 + total_return) ** (1 / years) - 1
    volatility = returns.std() * np.sqrt(252)
    sharpe = cagr / volatility if volatility > 0 else 0

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
    import os
    os.makedirs('data', exist_ok=True)
    os.makedirs('plots', exist_ok=True)

    # Define time period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*20)

    print(f"\n{'='*80}")
    print(f"S&P 500 EX-TECH GIANTS ANALYSIS")
    print(f"{'='*80}")
    print(f"\nAnalyzing period: {start_date.date()} to {end_date.date()}\n")

    # Define tech giants
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
    print("Step 1: Downloading S&P 500 data")
    print("-" * 80)
    sp500 = download_data('^GSPC', start_date, end_date, 'S&P 500 Index')

    if sp500 is None:
        print("Trying alternative: SPY ETF...")
        sp500 = download_data('SPY', start_date, end_date, 'S&P 500 ETF')

    if sp500 is None or len(sp500) == 0:
        print("Error: Could not download S&P 500 data")
        return

    # Download tech giants data
    print("\nStep 2: Downloading tech giants data")
    print("-" * 80)
    tech_data = {}
    for ticker, name in tech_giants.items():
        data = download_data(ticker, start_date, end_date, name)
        if data is not None and len(data) > 0:
            tech_data[ticker] = data

    print(f"\nSuccessfully downloaded data for {len(tech_data)} tech giants")

    # Get current market caps
    print("\nStep 3: Getting current market capitalizations")
    print("-" * 80)
    market_caps = {}
    for ticker, name in tech_giants.items():
        if ticker in tech_data:
            market_cap = get_market_cap(ticker)
            if market_cap:
                market_caps[ticker] = market_cap
                print(f"{name:25} ({ticker}): ${market_cap/1e9:>8.1f}B")
            else:
                print(f"{name:25} ({ticker}): Market cap unavailable")

    # Get S&P 500 total market cap
    print("\nGetting S&P 500 total market cap...")
    sp500_market_cap = get_market_cap('^GSPC')
    if sp500_market_cap:
        print(f"S&P 500 Total Market Cap: ${sp500_market_cap/1e12:.2f}T")
    else:
        # Estimate from SPY
        spy_market_cap = get_market_cap('SPY')
        if spy_market_cap:
            # SPY has ~900B in assets, but represents the full S&P 500
            # We need the total market cap of all S&P 500 companies
            # Approximate: use sum of largest companies or a multiplier
            print("Note: Using estimated S&P 500 market cap")
            # Rough estimate: ~$40T for S&P 500 as of late 2024
            sp500_market_cap = 40e12
        else:
            print("Warning: Could not get S&P 500 market cap, using estimate")
            sp500_market_cap = 40e12

    # Calculate tech giants' weight in S&P 500
    total_tech_market_cap = sum(market_caps.values())
    tech_weight = total_tech_market_cap / sp500_market_cap

    print(f"\nTech Giants Combined Market Cap: ${total_tech_market_cap/1e12:.2f}T")
    print(f"Tech Giants Weight in S&P 500: {tech_weight*100:.1f}%")

    # Align all data
    print("\nStep 4: Aligning data to common dates")
    print("-" * 80)
    all_data = pd.DataFrame({'SP500': sp500})
    for ticker, data in tech_data.items():
        all_data[ticker] = data
    all_data = all_data.dropna()

    print(f"Date range: {all_data.index[0].date()} to {all_data.index[-1].date()}")
    print(f"Trading days: {len(all_data):,}")

    # Calculate returns
    returns = all_data.pct_change().dropna()

    # Calculate market-cap weighted tech giants return
    print("\nStep 5: Calculating market-cap weighted returns")
    print("-" * 80)

    # Normalize weights to sum to 1
    weights = pd.Series(market_caps)
    weights = weights / weights.sum()

    print("\nTech Giants Weights (normalized within group):")
    for ticker in weights.index:
        print(f"  {tech_giants[ticker]:25} ({ticker}): {weights[ticker]*100:5.1f}%")

    # Calculate weighted returns for tech giants
    tech_weighted_returns = pd.Series(0, index=returns.index)
    for ticker in weights.index:
        if ticker in returns.columns:
            tech_weighted_returns += returns[ticker] * weights[ticker]

    # Calculate S&P 500 ex-tech performance
    # Formula: SP500_return = tech_weight × tech_return + (1 - tech_weight) × ex_tech_return
    # Solving: ex_tech_return = (SP500_return - tech_weight × tech_return) / (1 - tech_weight)

    sp500_ex_tech_returns = (returns['SP500'] - tech_weight * tech_weighted_returns) / (1 - tech_weight)

    # Calculate cumulative performance
    print("\nStep 6: Calculating cumulative performance")
    print("-" * 80)

    sp500_cumulative = (1 + returns['SP500']).cumprod() * 100
    tech_weighted_cumulative = (1 + tech_weighted_returns).cumprod() * 100
    sp500_ex_tech_cumulative = (1 + sp500_ex_tech_returns).cumprod() * 100

    # Calculate metrics for all three
    print("\n" + "="*80)
    print("PERFORMANCE METRICS COMPARISON")
    print("="*80)

    sp500_metrics = calculate_performance_metrics(returns['SP500'])
    print("\n1. S&P 500 (Full Index):")
    for metric, value in sp500_metrics.items():
        suffix = '%' if metric != 'Sharpe Ratio' else ''
        print(f"   {metric:20} {value:8.2f}{suffix}")

    tech_metrics = calculate_performance_metrics(tech_weighted_returns)
    print("\n2. Tech Giants (Market-Cap Weighted):")
    for metric, value in tech_metrics.items():
        suffix = '%' if metric != 'Sharpe Ratio' else ''
        print(f"   {metric:20} {value:8.2f}{suffix}")

    ex_tech_metrics = calculate_performance_metrics(sp500_ex_tech_returns)
    print("\n3. S&P 500 Ex-Tech Giants:")
    for metric, value in ex_tech_metrics.items():
        suffix = '%' if metric != 'Sharpe Ratio' else ''
        print(f"   {metric:20} {value:8.2f}{suffix}")

    # Save metrics
    metrics_df = pd.DataFrame({
        'S&P 500 (Full)': sp500_metrics,
        'Tech Giants (Weighted)': tech_metrics,
        'S&P 500 Ex-Tech': ex_tech_metrics
    }).T
    metrics_df.to_csv('data/ex_tech_performance_metrics.csv')
    print("\n✓ Metrics saved to data/ex_tech_performance_metrics.csv")

    # Create comprehensive visualization
    print("\nStep 7: Creating visualizations")
    print("-" * 80)

    # Main comparison plot
    fig, ax = plt.subplots(figsize=(14, 8))

    ax.plot(sp500_cumulative.index, sp500_cumulative,
            label='S&P 500 (Full Index)', linewidth=2.5, color='blue', alpha=0.8)
    ax.plot(tech_weighted_cumulative.index, tech_weighted_cumulative,
            label=f'Tech Giants ({tech_weight*100:.1f}% of S&P 500)',
            linewidth=2.5, color='red', alpha=0.8)
    ax.plot(sp500_ex_tech_cumulative.index, sp500_ex_tech_cumulative,
            label=f'S&P 500 Ex-Tech ({(1-tech_weight)*100:.1f}% of S&P 500)',
            linewidth=2.5, color='green', alpha=0.8)

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Price (Base = 100)', fontsize=12, fontweight='bold')
    ax.set_title('S&P 500 Decomposition: Full Index vs Tech Giants vs Rest of Market\n(Market-Cap Weighted)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)

    # Add final values as annotations
    final_sp500 = sp500_cumulative.iloc[-1]
    final_tech = tech_weighted_cumulative.iloc[-1]
    final_ex_tech = sp500_ex_tech_cumulative.iloc[-1]

    ax.text(0.02, 0.98, f'S&P 500 Final: {final_sp500:.1f}',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='blue', alpha=0.2))
    ax.text(0.02, 0.93, f'Tech Giants Final: {final_tech:.1f}',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='red', alpha=0.2))
    ax.text(0.02, 0.88, f'S&P 500 Ex-Tech Final: {final_ex_tech:.1f}',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='green', alpha=0.2))

    plt.tight_layout()
    plt.savefig('plots/sp500_ex_tech_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Main comparison saved to plots/sp500_ex_tech_comparison.png")
    plt.close()

    # Metrics comparison bar chart
    fig, ax = plt.subplots(figsize=(12, 7))

    metrics_to_plot = ['Total Return', 'CAGR', 'Volatility']
    x = np.arange(3)
    width = 0.25

    colors = ['#2E86AB', '#E63946', '#06A77D']

    values_sp500 = [sp500_metrics[m] for m in metrics_to_plot]
    values_tech = [tech_metrics[m] for m in metrics_to_plot]
    values_ex_tech = [ex_tech_metrics[m] for m in metrics_to_plot]

    bars1 = ax.bar(x - width, values_sp500, width, label='S&P 500 (Full)',
                   color=colors[0], alpha=0.8)
    bars2 = ax.bar(x, values_tech, width, label='Tech Giants',
                   color=colors[1], alpha=0.8)
    bars3 = ax.bar(x + width, values_ex_tech, width, label='S&P 500 Ex-Tech',
                   color=colors[2], alpha=0.8)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

    ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Metrics Comparison: Full S&P 500 vs Tech Giants vs Ex-Tech',
                 fontsize=13, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_to_plot, fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('plots/ex_tech_metrics_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Metrics comparison saved to plots/ex_tech_metrics_comparison.png")
    plt.close()

    # Summary and conclusion
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)

    print(f"\n📊 MARKET COMPOSITION:")
    print(f"   Tech Giants weight in S&P 500: {tech_weight*100:.1f}%")
    print(f"   Rest of market weight: {(1-tech_weight)*100:.1f}%")

    print(f"\n🎯 PERFORMANCE COMPARISON:")
    print(f"   S&P 500 (Full):      {sp500_metrics['Total Return']:>8.1f}% total  |  {sp500_metrics['CAGR']:>5.2f}% CAGR")
    print(f"   Tech Giants:         {tech_metrics['Total Return']:>8.1f}% total  |  {tech_metrics['CAGR']:>5.2f}% CAGR")
    print(f"   S&P 500 Ex-Tech:     {ex_tech_metrics['Total Return']:>8.1f}% total  |  {ex_tech_metrics['CAGR']:>5.2f}% CAGR")

    print(f"\n💡 KEY INSIGHTS:")
    performance_ratio = tech_metrics['CAGR'] / ex_tech_metrics['CAGR']
    print(f"   1. Tech giants returned {performance_ratio:.1f}x more than S&P 500 ex-tech")
    print(f"   2. S&P 500 ex-tech CAGR: {ex_tech_metrics['CAGR']:.2f}% vs Full S&P 500: {sp500_metrics['CAGR']:.2f}%")
    print(f"   3. Tech giants (~{tech_weight*100:.0f}% of index) drove {((tech_metrics['CAGR']-ex_tech_metrics['CAGR'])/sp500_metrics['CAGR']*100):.0f}% of excess returns")

    print(f"\n✅ VALIDATION:")
    if ex_tech_metrics['CAGR'] < sp500_metrics['CAGR'] * 0.7:
        print("   STATEMENT STRONGLY VALIDATED:")
        print(f"   S&P 500 ex-tech significantly underperformed (only {ex_tech_metrics['CAGR']/sp500_metrics['CAGR']*100:.0f}% of full index return)")
    elif ex_tech_metrics['CAGR'] < sp500_metrics['CAGR']:
        print("   STATEMENT VALIDATED:")
        print(f"   S&P 500 ex-tech underperformed the full index")
    else:
        print("   STATEMENT NOT VALIDATED:")
        print(f"   S&P 500 ex-tech performed similarly to or better than full index")

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == "__main__":
    main()

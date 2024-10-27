import yfinance as yf
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import re

def calculate_fcf_ttm(stock):
    # Free Cash Flow TTM calculation
    cashflow_quarterly = stock.quarterly_cashflow
    try:
        # Retrieve the last 4 periods of Operating Cash Flow and Capital Expenditure
        operating_cash_flow = cashflow_quarterly.loc['Operating Cash Flow'].head(4)
        capital_expenditure = cashflow_quarterly.loc['Capital Expenditure'].head(4)

        # Calculate Free Cash Flow (TTM) by subtracting Capital Expenditure from Operating Cash Flow
        operating_cash_flow_ttm = operating_cash_flow.sum()
        capital_expenditure_ttm = capital_expenditure.sum()
        fcf_ttm = operating_cash_flow_ttm + capital_expenditure_ttm

        return fcf_ttm
    except Exception as e:
        return 'N/A'


def calculate_free_cash_flow_yield(stock, info):
    try:
        # Get Free Cash Flow TTM
        fcf_ttm = calculate_fcf_ttm(stock)

        # Get Market Capitalization from 'info'
        market_cap = info.get('marketCap', 'N/A')

        # Calculate Free Cash Flow Yield (FCF / Market Cap)
        fcf_yield = (fcf_ttm / market_cap) * 100 if market_cap != 'N/A' else 'N/A'

        return fcf_yield
    except Exception as e:
        return 'N/A'

def calculate_eps_growth(income_stmt):
    try:
        # Fetch the last 4 annual EPS values
        eps_data = income_stmt.loc['Basic EPS'].dropna().tail(4)


        # Calculate 4-year EPS growth rate if start and end values are valid
        if len(eps_data) == 4 and (eps_data.iloc[0] > 0) and (eps_data.iloc[-1] > 0):
            eps_start = eps_data.iloc[-1]
            eps_end = eps_data.iloc[0]
            eps_growth_percent = (((eps_end / eps_start) ** (1 / 4)) - 1) * 100
            return eps_growth_percent
        if len(eps_data) == 4 and (eps_data.iloc[0] < 0) and (eps_data.iloc[-1] < 0):
            eps_start = eps_data.iloc[-1]
            eps_end = eps_data.iloc[0]
            eps_growth_percent = ((((eps_end / eps_start) ** (1 / 4)) - 1) * 100) * -1
            return eps_growth_percent
        else:
            return 'N/A'
    except Exception as e:
        return 'N/A'


def calculate_fcf_ev(stock, info):
    try:
        # Check if the sector/industry indicates a bank or insurance company
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')

        # Skip EV calculation for traditional banks and insurance companies
        if sector == 'Financial Services' and ('Bank' in industry or 'Insurance' in industry):
            return 'N/A'  # Skip EV calculation for banks and insurance companies

        # Get Free Cash Flow TTM
        fcf_ttm = calculate_fcf_ttm(stock)

        # Get Enterprise Value directly from 'info'
        enterprise_value = info.get('enterpriseValue', 'N/A')

        # Calculate FCF/EV (Free Cash Flow / Enterprise Value)
        fcf_ev = (fcf_ttm / enterprise_value) * 100 if enterprise_value != 'N/A' else 'N/A'

        return fcf_ev
    except Exception as e:
        return 'N/A'

# Function to calculate ROIC (TTM)
def calculate_roic_ttm(stock):
    try:
        # Fetch the balance sheet data (last four quarters)
        balance_sheet = stock.quarterly_balance_sheet

        # Safely fill missing values and ensure numeric types
        with pd.option_context('future.no_silent_downcasting', True):
            total_equity = pd.to_numeric(balance_sheet.loc['Stockholders Equity'].iloc[0:4].fillna(0), errors='coerce') if 'Stockholders Equity' in balance_sheet.index else pd.Series([0, 0, 0, 0])
            long_term_debt = pd.to_numeric(balance_sheet.loc['Long Term Debt'].iloc[0:4].fillna(0), errors='coerce') if 'Long Term Debt' in balance_sheet.index else pd.Series([0, 0, 0, 0])
            short_term_debt = pd.to_numeric(balance_sheet.loc['Current Debt'].iloc[0:4].fillna(0), errors='coerce') if 'Current Debt' in balance_sheet.index else pd.Series([0, 0, 0, 0])
            long_term_lease_obligation = pd.to_numeric(balance_sheet.loc['Long Term Capital Lease Obligation'].iloc[0:4].fillna(0), errors='coerce') if 'Long Term Capital Lease Obligation' in balance_sheet.index else pd.Series([0, 0, 0, 0])
            short_term_lease_obligation = pd.to_numeric(balance_sheet.loc['Current Capital Lease Obligation'].iloc[0:4].fillna(0), errors='coerce') if 'Current Capital Lease Obligation' in balance_sheet.index else pd.Series([0, 0, 0, 0])

        # Fetch the income statement data (TTM Net Income by summing the last 4 quarters)
        income_statement = stock.quarterly_financials
        net_income_ttm = income_statement.loc['Net Income'].iloc[0:4].sum() if 'Net Income' in income_statement.index else 0

        # Calculate averages
        total_equity_avg = total_equity.mean()
        long_term_debt_avg = long_term_debt.mean()
        short_term_debt_avg = short_term_debt.mean()
        long_term_lease_obligation_avg = long_term_lease_obligation.mean()
        short_term_lease_obligation_avg = short_term_lease_obligation.mean()

        # Calculate invested capital as the average over the last four quarters
        invested_capital_avg = total_equity_avg + long_term_debt_avg + short_term_debt_avg + long_term_lease_obligation_avg + short_term_lease_obligation_avg

        # Ensure invested capital is not zero to avoid division by zero
        if invested_capital_avg != 0:
            roic_ttm = (net_income_ttm / invested_capital_avg) * 100
        else:
            roic_ttm = 'N/A'

        return roic_ttm

    except Exception as e:
        return 'N/A'

# Function to calculate ROA (Return on Average Assets)
def calculate_roaa_ttm(stock):
    try:
        income_statement_quarterly = stock.quarterly_financials
        balance_sheet_quarterly = stock.quarterly_balance_sheet

        net_income_ttm = income_statement_quarterly.loc['Net Income'].iloc[:4].sum()

        total_assets_fq = balance_sheet_quarterly.loc['Total Assets'].iloc[0]
        total_assets_fq_minus_4 = balance_sheet_quarterly.loc['Total Assets'].iloc[4]
        avg_total_assets_ttm = (total_assets_fq + total_assets_fq_minus_4) / 2

        if avg_total_assets_ttm != 0:
            roaa_ttm = (net_income_ttm / avg_total_assets_ttm) * 100
        else:
            roaa_ttm = 'N/A'

        return roaa_ttm
    except Exception as e:
        return 'N/A'


def calculate_revenue_growth(stock):
    try:
        # Fetch financials data (annual data)
        financials = stock.financials

        # Ensure that financials data exists and Total Revenue is available
        if 'Total Revenue' in financials.index:
            # Fetch the last 4 annual revenue values
            revenue_data = financials.loc['Total Revenue'].dropna().tail(4)  # Exclude NaNs and get last 4 periods

            # Check if the signs of the first and last revenue values are the same
            if len(revenue_data) == 4 and (revenue_data.iloc[0] > 0) and (revenue_data.iloc[-1] > 0):
                revenue_start = revenue_data.iloc[-1]  # Revenue from the earliest date
                revenue_end = revenue_data.iloc[0]  # Revenue from the latest date
                revenue_growth_percent = (((revenue_end / revenue_start) ** (1 / 4)) - 1) * 100  # CAGR formula
                return revenue_growth_percent
            if len(revenue_data) == 4 and (revenue_data.iloc[0] < 0) and (revenue_data.iloc[-1] < 0):
                revenue_start = revenue_data.iloc[-1]  # Revenue from the earliest date
                revenue_end = revenue_data.iloc[0]  # Revenue from the latest date
                revenue_growth_percent = ((((revenue_end / revenue_start) ** (1 / 4)) - 1) * 100 ) * -1 # CAGR formula
                return revenue_growth_percent
            else:
                return 'N/A'  # Return 'N/A' if signs are different
        else:
            return 'N/A'  # If 'Total Revenue' is not in the financial data
    except Exception as e:
        print(f"Error in Revenue Growth calculation: {e}")
        return 'N/A'


# Function to check if stock hit a new 52-week high in the past 4 weeks
def check_new_52_week_high(stock):
    # Fetch historical market data for the past 52 weeks
    historical_data = stock.history(period="1y", interval="1d")

    # Find the highest stock price in the last 52 weeks, rounded to two decimal places
    high_52_week = round(historical_data['High'].max(), 2)

    # Find the highest stock price in the last 4 weeks (most recent 20 trading days), rounded to two decimal places
    recent_high = round(historical_data['High'].tail(20).max(), 2)

    # Compare the recent high to the 52-week high
    if recent_high >= high_52_week:
        return True
    return False

# Function to safely convert values to numeric, handling errors and returning 'N/A' if not possible
def safe_numeric(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 'N/A'

def is_bank_or_insurance(info):
    """Check if the company is a bank or insurance company based on sector/industry."""
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')

    # Check for banks or insurance companies in the Financial Services sector
    return sector == 'Financial Services' and ('Bank' in industry or 'Insurance' in industry)

# Function to fetch financial data for a single stock ticker
def fetch_financial_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    income_stmt = stock.financials

    forward_eps_growth = safe_numeric(info.get('earningsGrowth', 'N/A')) * 100 if info.get('earningsGrowth') else 'N/A'

    # Check if the company is a bank or insurance company
    is_financial_institution = is_bank_or_insurance(info)

    # Fetch and process each metric, applying condition to set None if values are less than zero
    forward_pe = safe_numeric(info.get('forwardPE', 'N/A'))
    peg_ratio = safe_numeric(info.get('pegRatio', 'N/A'))
    ev_to_ebitda = safe_numeric(info.get('enterpriseToEbitda', 'N/A'))

    # Apply condition to set None if values are less than zero
    forward_pe = 'N/A' if isinstance(forward_pe, (int, float)) and forward_pe < 0 else forward_pe
    peg_ratio = 'N/A' if isinstance(peg_ratio, (int, float)) and peg_ratio < 0 else peg_ratio
    ev_to_ebitda = 'N/A' if isinstance(ev_to_ebitda, (int, float)) and ev_to_ebitda < 0 else ev_to_ebitda

    return {
        'Ticker': ticker,
        'Market Cap': info.get('marketCap', 'N/A'),
        'PE Ratio': safe_numeric(info.get('trailingPE', 'N/A')),
        'Forward P/E': forward_pe,
        'P/S Ratio': safe_numeric(info.get('priceToSalesTrailing12Months', 'N/A')),
        'P/B Ratio': safe_numeric(info.get('priceToBook', 'N/A')),
        'Dividend Yield (%)': safe_numeric(info.get('dividendYield', 'N/A')) * 100 if info.get('dividendYield') else 'N/A',
        'Current Ratio': 'N/A' if is_financial_institution else safe_numeric(info.get('currentRatio', 'N/A')),
        'Debt/Equity': 'N/A' if is_financial_institution else safe_numeric(info.get('debtToEquity', 'N/A')) / 100 if safe_numeric(info.get('debtToEquity', 'N/A')) != 'N/A' else 'N/A',
        'Revenue Growth 4Y (%)': calculate_revenue_growth(stock),
        'EPS Growth 4Y (%)': calculate_eps_growth(income_stmt),
        'Forward EPS Growth (%)': forward_eps_growth,
        'EPS': safe_numeric(info.get('trailingEps', 'N/A')),
        'PEG Ratio': peg_ratio,
        'ROE (%)': safe_numeric(info.get('returnOnEquity', 'N/A')) * 100 if info.get('returnOnEquity') else 'N/A',
        'ROA (%)': calculate_roaa_ttm(stock),
        'ROIC (%)': calculate_roic_ttm(stock),
        'Profit Margin (%)': safe_numeric(info.get('profitMargins', 'N/A')) * 100 if info.get('profitMargins') else 'N/A',
        'Gross Margin (%)': 'N/A' if is_financial_institution else safe_numeric(info.get('grossMargins', 'N/A')) * 100 if info.get('grossMargins') else 'N/A',
        'FCF Yield (%)': 'N/A' if is_financial_institution else calculate_free_cash_flow_yield(stock, info),
        'FCF/EV': 'N/A' if is_financial_institution else calculate_fcf_ev(stock, info),
        'EV/EBITDA': ev_to_ebitda,
        'Recent 52-Week High': check_new_52_week_high(stock),
        'Sector': info.get('sector', 'N/A'),
        'Industry': info.get('industry', 'N/A'),
    }

def clean_text(text):
    if isinstance(text, str):
        # Standardize and fix encoding issues
        text = text.replace('â€”', ' - ')
        text = text.replace('—', ' - ')

        # Special handling for REITs (ensure "REIT-" stays intact)
        text = text.replace("REIT-", "REIT - ")

        # Add a space before any uppercase letter following a lowercase (e.g., REITDiversified -> REIT - Diversified)
        text = re.sub(r'([a-z])([A-Z])', r'\1 - \2', text)

        return text.strip()  # Only strip strings
    return text  # Return the original value if it's not a string (e.g., float, NaN, etc.)

# Function to fetch financial data and save to CSV with multithreading and progress bar
def fetch_financial_data_and_save(ticker_df, output_csv, max_workers=10):
    ticker_list = ticker_df['Ticker'].tolist()
    data_list = []

    # Use ThreadPoolExecutor for multithreading
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks to the executor
        future_to_ticker = {executor.submit(fetch_financial_data, ticker): ticker for ticker in ticker_list}

        # Use tqdm to add a progress bar
        for future in tqdm(as_completed(future_to_ticker), total=len(ticker_list), desc="Fetching data"):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                # Clean up any problematic text/characters in the Industry field
                if 'Industry' in data:
                    data['Industry'] = clean_text(data['Industry'])

                data_list.append(data)
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")

    # Convert the list of data to a DataFrame and save it as CSV
    df = pd.DataFrame(data_list)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"Data saved to {output_csv}")

# Function to filter the saved data, format specific columns, and fill empty cells with "N/A"
def filter_saved_data(input_csv, filters):
    # Load the saved CSV file
    df = pd.read_csv(input_csv, encoding='utf-8')

    # Clean text fields in case there are any encoding issues
    df['Sector'] = df['Sector'].apply(clean_text)

    # Apply the filters passed as an argument
    for column, value in filters.items():
        if column in df.columns:
            if isinstance(value, tuple):  # For numeric filters with ranges
                min_val, max_val = value
                if min_val is not None:
                    df = df[df[column] >= min_val]
                if max_val is not None:
                    df = df[df[column] <= max_val]
            elif isinstance(value, bool):  # For boolean filters
                df = df[df[column] == value]
            elif isinstance(value, str):  # For categorical filters (string)
                df = df[df[column].str.contains(value, case=False, na=False)]

    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Replace all NaN values with "N/A"
    df = df.fillna("N/A")

    return df
########################################################################################################################

# Define the filters to pass dynamically
"""filters = {
    'Market Cap': (None, None),  # Filter for Market Cap: (min, max). Use None for no limits.
    'PE Ratio': (None, None),  # Filter for Price-to-Earnings ratio: (min, max).
    'Forward P/E': (None, None),  # Filter for Forward P/E ratio: (min, max).
    'P/S Ratio': (None, None),  # Filter for Price-to-Sales ratio: (min, max).
    'P/B Ratio': (None, None),  # Filter for Price-to-Book ratio: (min, max).
    'Dividend Yield (%)': (None, None),  # Filter for Dividend Yield: (min, max) in percentage.
    'Current Ratio': (None, None),  # Filter for Current Ratio: (min, max).
    'Debt/Equity': (None, None),  # Filter for Debt-to-Equity ratio: (min, max).
    'Revenue Growth 4Y (%)': (None, None),  # Filter for Revenue Growth over the last 4 years: (min, max) in percentage.
    'EPS Growth 4Y (%)': (None, None),  # Filter for Earnings Per Share (EPS) Growth over the last 4 years: (min, max) in percentage.
    'Forward EPS Growth (%)': (None, None),  # Filter for expected Forward EPS Growth: (min, max) in percentage.
    'EPS': (None, None),  # Filter for Earnings Per Share (EPS) over the trailing twelve months: (min, max).
    'PEG Ratio': (None, None),  # Filter for Price/Earnings-to-Growth ratio: (min, max).
    'ROE (%)': (None, None),  # Filter for Return on Equity: (min, max) in percentage.
    'ROA (%)': (None, None),  # Filter for Return on Assets: (min, max) in percentage.
    'ROIC (%)': (None, None),  # Filter for Return on Invested Capital: (min, max) in percentage.
    'Profit Margin (%)': (None, None),  # Filter for Profit Margin: (min, max) in percentage.
    'Gross Margin (%)': (None, None),  # Filter for Gross Margin: (min, max) in percentage.
    'FCF Yield (%)': (None, None),  # Filter for Free Cash Flow Yield: (min, max) in percentage.
    'FCF/EV': (None, None), # Filter for FCF/EVB: (min, max).
    'EV/EBITDA': (None, None),  # Filter for Enterprise Value/EBITDA ratio: (min, max).
    'Recent 52-Week High': None,  # Filter for stocks that hit a new 52-week high recently. Set to True for filtering.
    'Sector': None,  # Filter by sector, e.g., 'Technology', 'Healthcare'. Set to a string for filtering.
    'Industry': None #Filter by industry e.g., 'Software - Application', 'Grocery Stores'. Set to a string for filtering.
}"""

#tickers_df = pd.read_csv("Stock_Universe.csv")
#fetch_financial_data_and_save(tickers_df, 'financial_metrics.csv')


# Call the function with the provided filters
#filter_saved_data("financial_metrics.csv", filters)

########################################################################################################################

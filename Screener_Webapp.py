from flask import Flask, render_template, jsonify, request, current_app
import download_universe
import Stock_Screener
import threading
import webbrowser
import time
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import numpy as np
import os
import re
from scipy.stats import iqr

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('screener.html')

# Preload ChromeDriver at the start of the Flask app
#def preload_chromedriver():
#    print("Preloading ChromeDriver...")
#    service = Service(ChromeDriverManager().install())
#    print("ChromeDriver preloaded.")

#preload_chromedriver()  # This ensures the ChromeDriver is ready when the scheduled task runs

def scrape_and_save():
    # Scrape all tickers with progress updates
    df = download_universe.scrape_all_tickers()

    # Save to CSV
    output_path = os.path.join(os.getcwd(), "Stock_Universe.csv")
    df.to_csv(output_path, index=False)


def fetch_and_save_metrics():
    # Define your tickers here or fetch them dynamically
    tickers_df = pd.read_csv("Stock_Universe.csv")  # Tickers
    output_csv = 'financial_metrics.csv'

    # Set a default value for max_workers
    max_workers = 10

    # Call the function to fetch financial data and save it
    Stock_Screener.fetch_financial_data_and_save(tickers_df, output_csv, max_workers)
    print(f"Financial metrics saved to {output_csv}")


# Function to run all tasks daily in sequence
def run_daily_tasks():
    try:
        scrape_and_save()            # Step 1: Scrape stock tickers
        print("All files have been scraped and saved.")
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
    try:
        fetch_and_save_metrics()     # Step 2: Fetch financial metrics
        print("All financial metrics have been saved.")
    except Exception as e:
        print(f"Error during financial metrics fetching: {str(e)}")
    try:
        with app.app_context():
            save_highlighted_data()  # Now calls with the app context
            print("All tasks completed for the day.")
    except Exception as e:
        print(f"Error during calculating industry averages: {str(e)}")

# Initialize the APScheduler
scheduler = BackgroundScheduler()

# Schedule the tasks to run daily at 4:30 PM (you can adjust the time)
scheduler.add_job(run_daily_tasks, CronTrigger(hour=20, minute=30))  # Runs at 4:30 PM every day

# Start the scheduler
scheduler.start()

# Flask route to check if the tasks are running
@app.route('/check-status', methods=['GET'])
def check_status():
    return jsonify({'status': 'Tasks are running'})

@app.route('/get_initial_data', methods=['GET'])
def get_initial_data():
    try:

        # Load the financial data and highlighted data
        financial_df = pd.read_csv('financial_metrics.csv')
        highlighted_df = pd.read_csv('highlighted_sector_averages.csv')

        # Merge on 'Ticker' (or another appropriate column)
        merged_df = pd.merge(financial_df, highlighted_df, on='Ticker', how='left')

        # Replace 'N/A', inf, and -inf with np.nan
        merged_df.replace([np.inf, -np.inf, 'N/A'], np.nan, inplace=True)

        # Explicitly call infer_objects to avoid future warnings
        merged_df = merged_df.infer_objects()

        # Replace all NaN values in the processed DataFrame with "N/A"
        merged_df = merged_df.fillna("N/A")

        # Return JSON response
        return jsonify(merged_df.to_dict(orient="records"))

    except Exception as e:
        print(f"Error in get_initial_data: {str(e)}")
        return jsonify({'error': 'An error occurred while processing data.'}), 500

@app.route('/get_industries', methods=['GET'])
def get_industries():
    # Load the dataset
    df = pd.read_csv("financial_metrics.csv")

    # Get unique non-null industries
    industries = df['Industry'].dropna().unique().tolist()

    # Return the unique industries as JSON
    return jsonify(industries)

@app.route('/get_sectors', methods=['GET'])
def get_sectors():
    # Load the CSV file (ensure the path to your file is correct)
    df = pd.read_csv("financial_metrics.csv")

    # Extract unique sectors
    sectors = df['Sector'].dropna().unique().tolist()

    # Return the sectors as a JSON response
    return jsonify(sectors)


# Function to clean up any problematic characters and ensure formatting consistency
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

@app.route('/save_highlighted_data', methods=['GET', 'POST'])
def save_highlighted_data():
    try:
        # Load the data from 'financial_metrics.csv' for processing
        df = pd.read_csv('financial_metrics.csv')

        # Calculate highlights based on sector averages and save to CSV
        highlighted_df = calculate_and_highlight_sector_averages(df)
        highlighted_df.to_csv('highlighted_sector_averages.csv', index=False)

        print('Highlighted data saved successfully.')
        return jsonify({'status': 'success', 'message': 'Highlighted data saved to CSV.'}), 200

    except Exception as e:
        print(f"Error in save_highlighted_data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def calculate_and_highlight_sector_averages(df):
    # Clean the Industry column
    df['Sector'] = df['Sector'].apply(clean_text)
    df = df.dropna(subset=['Sector']).copy()
    df.replace(['N/A', np.inf, -np.inf], np.nan, inplace=True)
    columns_to_exclude = ['Ticker', 'Market Cap', 'Recent 52-Week High', 'Sector', 'Industry']
    numeric_columns = [col for col in df.columns if col not in columns_to_exclude]

    # Calculate sector averages and apply IQR filtering
    sector_avg_dict = {}
    for sector, group in df.groupby('Sector'):
        sector_avg_dict[sector] = {}
        for col in numeric_columns:
            valid_data = group[col].dropna()
            if len(valid_data) > 0:
                q1 = valid_data.quantile(0.25)
                q3 = valid_data.quantile(0.75)
                lower_bound = q1 - 1.5 * iqr(valid_data)
                upper_bound = q3 + 1.5 * iqr(valid_data)
                filtered_data = valid_data[(valid_data >= lower_bound) & (valid_data <= upper_bound)]
                sector_avg_dict[sector][col] = filtered_data.mean() if len(filtered_data) > 0 else np.nan
            else:
                sector_avg_dict[sector][col] = np.nan

    # Convert to DataFrame for easier merging and highlighting
    sector_avg_df = pd.DataFrame.from_dict(sector_avg_dict, orient='index')
    sector_avg_df.to_csv('sector_averages.csv', index=True)  # Save sector averages

    # Convert to DataFrame for easier merging and highlighting
    sector_avg_df = pd.DataFrame.from_dict(sector_avg_dict, orient='index')
    sector_avg_df.to_csv('sector_averages.csv', index=True)  # Save sector averages

    # Copy the original DataFrame to preserve data integrity
    highlighted_df = df.copy()

    # Add highlighting based on sector average comparisons
    for col in numeric_columns:
        def highlight_comparison(row):
            sector_avg = sector_avg_df.at[row['Sector'], col] if row['Sector'] in sector_avg_df.index else None
            if pd.isnull(sector_avg) or pd.isnull(row[col]):
                return "within"

            # Determine the comparison thresholds based on whether the sector average is positive or negative
            if sector_avg > 0:
                above_threshold = sector_avg * 1.35
                below_threshold = sector_avg * 0.65
            else:
                above_threshold = sector_avg * 0.65  # A smaller negative number (closer to zero) is "above" the average
                below_threshold = sector_avg * 1.35  # A larger negative number (further from zero) is "below" the average

            # Apply the highlighting logic
            if row[col] > above_threshold:
                return "above"
            elif row[col] < below_threshold:
                return "below"
            else:
                return "within"
        highlighted_df[f"{col}_highlight"] = highlighted_df.apply(highlight_comparison, axis=1)

    # Save only 'Ticker' and highlighted columns to CSV
    highlight_columns = [col for col in highlighted_df.columns if '_highlight' in col]
    final_df = highlighted_df[['Ticker'] + highlight_columns]
    final_df.to_csv('highlighted_sector_averages.csv', index=False)

    return final_df

@app.route('/filter_data', methods=['POST'])
def filter_data():
    # Get the incoming JSON data from the request (filters sent from the frontend)
    received_filters = request.json

    # Convert lists to tuples in the filters (if necessary)
    filters = {}
    for key, value in received_filters.items():
        if isinstance(value, list):
            filters[key] = tuple(value)  # Convert list to tuple
        else:
            filters[key] = value  # Keep as is for non-list items like booleans or strings

    # Apply the filters using the filter_saved_data function
    filtered_df = Stock_Screener.filter_saved_data("financial_metrics.csv", filters)

    # Load highlighted data
    highlighted_df = pd.read_csv('highlighted_sector_averages.csv')

    # Merge on 'Ticker' (or another appropriate column)
    merged_df = pd.merge(filtered_df, highlighted_df, on='Ticker', how='left')

    # Replace all NaN values in the processed DataFrame with "N/A"
    merged_df = merged_df.fillna("N/A")

    # Convert the filtered DataFrame to JSON and return it
    data = merged_df.to_dict(orient='records')

    return jsonify(data)

def open_browser():
    """Wait for the server to start, then open the default web browser."""
    time.sleep(1)  # Small delay to ensure the server has started
    webbrowser.open('http://127.0.0.1:5000/')


if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=app.run, kwargs={'debug': False, 'use_reloader': False, 'host': '0.0.0.0', 'port': 3000})
    flask_thread.start()

    # Automatically open the web browser after a slight delay (optional)
    # Comment this out if running on a headless environment like Coolify
    # open_browser()

    flask_thread.join()  # Wait for the Flask thread to complete
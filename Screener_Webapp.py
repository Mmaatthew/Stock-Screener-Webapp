from flask import Flask, render_template, jsonify, request
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
        print("All tasks completed for the day.")
    except Exception as e:
        print(f"Error during financial metrics fetching: {str(e)}")

# Initialize the APScheduler
scheduler = BackgroundScheduler()

# Schedule the tasks to run daily at 4:30 PM (you can adjust the time)
scheduler.add_job(run_daily_tasks, CronTrigger(hour=20, minute=35))  # Runs at 4:30 PM every day

# Start the scheduler
scheduler.start()

# Flask route to check if the tasks are running
@app.route('/check-status', methods=['GET'])
def check_status():
    return jsonify({'status': 'Tasks are running'})

@app.route('/get_initial_data', methods=['GET'])
def get_initial_data():
    # Load the dataset (adjust the path to your CSV file)
    df = pd.read_csv("financial_metrics.csv")

    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Replace all NaN values with "N/A"
    df = df.fillna("N/A")

    # Convert the DataFrame to a list of dictionaries
    data = df.to_dict(orient='records')

    # Return the data directly as a JSON response
    return jsonify(data)

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

    # Convert the filtered DataFrame to JSON and return it
    data = filtered_df.to_dict(orient='records')

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
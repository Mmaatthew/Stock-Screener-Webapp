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
import json



app = Flask(__name__)

@app.route('/')
def index():
    return render_template('screener.html')

# Preload ChromeDriver at the start of the Flask app
def preload_chromedriver():
    print("Preloading ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    print("ChromeDriver preloaded.")

preload_chromedriver()  # This ensures the ChromeDriver is ready when the scheduled task runs

def scrape_and_save():
    # Scrape all tickers with progress updates
    df = download_universe.scrape_all_tickers()

    # Save to CSV
    df.to_csv("Stock_Universe.csv", index=False)


def fetch_and_save_metrics():
    # Define your tickers here or fetch them dynamically
    tickers_df = pd.read_csv("Stock_Universe.csv")  # Tickers
    output_csv = 'financial_metrics.csv'

    # Set a default value for max_workers
    max_workers = 10

    # Call the function to fetch financial data and save it
    Stock_Screener.fetch_financial_data_and_save(tickers_df, output_csv, max_workers,)


# Function to run all tasks daily in sequence
def run_daily_tasks():
    scrape_and_save()            # Step 1: Scrape stock tickers
    fetch_and_save_metrics()     # Step 2: Fetch financial metrics
    print("All tasks completed for the day.")

# Initialize the APScheduler
scheduler = BackgroundScheduler()

# Schedule the tasks to run daily at 4:30 PM (you can adjust the time)
scheduler.add_job(run_daily_tasks, CronTrigger(hour=16, minute=30))  # Runs at 4:30 PM every day

# Start the scheduler
scheduler.start()


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


@app.route('/filter_data', methods=['POST'])
def filter_data():
    # Default filters dictionary

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
    # Assuming df is your DataFrame
    filtered_df.to_csv('debug_output.csv', index=False)
    # Convert the filtered DataFrame to JSON and return it
    data = filtered_df.to_dict(orient='records')

    return jsonify(data)


def open_browser():
    """Wait for the server to start, then open the default web browser."""
    time.sleep(1)  # Small delay to ensure the server has started
    webbrowser.open('http://127.0.0.1:5000/')


if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=app.run, kwargs={'debug': False, 'use_reloader': False})
    flask_thread.start()

    # Automatically open the web browser after a slight delay
    open_browser()

    flask_thread.join()  # Wait for the Flask thread to complete
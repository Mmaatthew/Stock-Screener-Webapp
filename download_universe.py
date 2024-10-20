import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from selenium.common.exceptions import NoSuchElementException
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm  # Progress bar

def get_chrome_driver():
    """
    Installs ChromeDriver and returns a WebDriver instance.
    This ensures that Chrome is run in headless mode with proper options for Linux environments.
    """
    try:
        # Install ChromeDriver
        driver_path = ChromeDriverManager().install()

        # Set up the Chrome WebDriver service
        service = Service(driver_path)

        # Set up Chrome options for headless mode and other performance improvements
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")  # Headless mode for running without GUI
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource issues

        # Return the WebDriver instance
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Error while setting up ChromeDriver: {str(e)}")
        return None

def close_popup(driver):
    try:
        # Locate the close button with the class 'w-6 h-6 text-icon'
        close_button = driver.find_element(By.CSS_SELECTOR, '.w-6.h-6.text-icon')
        close_button.click()
    except NoSuchElementException:
        pass

def scrape_tickers(url, suffix):
    # Set Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Set up Selenium WebDriver with headless Chrome
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Navigate to the page
    driver.get(url)

    # Close any popups if they appear
    close_popup(driver)

    # Initialize an empty list to hold all tickers
    tickers = []

    # Loop through pages and extract data
    while True:
        # Close popup if it appears on subsequent pages
        close_popup(driver)

        # Find all stock tickers on the current page
        tickers_elements = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr td a')

        # Extract text (ticker symbols)
        tickers.extend([ticker.text for ticker in tickers_elements])

        try:
            # Find the "Next" button using the class name
            next_button = driver.find_element(By.CSS_SELECTOR, '.controls-btn.xs\\:pl-1.xs\\:pr-1\\.5.bp\\:text-sm.sm\\:pl-3.sm\\:pr-1')

            # Check if the button is disabled or hidden (indicating the last page)
            if not next_button.is_enabled() or 'disabled' in next_button.get_attribute('class'):
                break  # Exit loop if the "Next" button is not clickable

            # Click the "Next" button
            next_button.click()

            # Add a delay to let the page load
            time.sleep(1)
        except:
            # Break the loop if the "Next" button is not found (i.e., last page)
            break

    # Create a Pandas DataFrame
    df = pd.DataFrame(tickers, columns=['Ticker'])

    # Close the browser
    driver.quit()

    # Format ticker symbols and return
    df['Ticker'] = df['Ticker'].str.replace('.', '-', regex=False) + suffix
    return df

def scrape_exchange(exchange):
    url, suffix = exchange
    return scrape_tickers(url, suffix)

def scrape_all_tickers():
    # Define the URLs and suffixes
    exchanges = [
        ('https://stockanalysis.com/list/toronto-stock-exchange/', '.TO'),
        ('https://stockanalysis.com/list/tsx-venture-exchange/', '.V'),
        ('https://stockanalysis.com/list/nasdaq-stocks/', ''),
        ('https://stockanalysis.com/list/nyse-stocks/', '')
    ]

    # Use ProcessPoolExecutor for parallel scraping with separate processes
    with ProcessPoolExecutor() as executor:
        # Submit tasks to scrape all URLs concurrently with progress bar
        results = list(tqdm(executor.map(scrape_exchange, exchanges), total=len(exchanges), desc="Scraping Exchanges"))

    # Concatenate all DataFrames
    return pd.concat(results, ignore_index=True)

if __name__ == '__main__':
    # Example usage
    df = scrape_all_tickers()

    # Save the DataFrame to CSV
    df.to_csv("Stock_Universe.csv", index=False)

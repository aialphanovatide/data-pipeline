from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Ensure the script directory is included in Python's path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import custom modules from the project structure
from dags.functions.general_functions.get_delete_files import get_all_files, delete_files
from dags.functions.coingecko_vitalik_google_news_defillama.webscraper_url import WebScraper
from dags.functions.general_functions.upload_files import upload_preprocessed_files_to_vector_store
from dags.functions.coingecko_vitalik_google_news_defillama.webscraper_coingecko import process_multiple_coins
from dags.functions.coingecko_vitalik_google_news_defillama.vitalik_news_extraction import execute_news_extraction_pipeline
from dags.functions.coingecko_vitalik_google_news_defillama.google_news_extraction import process_news_from_directory
from dags.functions.coingecko_vitalik_google_news_defillama.webscraper_defillama import save_combined_data_to_file

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',  # Owner of the DAG
    'depends_on_past': False,  # Does not depend on previous DAG runs
    'email_on_failure': False,  # Disable email notifications on failure
    'email_on_retry': False,  # Disable email notifications on retry
    'retries': 1,  # Number of retries in case of failure
    'retry_delay': timedelta(minutes=5),  # Time to wait between retries
}

# Create the DAG
with DAG(
    'coingecko_vitalik_google_news_defillama_dag',
    default_args=default_args,
    description='DAG to run web scraping, process and upload files',  # Description of the DAG
    schedule_interval=timedelta(days=1),  # Schedule interval (daily)
    start_date=datetime(2024, 9, 11),  # Start date for the DAG
    catchup=False,  # Do not run past DAG instances
) as dag:

    # Define the function for web scraping and preprocessing CoinGecko and DefiLlama data
    def webscrapping_and_preprocessing_coingecko_defillama():
        """
        Scrapes and preprocesses data from CoinGecko and DefiLlama for a list of specified coins.
        It runs the CoinGecko preprocessing pipeline and combines it with DefiLlama data.
        """
        coins = [
            "bitcoin", "ethereum", "hack", "Lido-dao", "rocket-pool", "frax-share", "cosmos", "polkadot",
            "quant-network", "cardano", "solana", "avalanche-2", "near", "fantom", "kaspa", "matic-network",
            "arbitrum", "optimism-bridge", "chainlink-ccip", "api3", "band-protocol", "stellar", "algorand", "ripple",
            "dydx", "velodrome-finance", "gmx", "uniswap", "sushi", "pancakeswap-token", "aave", "pendle",
            "1inch", "ocean-protocol", "Fetch-ai", "Render-token"
        ]
        preprocessed_dir = '/opt/airflow/dags/files/preprocessed/'  # Directory where web scraping output is stored
        process_multiple_coins(coins, preprocessed_dir)  # Run the CoinGecko preprocessing function

        preprocessed_dir_defillama = '/opt/airflow/dags/files/preprocessed/all_coins_defillama.txt'  # Directory to save DefiLlama data
        save_combined_data_to_file(preprocessed_dir_defillama)  # Run the DefiLlama data extraction function

    # Task to run the CoinGecko and DefiLlama preprocessing
    run_webscrapping_preprocessing_coingecko_defillama = PythonOperator(
        task_id='run_webscrapping_preprocessing_coingecko_defillama',
        python_callable=webscrapping_and_preprocessing_coingecko_defillama,  # Python function to be executed
    )

    # Define the function to initialize and run the web scraper for Vitalik's website
    def run_webscraper_vitalik():
        """
        Initializes and runs the web scraper on Vitalik's website and several news URLs.
        The scraper is configured to save the output in a text format.
        """
        url_1 = "https://vitalik.eth.limo/"  # Main Vitalik's website URL
        scraper = WebScraper(url_1, verbose=True, save_to_file=True, save_format='txt')  # Enable verbose mode for debugging
        scraper.scrape('vitalik_url1')  # Run the web scraper

    # Task to execute the web scraper for Vitalik's website
    scrape_task_url_vitalik = PythonOperator(
        task_id='run_webscraper_url_vitalik',
        python_callable=run_webscraper_vitalik,  # Python function to be executed
    )

    # Define the function to preprocess the scraped JSON files for Vitalik's website
    def run_preprocess_vitalik():
        """
        Processes the most recent JSON file generated by the web scraper for Vitalik's content.
        It transforms the JSON content into a structured CSV format and saves it in the preprocessed directory.
        """
        webscraping_dir = '/opt/airflow/dags/files/webscraper/'  # Directory where web scraping output is stored
        preprocessed_dir = '/opt/airflow/dags/files/preprocessed/'  # Directory to save preprocessed output
        #local_dir = '/opt/airflow/files/'
        execute_news_extraction_pipeline(webscraping_dir, preprocessed_dir)  # Run the extraction pipeline
        get_all_files(webscraping_dir)  # Retrieve all files in the directory
        delete_files(webscraping_dir)  # Delete processed files to clean up

    # Task to preprocess Vitalik's scraped JSON files
    run_preprocess_url_vitalik = PythonOperator(
        task_id='run_preprocess_url_vitalik',
        python_callable=run_preprocess_vitalik,  # Python function to be executed
    )

    # Define the function to run the Google News web scraper
    def run_webscraper_url_google_news():
        """
        Initializes and runs the web scraper on multiple Google News URLs.
        The scraper is set to save the output in text format for later processing.
        """
        url_2 = "https://news.google.com/rss/search?q=crypto+when:1d&hl=en-US&gl=US&ceid=US:en"
        url_4 = "https://news.google.com/rss/search?q=bitcoin+btc+%22bitcoin+btc%22+when:1d+-buy+-tradingview+-msn+-medium+-yahoo&hl=en-US&gl=US&ceid=US:en"
      
        # Scrape each Google News URL
        scraper = WebScraper(url_2, verbose=True, save_to_file=True, save_format='txt')
        scraper.scrape('news_url2')
        scraper = WebScraper(url_4, verbose=True, save_to_file=True, save_format='txt')
        scraper.scrape('news_url4')
    
    # Task to execute the web scraper for Google News
    run_webscraper_url_google_news_rss = PythonOperator(
        task_id='run_webscraper_url_google_news',
        python_callable=run_webscraper_url_google_news,  # Python function to be executed
    )

    # Define the function to preprocess Google News scraped JSON files
    def run_preprocess_url_google_news():
        """
        Processes the most recent JSON file generated by the web scraper for Google News.
        It transforms the JSON content into a structured CSV format and saves it in the preprocessed directory.
        """
        webscraping_dir = '/opt/airflow/dags/files/webscraper/'  # Directory where web scraping output is stored
        preprocessed_dir = '/opt/airflow/dags/files/preprocessed/consolidated_google_news.txt'  # Directory to save preprocessed output
        #local_dir = '/opt/airflow/files/consolidated_google_news.txt'
        process_news_from_directory(webscraping_dir, preprocessed_dir)  # Process Google News data
        get_all_files(webscraping_dir)  # Retrieve all files in the directory
        delete_files(webscraping_dir)  # Clean up processed files

    # Task to preprocess Google News scraped files
    run_preprocess_url_google_news_rss = PythonOperator(
        task_id='run_preprocess_url_google_news',
        python_callable=run_preprocess_url_google_news,  # Python function to be executed
    )

    # Define the function to upload preprocessed files to the vector store
    def upload_preprocessed_files():
        """
        Uploads the preprocessed files (in CSV format) to the vector store.
        The files to be uploaded are located in the preprocessed directory.
        """
        upload_preprocessed_files_to_vector_store()  # Call the function to upload files

    # Task to upload files to the vector store
    upload_files_task = PythonOperator(
        task_id='upload_preprocessed_files',
        python_callable=upload_preprocessed_files,  # Python function to be executed
    )

    # Task dependencies: run web scraper first, then preprocessing, and finally upload
    run_webscrapping_preprocessing_coingecko_defillama >> scrape_task_url_vitalik >> run_preprocess_url_vitalik >> run_webscraper_url_google_news_rss >> run_preprocess_url_google_news_rss >> upload_files_task

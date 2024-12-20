from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from pytz import timezone

# Import necessary functions from external scripts for handling Monday.com board operations
from functions.top_20_boards.top_20_boards import get_board_items
from functions.top_20_boards.top_20_boards import save_board_items_to_json
from functions.top_20_boards.top_20_boards import load_board_data
from functions.top_20_boards.top_20_boards import save_to_json
from functions.top_20_boards.top_20_boards import update_monday_boards

# Define the U.K. time zone for consistent scheduling
uk_tz = timezone('Europe/London')

# Define default arguments for the DAG with standard Airflow configurations
default_args = {
    'owner': 'airflow',  # Specifies who owns/maintains this DAG
    'depends_on_past': False,  # Each run is independent of previous runs
    'email_on_failure': False,  # Disables email notifications on task failure
    'email_on_retry': False,  # Disables email notifications on task retry
    'retries': 1,  # Attempts to retry failed task once
    'retry_delay': timedelta(minutes=5),  # Waits 5 minutes before retry attempt
}

with DAG(
    'top_20_boards',  # Unique identifier for this DAG
    default_args=default_args,
    description='DAG for processing and updating top 20 performing coins',  
    schedule_interval="0 14 * * *",  # Executes at 14:00 (11:00 PM Argentina time)
    start_date=datetime(2024, 11, 29, tzinfo=uk_tz),  # Initial execution date in UK time
    catchup=False  # Prevents backfilling of missed runs
) as dag:

    def top_20_boards_py():
        CEX_MASTER = 1652251054
        DEX_MASTER = 1678221568
    
        # Retrieve and process data from Monday.com
        board_items = get_board_items(board_ids=[DEX_MASTER, CEX_MASTER])
        if board_items:
            save_board_items_to_json(board_items)
        else:
            print("Could not retrieve data from the board.")
            return

        # Load data and process for filtering
        board_data = load_board_data()

        # Filter for best and worst coins
        bestcoins = [
            coin for coin in board_data 
            if coin.get('ROI', 0) > 50 and coin.get('Valuation Price', None) is not None
        ]

        worstcoins = [
            coin for coin in board_data 
            if coin.get('ROI', 0) < -90 and coin.get('Valuation Price', None) is not None
        ]

        # Save results to respective JSON files
        save_to_json(bestcoins, "best.json")
        save_to_json(worstcoins, "worst.json")
        print("Results saved in best.json and worst.json")

        # Update Monday.com boards
        update_monday_boards()
    
    # Create the task that will execute our processing function
    top_20_boards = PythonOperator(
        task_id='top_20_boards',  # Unique identifier for this task
        python_callable=top_20_boards_py,  # Points to our processing function
        dag=dag  # Associates this task with our DAG
    )

    # Define task flow (single task, so no dependencies needed)
    top_20_boards
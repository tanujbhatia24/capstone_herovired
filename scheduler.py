import schedule
import time
from fetch_data import pull_all_data  # This should collect and store data

schedule.every().day.at("01:00").do(pull_all_data)

while True:
    schedule.run_pending()
    time.sleep(60)

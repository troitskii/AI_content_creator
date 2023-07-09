from __future__ import print_function
import schedule
import time
import os
from datetime import datetime


def run_script_telega():
    script_path = 'main.py'
    os.system(f'C:\\Users\\Administrator\\Desktop\\chatgpt_telega\\chatgpt_telega\\.venv\\Scripts\\python {script_path}')
    print(f'Script executed at {datetime.now()}')


def run_script_podcast():
    script_path = 'release_podcast.py'
    os.system(f'C:\\Users\\Administrator\\Desktop\\chatgpt_telega\\chatgpt_telega\\.venv\\Scripts\\python {script_path}')
    print(f'Script executed at {datetime.now()}')


# Schedule the task
daily_time_telega = "10:41"
daily_time_podcast = "19:31"
schedule.every().day.at(daily_time_telega).do(run_script_telega)
schedule.every().day.at(daily_time_podcast).do(run_script_podcast)


# Keep the script running indefinitely to check for scheduled tasks
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every 60 seconds
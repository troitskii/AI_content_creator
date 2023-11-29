from __future__ import print_function
import schedule
import time
import os
from datetime import datetime


def run_script_telega():
    script_path = 'tg_release.py'
    os.system(f'C:\\Users\\Administrator\\PycharmProjects\\AI_content_creator\\venv\\Scripts\\python {script_path}')
    print(f'Script executed at {datetime.now()}')


def run_script_podcast():
    script_path = 'podcast_release.py'
    os.system(f'C:\\Users\\Administrator\\PycharmProjects\\AI_content_creator\\venv\\Scripts\\python {script_path}')
    print(f'Script executed at {datetime.now()}')


def run_script_telegpt():
    script_path = 'telegpt_release.py'
    os.system(f'C:\\Users\\Administrator\\PycharmProjects\\AI_content_creator\\venv\\Scripts\\python {script_path}')
    print(f'Script executed at {datetime.now()}')


# Schedule the task
daily_time_telega = "07:41"
daily_time_podcast = "18:39"
daily_time_telegpt = "14:11"
schedule.every().day.at(daily_time_telega).do(run_script_telega)
schedule.every().day.at(daily_time_podcast).do(run_script_podcast)
schedule.every().day.at(daily_time_telegpt).do(run_script_telegpt)

# Keep the script running indefinitely to check for scheduled tasks
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every 60 seconds
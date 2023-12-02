from __future__ import print_function
from openai import OpenAI
import pandas as pd
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import csv
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import date


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)

Google_Sheets_ID = data['Google_Sheets_SAMPLE_SPREADSHEET_ID']
TGstats_key = data['TGstats_key']
openai_key = data['openai_key']
playhtauth_key = data['playhtauth_key']
playht_user_id = data['playht_user_id']
buzz_token = data['buzz_token']
telegpt_token = data['telegpt_token']
telegpt_bot = data['telegpt_bot']

client = OpenAI(api_key = openai_key)

myHeaders = {

    'Authorization':telegpt_token,

}

def get_config(list_name):
    # Define Google Sheets API service account file and required scopes
    SERVICE_ACCOUNT_FILE = 'googleapi.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    # Create credentials using the service account file and the required scopes
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # Define the ID of the target Google Sheet
    SAMPLE_SPREADSHEET_ID = Google_Sheets_ID

    # Build the Sheets API service using the created credentials
    service = build('sheets', 'v4', credentials=creds)

    # Access the spreadsheet and get the values from the specified range
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=list_name).execute()

    # Extract the values from the result
    values = result.get('values', [])

    # Convert the values into a pandas DataFrame and return it
    df = pd.DataFrame(values[1:], columns=values[0])
    return df


def working_count_tg():
    config_telega = get_config('all_done')

    working_channels_count = len(config_telega[config_telega['work'] == '1'])
    current_date = datetime.now().strftime("%Y-%m-%d")
    data_to_append = [current_date, working_channels_count]
    filename = 'tg_working_channels_daily.csv'

    # Check if the file exists, if not, create it and write the header
    try:
        with open(filename, 'r') as csvfile:
            pass
    except FileNotFoundError:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['date', 'number of working_channels_tg'])

    # Append data to the CSV file
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(data_to_append)


def remove_out_of_bounds_dates(df, date_column):
    # Function to check if date is within pandas datetime bounds
    def is_valid_date(date_str):
        try:
            pd.to_datetime(date_str)
            return True
        except pd._libs.tslibs.np_datetime.OutOfBoundsDatetime:
            return False

    # Apply the check to the specified date column and filter the DataFrame
    mask = df[date_column].apply(is_valid_date)
    return df[mask]


def working_count_telegpt():
        # Load everything
        response = requests.get('https://telegpt.tech/api/1.1/obj/Media_Plan', headers=myHeaders).json()
        response = response['response']['results']
        response_df = pd.DataFrame(response)
        today = date.today().strftime("%m/%d/%y")

        # Filter media plans
        media_plan = remove_out_of_bounds_dates(response_df, 'datedate')
        media_plan['datedate'] = pd.to_datetime(media_plan['datedate'])
        media_plan['datedate'] = media_plan['datedate'] + pd.Timedelta(hours=3)
        media_plan['datedate'] = media_plan['datedate'].dt.strftime('%m/%d/%y')
        media_plan = media_plan[media_plan['datedate'] == today]
        media_plan.rename(columns={'channel': 'Link'}, inplace=True)

        # Start saving the thing
        working_channels_count = len(media_plan)
        current_date = datetime.now().strftime("%Y-%m-%d")
        data_to_append = [current_date, working_channels_count]
        filename = 'telegpt_working_channels_daily.csv'

        # Check if the file exists, if not, create it and write the header
        try:
            with open(filename, 'r') as csvfile:
                pass
        except FileNotFoundError:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['date', 'number of working_channels_tg'])

        # Append data to the CSV file
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(data_to_append)

        return response_df




if __name__ == '__main__':
    working_count_tg()

if __name__ == '__main__':
    working_count_telegpt()
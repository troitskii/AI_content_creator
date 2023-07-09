from __future__ import print_function
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime
import json


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)

Google_Sheets_ID = data['Google_Sheets_SAMPLE_SPREADSHEET_ID']
TGstats_key = data['TGstats_key']
openai_key = data['openai_key']
playhtauth_key = data['playhtauth_key']
playht_user_id = data['playht_user_id']
buzz_token = data['buzz_token']


def get_config():
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
                                range='all_done').execute()

    # Extract the values from the result
    values = result.get('values', [])

    # Convert the values into a pandas DataFrame and return it
    df = pd.DataFrame(values[1:], columns=values[0])
    return df


def get_views():
    try:
        URL = "https://api.tgstat.ru/channels/views"
        config_telega = get_config()
        PARAMS = {'token': TGstats_key, 'channelId': config_telega['Link'][0],
                  'startDate': '2/19/23'}
        r = requests.get(url=URL, params=PARAMS)
        data = r.json()
        final_views = pd.DataFrame(data['response'])
        for index in config_telega.index:
            channel_name = config_telega['Link'][index]
            PARAMS = {'token': TGstats_key, 'channelId': channel_name,
                      'startDate': '3/21/23'}
            r = requests.get(url=URL, params=PARAMS)
            data = r.json()
            df = pd.DataFrame(data['response'])
            df = df.rename(columns={"views_count": channel_name})
            print(config_telega['Link'][index])
            final_views = final_views.merge(df, on='period', how='left')
        final_views = final_views.drop(columns=['views_count'])
        return final_views
    except:
        error_log_list = {'errordate': [], 'Link': []}
        error_log = pd.DataFrame(data=error_log_list)
        error_log = error_log.append({'Link': config_telega['Link'][index]}, ignore_index=True)
        error_log['errordate'] = datetime.today().strftime('%Y-%m-%d')
        pass


def get_subscribers():
    try:
        URL = "https://api.tgstat.ru/channels/subscribers"
        config_telega = get_config()
        PARAMS = {'token': TGstats_key, 'channelId': config_telega['Link'][0],
                  'startDate': '3/21/23'}
        r = requests.get(url=URL, params=PARAMS)
        data = r.json()
        final_subscribers = pd.DataFrame(data['response'])
        for index in config_telega.index:
            channel_name = config_telega['Link'][index]
            PARAMS = {'token': TGstats_key, 'channelId': channel_name,
                      'startDate': '2/19/23'}
            r = requests.get(url=URL, params=PARAMS)
            data = r.json()
            df = pd.DataFrame(data['response'])
            df['participants_count'] = df['participants_count'].astype('Int64')
            df['participants_count'] -=2 # every channel has an owner and a bot, need to substract them
            df = df.rename(columns={"participants_count": channel_name})
            final_subscribers = final_subscribers.merge(df, on='period', how='left')
        final_subscribers = final_subscribers.drop(columns=['participants_count'])
        return final_subscribers
    except:
        pass

def get_links_list():
    config_telega = get_config()
    links_list = config_telega['Link'].tolist()
    return links_list

views = get_views()
subscribers = get_subscribers()
views.to_csv('view.csv')
subscribers.to_csv('subscribers.csv')
from __future__ import print_function
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime
import json
import numpy as np


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

def analyze_results(views, subs):
    # Transpose the data
    views_data = views.iloc[:, 1:].transpose()
    subscribers_data = subs.iloc[:, 1:].transpose()

    # Drop first row
    subscribers_data.drop(subscribers_data.index[0], inplace=True)
    views_data.drop(views_data.index[0], inplace=True)

    # Assuming df is your DataFrame
    resulting_df = pd.DataFrame()
    resulting_df['views_last_day'] = views_data.iloc[1:, :1].apply(lambda row: np.mean([val for val in row if val < 1000]),
                                                          axis=1)

    resulting_df['views_avg_7'] = views_data.iloc[1:, :7].apply(lambda row: np.mean([val for val in row if val < 1000]),
                                                          axis=1)
    resulting_df['views_avg_30'] = views_data.iloc[1:, :30].apply(lambda row: np.mean([val for val in row if val < 1000]),
                                                            axis=1)
    resulting_df['subs_last_day'] = subscribers_data[0]
    resulting_df['subs_change_7'] = subscribers_data[0] - subscribers_data[6]
    resulting_df['subs_change_30'] = subscribers_data[0] - subscribers_data[29]

    # Ensure the denominator is not zero to avoid ZeroDivisionError
    non_zero_denom = subscribers_data[0].copy()
    non_zero_denom[non_zero_denom == 0] = np.nan

    # Perform the division. This will return NaN where the denominator was zero.
    resulting_df['efficiency_7'] = resulting_df['views_avg_7'] / non_zero_denom

    # Replace NaN values (where the denominator was zero) with zero.
    resulting_df['efficiency_7'].fillna(0, inplace=True)

    # Perform the division. This will return NaN where the denominator was zero.
    resulting_df['efficiency_30'] = resulting_df['views_avg_30'] / non_zero_denom

    # Replace NaN values (where the denominator was zero) with zero.
    resulting_df['efficiency_30'].fillna(0, inplace=True)

    return resulting_df


views = get_views()
subscribers = get_subscribers()

views.to_csv('view.csv')
subscribers.to_csv('subscribers.csv')

analytics_results = analyze_results(views, subscribers)
analytics_results.to_csv('analytics_results.csv')
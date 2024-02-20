from __future__ import print_function
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import csv


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)


Google_Sheets_analytics = data['Google_Sheets_SAMPLE_SPREADSHEET_ID_analytics']


def update_analytics_spreadsheet(file_name, spreadsheet_id, list_name):
    # Define Google Sheets API service account file and required scopes
    SERVICE_ACCOUNT_FILE = 'googleapi.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    # Create credentials using the service account file and the required scopes
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # Build the Sheets API service using the created credentials
    service = build('sheets', 'v4', credentials=creds)

    # Access the spreadsheet and get the values from the specified range
    sheet = service.spreadsheets()
    f = open(f'{file_name}.csv', "r")
    values = [r for r in csv.reader(f)]
    result = sheet.values().update(spreadsheetId=spreadsheet_id,
                                range=list_name, valueInputOption="USER_ENTERED", body={"values": values}).execute()
    return 'analytics updated'



update_analytics_spreadsheet('episode_creation_log', Google_Sheets_analytics, 'podcasts')
update_analytics_spreadsheet('errors_telegpt', Google_Sheets_analytics, 'telegpt')
update_analytics_spreadsheet('errors_tg', Google_Sheets_analytics, 'telega')
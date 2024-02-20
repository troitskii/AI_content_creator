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

    try:
        # Create credentials using the service account file and the required scopes
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        # Build the Sheets API service using the created credentials
        service = build('sheets', 'v4', credentials=creds)

        # Open the CSV file and read its contents
        with open(f'{file_name}.csv', "r") as f:
            values = [row for row in csv.reader(f)]

        # Prepare the request body and update the sheet
        body = {"values": values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=list_name,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()

        return 'Analytics updated successfully.'
    except Exception as e:
        # Optionally, log the error or pass it silently
        print(f"An error occurred: {e}")
        pass  # Or use 'return "An error occurred."' to notify the caller



update_analytics_spreadsheet('episode_creation_log', Google_Sheets_analytics, 'podcasts')
update_analytics_spreadsheet('errors_telegpt', Google_Sheets_analytics, 'telegpt')
update_analytics_spreadsheet('errors_tg', Google_Sheets_analytics, 'telega')
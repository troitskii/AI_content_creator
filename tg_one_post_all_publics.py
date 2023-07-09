from __future__ import print_function
import telebot
import pandas as pd
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
import csv
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


def main():
    # Load configuration for telegram channels
    config_telega = get_config()

    # Initialize error_testing_list to store failed operations
    error_list = []

    # Iterate through each telegram channel configuration
    for index in config_telega.index:
        try:
            # Extract necessary configurations
            excel = config_telega['Excel'][index]
            password = config_telega['Password'][index]
            link = config_telega['Link'][index]

            # Initialize TeleBot instance with the given token
            bot = telebot.TeleBot(password)

            # Extract the generated text from the response
            text = 'Всем привет! Мы проводим тестирование качества нашего контента, пожалуйста, пройдите опрос в специальном паблике (https://t.me/testingchatgpt). Мы правда-правда будем очень вам благодарны :) \n \nHello everyone! We are conducting quality testing of our content, please take the survey in our special channel (https://t.me/testingchatgpt). We would be really grateful for your participation :)'

            # Send the message to the channel
            bot.send_message(link, text)
        except:
            # Log the failed operation to error_testing_list
            error_list.append(excel)
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Write the errors to a CSV file
            with open('errors.csv', 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Channel', 'Date'])
                for string in error_list:
                    csv_writer.writerow([string, current_date])


if __name__ == '__main__':
    main()
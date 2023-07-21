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
    config_telega = config_telega[config_telega['Language'] == 'English']

    # Initialize error_testing_list to store failed operations
    error_list = []

    # Iterate through each telegram channel configuration
    for index in config_telega.index:
        try:
            # Extract necessary configurations
            password = config_telega['Password'][index]
            link = config_telega['Link'][index]

            # Initialize TeleBot instance with the given token
            bot = telebot.TeleBot(password)

            # Extract the generated text from the response
            text = f'''🎧🍏 Discover the Deliciously Nutritious Journey of "Healthy Food" Podcast! 🥦🎙️
    
                        📢 Calling all foodies and health enthusiasts! 🌱🌍 Get ready to tantalize your taste buds and nourish your mind as we unveil our sizzling new podcast, "Healthy Food"! 🎧🔥
                        
                        🍎 From scrumptious recipes to mindful eating tips, join us on an epic gastronomic adventure that will transform your relationship with food. 🌽🥕
                        
                        🔊 Tune in on all major podcast platforms like Apple, Amazon, Spotify, and more! 🎶🎉 Whether you're a seasoned chef or a curious novice, "Healthy Food" promises to serve up a delectable feast of knowledge and inspiration.
                        
                        🗓️ So mark your calendars and prepare your headphones for a wholesome audio experience like no other. Subscribe today and unlock the secrets to a vibrant, nourishing life! 🌿✨
                        
                        📲 Don't miss out! Click that play button and let the flavors of "Healthy Food" podcast melt in your ears. It's time to nourish your soul while satisfying your cravings! 🎙️🍽️ \n \n https://www.buzzsprout.com/2180464'''

            # Send the message to the channel
            bot.send_message(link, text)
            print(link)
        except: print('BAD TRY, UNSUCCESSFUL ATTEMPT:'+link)


if __name__ == '__main__':
    main()
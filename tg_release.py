from __future__ import print_function
import telebot
from openai import OpenAI
import pandas as pd
from datetime import date
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
import csv
import requests
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

client = OpenAI(api_key = openai_key)

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


def main():
    # Load configuration for telegram channels
    config_telega = get_config('all_done')
    media_plan = get_config('media_plans')
    today = date.today().strftime("%m/%d/%y")

    # Initialize error_testing_list to store failed operations
    error_list = []

    # Iterate through each telegram channel configuration
    for index in config_telega.index:
        if config_telega['work'][index] == '1':
            try:
                # Extract necessary configurations
                image_channel = config_telega['Image_channel'][index]
                password = config_telega['Password'][index]
                link = config_telega['Link'][index]
                context = config_telega['Context'][index]
                print(link)

                # Initialize TeleBot instance with the given token
                bot = telebot.TeleBot(password)

                # Getting prompt from media plan
                getting_prompt = media_plan[media_plan['channel'] == link]
                getting_prompt['datedate'] = pd.to_datetime(getting_prompt['datedate'], errors='coerce',
                                                            dayfirst=True).dt.strftime(
                    '%m/%d/%y')
                getting_prompt = getting_prompt[getting_prompt['datedate'] == today]
                getting_prompt = getting_prompt['prompt_human']


                # Check if the channel requires an image
                if image_channel == 'yes':

                    # Create an image using OpenAI API
                    response_image = client.images.generate(
                        prompt=getting_prompt.iloc[0],
                        n=1,
                        size="1024x1024"
                    )

                    # Extract image URL from the response
                    df = pd.DataFrame([image.__dict__ for image in response_image.data])
                    image_url = df["url"].iloc[0]

                    response = requests.get(f'https://api.telegram.org/bot{password}/sendPhoto', {
                        'photo': image_url,
                        'chat_id': link,
                        'caption': getting_prompt.iloc[0]
                    })

                    if response.status_code == 200:
                        print('ok')
                    else:
                        print(response.text)  # Do what you want with response

                else:
                    # Create a chat message using OpenAI API
                    messages = [
                        {"role": "system",
                         "content": context},
                        {"role": "user", "content": getting_prompt.iloc[0]}
                    ]
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=messages,
                        max_tokens=1500,
                        n=1,
                        temperature=0,
                    )
                    choices = response.choices
                    message = choices[0].message
                    content = message.content

                    # Send the message to the channel
                    bot.send_message(link, content)
            except:
                # Log the failed operation to error_testing_list
                error_list.append(link)
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Open the CSV file in append mode
                with open('errors_tg.csv', 'a', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)

                    # Check if the file is empty, if so, write the headers
                    if csvfile.tell() == 0:
                        csv_writer.writerow(['Channel', 'Date'])

                    # Write the errors
                    for string in error_list:
                        csv_writer.writerow([string, current_date])

        else: pass



if __name__ == '__main__':
    main()
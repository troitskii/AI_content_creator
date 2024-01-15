from __future__ import print_function
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
from openpyxl import Workbook
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)

Google_Sheets_ID = data['Google_Sheets_SAMPLE_SPREADSHEET_ID']
TGstats_key = data['TGstats_key']
openai_key = data['openai_key']
playhtauth_key = data['playhtauth_key']
playht_user_id = data['playht_user_id']
buzz_token = data['buzz_token']


# Set up API key and client
client = OpenAI(api_key = openai_key)

expressions_to_remove = ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.',
                         '12.', '13.', '14.', '15.', '16.', '17.', '18.', '19.', '20.', '21.', '22.',
                         '23.', '24.', '25.', '26.', '27.', '28.', '29.', '30.', '31.', '32.', '33.',
                         '34.', '35.', '36.', '37.', '38.', '39.', '40.', '41.', '42.', '43.', '44.',
                         '45.', '46.', '47.', '48.', '49.', '50.', '- ', '51.', '52.', '53.', '54.', '55.',
                         '56.', '57.','58.','59.','60.','61.','62.','63.','64.','65.','66.','67.','68.','69.','70.']
expressions_to_remove.reverse()

def remove_expressions(input_string):
    for expression in expressions_to_remove:
        input_string = input_string.replace(expression, '')
    return input_string


def get_config():
    # Define Google Sheets API service account file and required scopes
    SERVICE_ACCOUNT_FILE = r'googleapi.json'
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
                                range='content_create').execute()

    # Extract the values from the result
    values = result.get('values', [])

    # Convert the values into a pandas DataFrame and return it
    df = pd.DataFrame(values[1:], columns=values[0])
    return df


def generate_media_plans():
    config_telega = get_config()
    #plans_count = 30
    d = {'name': [], 'item': []}
    df_main = pd.DataFrame(data=d)
    for index in config_telega.index:
        # Extract necessary configurations
        language = config_telega['Language'][index]
        topic = config_telega['Channel description'][index]
        link = config_telega['Link'][index]
        plans_count = int(config_telega['number'][index])
        if plans_count > 0:
            try:
                print(link)
                prompt = f"Create a media plan for a Telegram channel for {plans_count} prompts. The telegram channel writes about {topic}. Each topic should start from a new line. Do not write introduction or a head of the reply message. Start immediatelly with prompts list. Prompts must be written in {language}."
                messages = [
                    {"role": "system",
                     "content": "Imagine that you are the owner of a Telegram channel. The idea of the Telegram channel is that it is not the owner who writes in it, but ChatGPT. The channel owner needs to come up with prompts for ChatGPT every day so that ChatGPT writes interesting posts for the channel subscribers. The prompts should be interesting all on the designated topic."},
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=3500,
                    n=1,
                    temperature=1,
                )

                # Extract the generated text from the response
                choices = response.choices
                message = choices[0].message
                text = message.content

                cleaned_input = remove_expressions(text)
                rows = cleaned_input.split('\n')
                names = [link] * len(rows)
                df = pd.DataFrame(list(zip(names, rows)), columns=['name', 'item'])
                df_main = pd.concat([df_main, df], ignore_index=True)
            except Exception as e:
                print(f"Error occurred while processing index {index}. Error message: {e}")
                continue
        else:
            pass
    return df_main


def generate_media_plans_2(topic, link, language):
    plans_count = 30
    d = {'name': [], 'item': []}
    df_main = pd.DataFrame(data=d)
    prompt = f"Create a media plan for a Telegram channel for {plans_count} prompts. The telegram channel writes about {topic}. Each topic should start from a new line. Do not write introduction or a head of the reply message. Start immediatelly with prompts list. Prompts must be written in {language}."
    messages = [
        {"role": "system",
         "content": "Imagine that you are the owner of a Telegram channel. The idea of the Telegram channel is that it is not the owner who writes in it, but ChatGPT. The channel owner needs to come up with prompts for ChatGPT every day so that ChatGPT writes interesting posts for the channel subscribers. The prompts should be interesting all on the designated topic."},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=3500,
        n=1,
        temperature=0,
    )

    # Extract the generated text from the response
    choices = response.choices
    message = choices[0].message
    text = message.content

    cleaned_input = remove_expressions(text)
    rows = cleaned_input.split('\n')
    names = [link] * len(rows)
    df = pd.DataFrame(list(zip(names, rows)), columns=['name', 'item'])
    df_main = pd.concat([df_main, df], ignore_index=True)
    return df_main



def clean_column_content(df, column):
    df[column] = df[column].str.replace(r'\(prompt_images.*?.jpg\)', '', regex=True)
    df[column] = df[column].str.replace(r'![', '')
    df[column] = df[column].str.replace(r']', '')
    df[column] = df[column].str.replace(r'[', '')
    df[column] = df[column].str.replace(r'"', '')
    df[column] = df[column].str.replace(r'Image: ', '')
    df[column] = df[column].str.replace(r'(video_link)', '')

    df = df[df[column].notna()]
    df[column] = df[column].astype(str)
    df = df[df[column].str.len() >= 10]

    df = df[~df[column].str.startswith("Sure! ")]
    df = df[~df[column].str.startswith("Prompts for a Telegram channel ")]
    df = df[~df[column].str.startswith("    Prompt")]
    df = df[~df[column].str.startswith("Привет, ")]
    df = df[~df[column].str.startswith("Надеюсь, эти темы ")]
    df = df[~df[column].str.startswith("Image(https")]
    df = df[~df[column].str.startswith("Feel free to ")]
    df = df[~df[column].str.startswith("Примечание: Пожалуйста, ")]
    df = df[~df[column].str.startswith("Prompts for ")]

    df = df[~df[column].str.contains("(image_link)")]
    df = df[~df[column].str.contains("(image_url)")]
    df = df[~df[column].str.contains("Note: ")]

    return df


def clean_media_plans():
    workbook = generate_media_plans_2('Лучшие клубы мира', "@mir", "Russian")
    workbook = clean_column_content(workbook, 'item')

    # Sort DataFrame based on 'X'
    workbook = workbook.sort_values(by='name')
    # Initialize dates column to today
    workbook['dates'] = datetime.today().date()

    # Iterate and adjust dates
    for i in range(1, len(workbook)):
        if workbook.iloc[i]['name'] == workbook.iloc[i - 1]['name']:
            workbook.iloc[i, workbook.columns.get_loc('dates')] = workbook.iloc[i - 1]['dates'] + timedelta(days=1)
    json_str = workbook.to_json(orient='records')
    return json_str



result = clean_media_plans()

result.to_csv('hello_world')
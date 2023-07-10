from __future__ import print_function
import openai
import pandas as pd
from datetime import date
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
import json
from pydub import AudioSegment
from io import BytesIO


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)

Google_Sheets_ID = data['Google_Sheets_SAMPLE_SPREADSHEET_ID']
TGstats_key = data['TGstats_key']
openai_key = data['openai_key']
playhtauth_key = data['playhtauth_key']
playht_user_id = data['playht_user_id']
buzz_token = data['buzz_token']


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


def get_prompt(channel_name):
    # Load config for prompt
    media_plans_excel = get_config('media_plans')
    today = date.today().strftime("%m/%d/%y")

    # Getting TEXT prompt from media plan
    getting_prompt = media_plans_excel[media_plans_excel['channel'] == channel_name]
    getting_prompt['datedate'] = pd.to_datetime(getting_prompt['datedate'], errors='coerce',
                                                dayfirst=True).dt.strftime('%m/%d/%y')
    getting_prompt = getting_prompt[getting_prompt['datedate'] == today]
    getting_prompt = getting_prompt['prompt_human'].iloc[0]
    return getting_prompt


def create_podcast_text(prompt):
    # Set OpenAI API key
    openai.api_key = openai_key

    # Create a chat message using OpenAI API
    messages = [
        {"role": "system",
         "content": 'You need to write an script for a podcast on the given topic. In the podcast there are no guests - the author of the podcast does it alone, so do not divide podcast into roles (author and guest). Do not write titles and chapters. Do not name the chapters - just write what the author needs to read. The text must be long.'},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=2000,
        n=1,
        temperature=0,
    )
    # Extract the generated text from the response
    podcast_text = response.choices[0].message['content'].strip()
    return podcast_text


def summarize_podcast_text(podcast_text):
    # Set OpenAI API key
    openai.api_key = openai_key

    # Create a chat message using OpenAI API
    messages2 = [
        {"role": "system",
         "content": 'You need to summarize podcast text in 2 - 3 senteces. I will send you the text of the podcast in next message.'},
        {"role": "user", "content": podcast_text}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages2,
        max_tokens=100,
        n=1,
        temperature=0,
    )
    # Extract the generated text from the response
    summarized_text = response.choices[0].message['content'].strip()
    return summarized_text


def create_mp3(podcast_text, channel_name):
    url = "https://play.ht/api/v2/tts"
    headers = {
        "AUTHORIZATION": playhtauth_key,
        "X-USER-ID": playht_user_id,
        "accept": "text/event-stream",
        "content-type": "application/json"
    }
    data = {
        "text": podcast_text,
        "voice": get_artist(channel_name)
    }
    response = requests.post(url, headers=headers, json=data)
    text_2 = response.text

    url = None
    lines = text_2.split("\n")

    for line in lines:
        if line.startswith("event: completed"):
            data_line = lines[lines.index(line) + 1]  # data line comes after event line
            data_str = data_line.replace("data: ", "", 1)  # remove "data: " prefix
            data_dict = json.loads(data_str)
            url = data_dict.get('url')
            break
    return url


def get_artist(channel_name):
    all_done_excel = get_config('all_done')
    artist_name = all_done_excel[all_done_excel['Link'] == channel_name]
    artist_name = artist_name['Artist'].iloc[0]
    return artist_name


def get_episode_number(channel_name):
    today = date.today().strftime("%m/%d/%y")
    media_plans_excel = get_config('media_plans')

    # Getting TEXT prompt from media plan
    episode_number = media_plans_excel[media_plans_excel['channel'] == channel_name]
    episode_number['datedate'] = pd.to_datetime(episode_number['datedate'], errors='coerce',
                                                dayfirst=True).dt.strftime('%m/%d/%y')
    episode_number = episode_number[episode_number['datedate'] == today]
    episode_number = episode_number['episode_number'].iloc[0]
    return episode_number


def get_season_number(channel_name):
    today = date.today().strftime("%m/%d/%y")
    media_plans_excel = get_config('media_plans')

    # Getting TEXT prompt from media plan
    season_number = media_plans_excel[media_plans_excel['channel'] == channel_name]
    season_number['datedate'] = pd.to_datetime(season_number['datedate'], errors='coerce',
                                                dayfirst=True).dt.strftime('%m/%d/%y')
    season_number = season_number[season_number['datedate'] == today]
    season_number = season_number['season_number'].iloc[0]
    return season_number


def create_tags(channel_text):
    # Set OpenAI API key
    openai.api_key = openai_key

    # Create a chat message using OpenAI API
    messages3 = [
        {"role": "system",
         "content": 'You must write hastags based on the text I will send you.'},
        {"role": "user", "content": channel_text}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages3,
        max_tokens=500,
        n=1,
        temperature=0,
    )
    # Extract the generated text from the response
    tags = response.choices[0].message['content'].strip()

    # find the position of the first '#'
    hash_position = tags.find('#')

    # if '#' is not found, return the original text
    if hash_position == -1:
        return tags

    # return the part of the text after the first '#'
    return tags[hash_position:]


def get_name(channel_name):
    config = get_config('all_done')
    config = config[config['Link'] == channel_name]
    channel_real_name = config['Channel name'].iloc[0]
    return channel_real_name


def create_artwork(channel_name):
    # Create an image using OpenAI API
    response_image = openai.Image.create(
        prompt= get_name(channel_name) +'art cover',
        n=1,
        size="1024x1024"
    )
    # Extract image URL from the response
    image_url = response_image['data'][0]['url']
    return image_url


def delete_specific_words(text):
    words_to_delete = ["Title: ", "Introduction"]
    for word in words_to_delete:
        text = text.replace(word, '')
    return text


def get_audio_duration(url):
    response = requests.get(url)
    audio = AudioSegment.from_file(BytesIO(response.content))
    return len(audio) / 1000.0


def get_base_url(channel_name):
    config = get_config('all_done')
    config = config[config['Link'] == channel_name]
    base_url = config['base_url'].iloc[0]
    return base_url


def create_episode(channel_name):
    if get_episode_number(channel_name) is not None:

        # Get all data
        get_prompt_result = get_prompt(channel_name)
        podcast_text = create_podcast_text(get_prompt_result)
        mp3 = create_mp3(podcast_text, channel_name)
        artwork = create_artwork(channel_name)
        artist = get_artist(channel_name)
        summary_podcast = summarize_podcast_text(podcast_text)
        tags = create_tags(podcast_text)
        season_number = get_season_number(channel_name)
        episode_number = get_episode_number(channel_name)

        # API configuration
        base_url = get_base_url(channel_name)  # Replace 9999 with your podcast identifier
        api_token = buzz_token  # Replace with your API token

        # Authorization headers
        headers = {
            "Authorization": f"Token token={api_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        url = f"{base_url}/episodes.json"
        data = {
            "title": get_prompt_result,
            "description": get_prompt_result,
            "summary": summary_podcast,
            "artist": artist,
            "tags": tags,
            "published_at": date.today().strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "duration": 300,
            "guid": "Buzzsprout788880",
            "inactive_at": None,
            "episode_number": episode_number,
            "season_number": season_number,
            "explicit": True,
            "private": False,
            "email_user_after_audio_processed": True,
            "audio_url": mp3,
            "artwork_url": artwork
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 201:
            episode = response.json()
            # Process the created episode data
            print(episode)
        else:
            print(f"Error: {response.status_code} - {response.text}")
    else: print('No episodes today!')


def main():
    # Load configuration for Podcasts
    config_telega = get_config('all_done')

    # Iterate through each telegram channel configuration
    for index in config_telega.index:
        if config_telega['Podcast'][index] == '1':
            create_episode(config_telega['Link'][index])
        else: pass


if __name__ == '__main__':
    main()
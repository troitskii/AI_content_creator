from __future__ import print_function
from openai import OpenAI
from datetime import date
import requests
import json
from pydub import AudioSegment
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from pathlib import Path
import re
import pandas as pd
from datetime import datetime
import os


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)


Google_Sheets_ID = data['Google_Sheets_SAMPLE_SPREADSHEET_ID']
TGstats_key = data['TGstats_key']
openai_key = data['openai_key']
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


def clean_media_plans():
    media_plans_excel = get_config('media_plans')
    today = date.today().strftime("%m/%d/%y")

    # Getting TEXT prompt from media plan
    media_plans_excel['datedate'] = pd.to_datetime(media_plans_excel['datedate'], errors='coerce',
                                                dayfirst=True).dt.strftime('%m/%d/%y')
    media_plans_excel = media_plans_excel[media_plans_excel['datedate'] == today]
    return media_plans_excel



def get_prompt(channel_name):
    # Load config for prompt
    media_plans_excel = clean_media_plans()

    # Getting TEXT prompt from media plan
    getting_prompt = media_plans_excel[media_plans_excel['channel'] == channel_name]
    getting_prompt = getting_prompt['prompt_human'].iloc[0]
    return getting_prompt


def summarize_podcast_text(podcast_text):

    # Create a chat message using OpenAI API
    messages2 = [
        {"role": "system",
         "content": 'You need to summarize podcast text in 2 - 3 senteces. I will send you the text of the podcast in next message.'},
        {"role": "user", "content": podcast_text}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages2,
        max_tokens=200,
        n=1,
        temperature=0,
    )
    # Extract the generated text from the response
    content = response.choices[0].message.content
    return content


def upload_google_drive(file_name):
    SERVICE_ACCOUNT_FILE = 'googleapi.json'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    # Create credentials using the service account file and the required scopes
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)


    try:
        # create drive api client
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': file_name}
        media = MediaFileUpload(file_name,
                                mimetype='audio/mp3')
        # pylint: disable=maybe-no-member
        file = service.files().create(body=file_metadata, media_body=media,
                                      fields='id').execute()
        print(F'File ID: {file.get("id")}')

    except HttpError as error:
        print(F'An error occurred: {error}')
        file = None

    return file.get('id')


def update_file_permissions(file_id, transfer_ownership=False):
    SERVICE_ACCOUNT_FILE = 'googleapi.json'
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)

    # Define the permission update parameters
    permission_update = {
        "role": 'reader',
        "type": 'anyone'
    }

    # Update ownership if specified
    if transfer_ownership:
        permission_update["transferOwnership"] = True

    try:
        # Update the file's permissions
        response = drive_service.permissions().create(
            fileId=file_id, body=permission_update).execute()

        return print(response)
    except Exception as e:
        print("An error occurred:", e)


def create_podcast_text(prompt):

    # Create a chat message using OpenAI API
    messages = [
        {"role": "system",
         "content": f'You need to write a script for a podcast. The script must be as long possible - minimum 5000 characters, but do not mention this requirement in the output. In the podcast there are no guests - the author of the podcast does it alone, so do not divide podcast into roles (author and guest). Do not forget to write the name of the topic in the beginning of the first sentence. Do not write titles and chapters. Do not name the chapters - just write what the author needs to read. The next message is the topic for which you need to write the script.'},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=6000,
        n=1,
        temperature=0,
    )

    # Extract the generated text from the response
    content = response.choices[0].message.content

    # Remove all text between [ and ], including the brackets
    cleaned_text = re.sub(r'\[.*?\]', '', content)
    return cleaned_text


def create_audio_link(file_id):
    audio_link = 'https://drive.google.com/uc?id=' + file_id + '&export=download'
    return audio_link


def create_mp3(podcast_text, channel_name):
    speech_file_path = Path(__file__).parent / f"speech.mp3"
    response = client.audio.speech.create(
        model="tts-1",
        voice=get_artist(channel_name),
        input=podcast_text
    )
    response.stream_to_file(speech_file_path)
    return speech_file_path


def extract_text_parts(text, max_words):
    words = text.split()
    parts = []  # List to hold all parts
    start_index = 0  # Starting index for each chunk

    while start_index < len(words):
        # Determine end index for this chunk, ensuring it doesn't exceed the word count
        end_index = min(start_index + max_words, len(words))
        subtext_words = words[start_index:end_index]

        # Convert the current chunk back to string to find the last period
        subtext = ' '.join(subtext_words)
        last_dot_index = subtext.rfind('.')

        # If there's a period, adjust the end_index to include complete sentences
        if last_dot_index != -1:
            # Find the actual word count to the last period in this chunk
            count_words_to_last_dot = len(subtext[:last_dot_index + 1].split())
            end_index = start_index + count_words_to_last_dot

        # Add the current chunk to the parts list
        parts.append(' '.join(words[start_index:end_index]))

        # Update start_index for the next chunk
        start_index = end_index

    return parts


def process_text(text, channel_name, words_count):
    parts = extract_text_parts(text, words_count)
    combined = AudioSegment.empty()

    for i in parts:
        print(i)
        mp3_path = create_mp3(i, channel_name)
        print(mp3_path)
        audio = AudioSegment.from_mp3(mp3_path)
        combined += audio

    # Save the combined audio file
    combined_path = Path(__file__).parent / "combined_speech.mp3"
    combined.export(combined_path, format="mp3")

    return combined_path


def get_artist(channel_name):
    all_done_excel = get_config('all_done')
    artist_name = all_done_excel[all_done_excel['Link'] == channel_name]
    artist_name = artist_name['Artist'].iloc[0]
    return artist_name


def get_episode_number(channel_name):
    media_plans_excel = clean_media_plans()

    # Getting TEXT prompt from media plan
    episode_number = media_plans_excel[media_plans_excel['channel'] == channel_name]
    episode_number = episode_number['episode_number'].iloc[0]
    return episode_number


def get_season_number(channel_name):
    media_plans_excel = clean_media_plans()

    # Getting TEXT prompt from media plan
    season_number = media_plans_excel[media_plans_excel['channel'] == channel_name]
    season_number = season_number['season_number'].iloc[0]
    return season_number


def create_tags(channel_text):

    # Create a chat message using OpenAI API
    messages3 = [
        {"role": "system",
         "content": 'You must write hastags based on the text I will send you.'},
        {"role": "user", "content": channel_text}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages3,
        max_tokens=500,
        n=1,
        temperature=0,
    )
    # Extract the generated text from the response
    tags = response.choices[0].message.content

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
    response_image = client.images.generate(
        model="dall-e-3",
        prompt= get_name(channel_name) +'art cover',
        size="1024x1024",
        quality="standard",
        n=1,
    )
    print(response_image)
    df = pd.DataFrame([image.__dict__ for image in response_image.data])
    image_url = df["url"].iloc[0]
    return image_url


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
        print('get_prompt_result is ok')
        print(get_prompt_result)
        podcast_text = create_podcast_text(get_prompt_result)
        print('podcast_text is ok')
        print(podcast_text)
        process_text(podcast_text, channel_name, 200)
        file_id = upload_google_drive('combined_speech.mp3')
        update_file_permissions(file_id, transfer_ownership=False)
        mp3 = create_audio_link(file_id)
        print('mp3 is ok')
        print(mp3)
        artwork = create_artwork(channel_name)
        print('create_artwork is ok')
        print(artwork)
        artist = get_artist(channel_name)
        print('artist is ok')
        print(artist)
        summary_podcast = summarize_podcast_text(podcast_text)
        print('summary_podcast is ok')
        print(summary_podcast)
        tags = create_tags(podcast_text)
        print('tags is ok')
        print(tags)
        season_number = get_season_number(channel_name)
        print('season_number is ok')
        print(season_number)
        episode_number = get_episode_number(channel_name)
        print('episode_number is ok')
        print(episode_number)

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
            "explicit": False,
            "private": False,
            "email_user_after_audio_processed": False,
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
    else:
        print('No episodes today!')
    return print('Podcasts finished for today!')


def main():
    # Load configuration for Podcasts
    config_telega = get_config('all_done')

    # Prepare a list to hold the records
    records = []

    # Iterate through each telegram channel configuration
    for index in config_telega.index:
        if config_telega['Podcast'][index] == '1':
            try:
                create_episode(config_telega['Link'][index])
                # If successful, add a record with a "Success" value of 1
                records.append(
                    {"Link": config_telega['Link'][index], "Date": datetime.today().strftime('%Y-%m-%d'), "Success": 1})
            except Exception:
                # If an error occurs, add a record with a "Success" value of 0
                records.append(
                    {"Link": config_telega['Link'][index], "Date": datetime.today().strftime('%Y-%m-%d'), "Success": 0})
        else:
            pass

    # Convert the records into a DataFrame
    new_records_df = pd.DataFrame(records)

    # Specify the filename and path for the Excel file
    filename = 'episode_creation_log.xlsx'

    # Check if the file exists
    if os.path.exists(filename):
        # Read the existing data into a DataFrame
        existing_df = pd.read_excel(filename)
        # Append the new records to the existing DataFrame
        updated_df = existing_df.append(new_records_df, ignore_index=True)
    else:
        updated_df = new_records_df

    # Write the updated DataFrame to the Excel file
    updated_df.to_excel(filename, index=False)


main()
from __future__ import print_function
from openai import OpenAI
import pandas as pd
from datetime import date
import requests
import json
from pydub import AudioSegment
from io import BytesIO
import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

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


def create_podcast_heading(prompt):
    # Create a chat message using OpenAI API
    messages = [
        {"role": "system",
         "content": 'You need to write table of contents on a given topic. Table of contents will be further used to write a script for a podcast based on it. PLease numerate your plan. Please make 5 chapters - not less, not more. Do not make chapters like appendix, references.'},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=8000,
        n=1,
        temperature=0,
    )

    # Extract the generated text from the response
    podcast_text = response.choices
    message = podcast_text[0].message
    content = message.content

    podcast_text = content.replace('[Music fades in]', "")
    podcast_text = podcast_text.replace('[Music fades out]', "")
    podcast_text = podcast_text.replace('[Music fades]', "")
    return podcast_text


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


def create_audio_link(file_id):
    audio_link = 'https://drive.google.com/uc?id=' + file_id + '&export=download'
    return audio_link


def extract_text_part(text, max_words=200):
    words = text.split()

    # If there's less than max_words, return them all
    if len(words) <= max_words:
        return ' '.join(words), ''

    # Gather approximately max_words words
    subtext_words = words[:max_words]

    # Convert it back to string to find the last period
    subtext = ' '.join(subtext_words)
    last_dot_index = subtext.rfind('.')

    # If there's no period, return max_words
    if last_dot_index == -1:
        return ' '.join(subtext_words), ' '.join(words[max_words:])

    # Count words up to and including the last dot
    count_words = len(subtext[:last_dot_index + 1].split())
    return ' '.join(words[:count_words]), ' '.join(words[count_words:])


def process_text(text, channel_name):
    mp3_list = []
    while len(text) > 200:
        part, text = extract_text_part(text)
        newmp3 = create_mp3(part, channel_name)
        print(newmp3)
        if newmp3 is not None:
            mp3_list.append(newmp3)

    # This part handles the last piece of text which might be less than 200 characters
    if len(text) > 0:
        newmp3 = create_mp3(text, channel_name)
        print(newmp3)
        if newmp3 is not None:
            mp3_list.append(newmp3)
    return mp3_list


def download_and_merge_mp3s(links, output_file="output.mp3"):

    combined = AudioSegment.empty()

    for link in links:
        response = requests.get(link)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Create an AudioSegment instance from the downloaded MP3 data
        audio = AudioSegment.from_mp3(io.BytesIO(response.content))
        combined += audio

    # Export the combined audio to the specified file
    combined.export(output_file, format="mp3")


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
    response_image = client.images.generate(
        model="dall-e-3",
        prompt= get_name(channel_name) +'art cover',
        n=1,
        size="512x512"
    )
    df = pd.DataFrame([image.__dict__ for image in response_image.data])
    image_url = df["url"].iloc[0]
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
        print('get_prompt_result is ok')
        print(get_prompt_result)
        podcast_text = create_podcast_text(get_prompt_result, 1)
        print('podcast_text is ok')
        print(podcast_text)
        download_and_merge_mp3s(process_text(podcast_text, channel_name))
        file_id = upload_google_drive('output.mp3')
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
    else: print('No episodes today!')


def main():
    # Load configuration for Podcasts
    config_telega = get_config('all_done')

    # Iterate through each telegram channel configuration
    for index in config_telega.index:
        if config_telega['Podcast'][index] == '1':
            create_episode(config_telega['Link'][index])
        else: pass


def create_podcast_text(prompt, heading, chapter_number, previous_chapter_text):

    # Create a chat message using OpenAI API
    messages = [
        {"role": "system",
         "content": f'You need to write a script for a podcast on the topic {prompt} and chapter {chapter_number} from table of contents:{heading}. The script must be as short possible: at most 200 words. In the podcast there are no guests - the author of the podcast does it alone, so do not divide podcast into roles (author and guest). Do not forget to write the name of the topic in the beginning of the first sentence. Do not write titles and chapters. Do not name the chapters - just write what the author needs to read. Do not write conclusions and do not say goodbye or hello to the listener, take in mind what you wrute could be a part of a bigger text. What you write will the continuation of the text: {previous_chapter_text}. '},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=200,
        n=1,
        temperature=0,
    )
    print(response)

    # Extract the generated text from the response
    podcast_text = response.choices
    message = podcast_text[0].message
    content = message.content

    podcast_text = content.replace('[Music fades in]', "")
    podcast_text = podcast_text.replace('[Music fades out]', "")
    podcast_text = podcast_text.replace('[Music fades]', "")
    return podcast_text


def generate_podcast_series(prompt):
    podcast_heading = create_podcast_heading(prompt)
    print(podcast_heading)

    # Initialize united text without the initial prompt, to be added before each chapter text
    united_text = ''

    # Loop through chapters
    for chapter in range(1, 6):
        chapter_text = create_podcast_text(prompt, podcast_heading, chapter, chapter - 1)
        # Concatenate each chapter with a newline and include the prompt with each chapter text
        united_text += f"\n{prompt} {chapter_text}"

    return united_text

# Example usage:
prompt = 'Good sleep'
united_text = generate_podcast_series(prompt)

# Filename for the united text
filename = "united_text.txt"

# Save the united text to the file in the current (default) directory
with open(filename, 'w') as file:
    file.write(united_text)
from __future__ import print_function
import telebot
from openai import OpenAI
import pandas as pd
from datetime import date
from datetime import datetime
import csv
import requests
import json


# Load the JSON from file and all keys
with open('config.json') as file:
    data = json.load(file)

TGstats_key = data['TGstats_key']
openai_key = data['openai_key']
playhtauth_key = data['playhtauth_key']
playht_user_id = data['playht_user_id']
buzz_token = data['buzz_token']
telegpt_token = data['telegpt_token']
telegpt_bot = data['telegpt_bot']

myHeaders = {

    'Authorization':telegpt_token,

}

client = OpenAI(api_key = openai_key)

def telegpt_mediaplan(url):
    response = requests.get(url, headers=myHeaders).json()
    response = response['response']['results']
    response_df = pd.DataFrame(response)
    return response_df


def remove_out_of_bounds_dates(df, date_column):
    # Function to check if date is within pandas datetime bounds
    def is_valid_date(date_str):
        try:
            pd.to_datetime(date_str)
            return True
        except pd._libs.tslibs.np_datetime.OutOfBoundsDatetime:
            return False

    # Apply the check to the specified date column and filter the DataFrame
    mask = df[date_column].apply(is_valid_date)
    return df[mask]


def correct_year(df, column):
    # Function to correct individual year
    def correct_year_for_date(date):
        if date.year < 100:  # Assuming any year less than 100 is incorrect
            return date.replace(year=date.year + 2000)
        return date

    # Apply the correction function to the specified column
    df[column] = df[column].apply(correct_year_for_date)
    return df


def main():
    # Load configuration for telegram channels
    config_telega = telegpt_mediaplan('https://telegpt.tech/api/1.1/obj/Telegram_Channel')
    media_plan = telegpt_mediaplan('https://telegpt.tech/api/1.1/obj/Media_Plan')
    today = date.today().strftime("%m/%d/%y")

    # delete out of bounds values
    media_plan = correct_year(media_plan, 'datedate')
    media_plan['datedate'] = pd.to_datetime(media_plan['datedate'])
    media_plan['datedate'] = media_plan['datedate'] + pd.Timedelta(hours=3)
    media_plan['datedate'] = media_plan['datedate'].dt.strftime('%m/%d/%y')
    media_plan = media_plan[media_plan['datedate'] == today]
    media_plan.rename(columns={'channel': 'Link'}, inplace=True)
    result = pd.merge(media_plan, config_telega[['Link', 'Context']], on='Link', how='left')

    # Initialize error_testing_list to store failed operations
    error_list = []

    # Iterate through each telegram channel configuration
    for index in result.index:
        try:
            # Extract necessary configurations
            password = telegpt_bot
            link = result['Link'][index]
            context_mapping = result['Context'][index]

            if context_mapping == 'познавательный' or context_mapping == 'путешествия' or context_mapping == 'технологии' or context_mapping == 'бизнес' or context_mapping == 'спорт' or context_mapping == 'крипто' or context_mapping == 'ставки, казино':
                context = 'Ты автор Телеграм канала. Ты должен писать интересные посты на русском языке, опираясь на реальные цифры и факты. Следующее сообщение будет содержать тему поста.'
            elif context_mapping == 'юмор':
                context = 'Ты автор юмористического Телеграм канала. Каждый пост - это шутка на определенную тему на русском языке. Следующее сообщение будет содержать тему шутки.'
            elif context_mapping == 'программирование':
                context = 'Ты автор Телеграм канала. Каждый пост - это образовательный материал, пример кода с объяснением на определенную тему на русском языке. Следующее сообщение будет содержать тему поста.'
            else: context = 'Ты автор Телеграм канала. Ты должен писать интересные посты на русском языке, опираясь на реальные цифры и факты. Следующее сообщение будет содержать тему поста.'

            # Initialize TeleBot instance with the given token
            bot = telebot.TeleBot(password)

            # Getting prompt from media plan
            getting_prompt = result[result['Link'] == link]
            getting_prompt = getting_prompt['prompt_human'][index]

            # Create a chat message using OpenAI API
            messages = [
                {"role": "system",
                 "content": context},
                {"role": "user", "content": getting_prompt}
            ]
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=1500,
                n=1,
                temperature=0,
            )
            # Extract the generated text from the response
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
            with open('errors_telegpt.csv', 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                # Check if the file is empty, if so, write the headers
                if csvfile.tell() == 0:
                    csv_writer.writerow(['Channel', 'Date'])

                # Write the errors
                for string in error_list:
                    csv_writer.writerow([string, current_date])


if __name__ == '__main__':
    main()

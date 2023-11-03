import openai
import speech_recognition as sr
import pygame
import requests
import os
import json
import keyboard

# Constants
OPENAI_API_KEY = "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"
FREESOUND_API_KEY = freesound = "uSXkh8wgzZvoQE8CW2wW7VhXSPjDL1OSRhXvmU1o"
BASE_SEARCH_URL = "https://freesound.org/apiv2/search/text/"
BASE_SOUND_DETAIL_URL = "https://freesound.org/apiv2/sounds/{sound_id}/"
SOUNDS_DIR = "audio_clips"
COMMANDS_JSON = "commands.json"

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Ensure the audio_clips directory exists
if not os.path.exists(SOUNDS_DIR):
    os.makedirs(SOUNDS_DIR)

# Ensure the commands.json file exists
if not os.path.exists(COMMANDS_JSON):
    with open(COMMANDS_JSON, 'w') as file:
        json.dump({}, file)

def search_and_download_sound(term):
    headers = {"Authorization": f"Token {FREESOUND_API_KEY}"}
    params = {"query": term, "filter": "duration:[0.5 TO 10]", "sort": "score"}
    response = requests.get(BASE_SEARCH_URL, params=params, headers=headers)

    if response.status_code == 200:
        results = response.json()
        if results['count'] > 0:
            sound_id = results['results'][0]['id']
            detail_response = requests.get(BASE_SOUND_DETAIL_URL.format(sound_id=sound_id), headers=headers)
            if detail_response.status_code == 200:
                sound_detail = detail_response.json()
                preview_url = sound_detail['previews'].get('preview-lq-mp3', None)
                response = requests.get(preview_url, stream=True)
                filename = os.path.join(SOUNDS_DIR, f"{term}.mp3")
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return filename
    return None

def listen_and_play_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Press spacebar to start recording...")
        keyboard.wait('space')
        print("Recording... Press spacebar again to stop.")
        audio = r.listen(source, timeout=None)
        if keyboard.is_pressed('space'):
            print("Stopped recording.")

        try:
            spoken_text = r.recognize_google(audio, language="en-EN", show_all=False)
            print("You mentioned:", spoken_text)

            with open(COMMANDS_JSON, "r") as file:
                commands_mapping = json.load(file)

            themes_list = ', '.join(commands_mapping.keys())
            message_content = f"Help Me pick a Sound from my dnd campaign. Based on this sentence:'{spoken_text}' - What sound should i play? Here's a list of options:  {themes_list} Is there a perfect sound match there? If Not Suggest a sound name i could add to my collection. Dont talk and dont converse with me at all except to say a soundname with from the list or if there isn't a 95% match say the soundname that should be in the list. Respond with 2 words only."

            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message_content}
            ]

            response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, temperature=0.8, max_tokens=10)
            matched_theme = str(response['choices'][0]['message']['content']).strip()
            print(f"Matched theme: {matched_theme}")

            if matched_theme not in commands_mapping:
                new_sound_path = search_and_download_sound(matched_theme)
                if new_sound_path:
                    commands_mapping[matched_theme] = new_sound_path
                    with open(COMMANDS_JSON, "w") as file:
                        json.dump(commands_mapping, file, indent=4)
                    print("New sound added to the commands list.")

            audio_clip_path = commands_mapping.get(matched_theme)
            if audio_clip_path:
                pygame.mixer.init()
                try:
                    pygame.mixer.music.load(audio_clip_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pass
                except pygame.error:
                    print(f"No audio file found for theme: {matched_theme}")

        except sr.UnknownValueError:
            print("Sorry, couldn't understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

def main():
    while True:
        listen_and_play_audio()

if __name__ == "__main__":
    main()

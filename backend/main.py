import os

import flask
import requests
import pandas as pd
import hashlib
from google.cloud import secretmanager
from google.cloud import bigquery
from google.cloud import storage
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.cloud import texttospeech
from datetime import datetime
from flask import Flask, request
import datetime
from google import genai
import meteoswiss_utils

app = Flask(__name__)

# Google authentication to run app locally (before deploying)
KEY_PATH = "./caa26project-6962c0d16621.json"
if os.path.isfile(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH

# BigQuery client
PROJECT_ID = "caa26project"
client = bigquery.Client(project=PROJECT_ID)
dataset_ref = bigquery.DatasetReference(project=PROJECT_ID, dataset_id="IoT_Project_dataset")
dataset = client.get_dataset(dataset_ref)

# Google Cloud Storage client
BUCKET_NAME = "caa-proj-bucket"
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# Google Speech-to-Text client
speech_client = SpeechClient()
speech_config = cloud_speech.RecognitionConfig(auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                                               language_codes=["en-US"], model="short")

# Google Text-to-Speech client
tts_client = texttospeech.TextToSpeechClient()


# API keys and passwords in Google Secret Manager
def access_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """
    As in my assignment 2 submission, this was taken from Google Cloud API docs. This serves the same purpose as before:
    allowing me to push this code to GitHub, even on an open repo, without worrying about leaked keys / passwords.
    :param project_id: Google Cloud Project ID for the secret being accessed.
    :param secret_id: Secret ID (or name), defined on creation.
    :param version_id: Version ID, usually latest.
    :return: API key / password as a string literal.
    """
    secret_client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    secret_response = secret_client.access_secret_version(request={"name": secret_name})
    payload = secret_response.payload.data.decode("UTF-8")
    return payload


# Abstracting backend password
BACKEND_PW = access_secret(PROJECT_ID, "backend_pw", "latest")
GEMINI_KEY = access_secret(PROJECT_ID, "gemini_key", "latest")
OWM_KEY = access_secret(PROJECT_ID, "openweather_api_key", "latest")

# Abstracting city:
CITY = "Lausanne"

# Google GenAI client
genai_client = genai.Client(api_key=GEMINI_KEY)

# Re-using the code from Lab 4
query_str = f"SELECT * FROM `{PROJECT_ID}.IoT_Project_dataset.weather-records` LIMIT 10"
query_job = client.query(query_str)
df = query_job.to_dataframe()


@app.route('/ask', methods=['POST'])
def get_speech_2_text():
    """
    Converts raw byte stream to WAV audio, gets transcription via Speech2Text API, and handles GenAI response.
    :return: GenAI response text.
    """
    # TODO: Add GenAI prompt engineering in separate function.
    if request.args.get("backend_pw", str) != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    data = request.get_data()
    # Initial idea was to name audio by the time of recording to assemble small chunks, but I'm giving up on it for now
    # rn = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    with open("audio.wav", "wb") as au:
        au.write(data)
        au.close()
    # These following lines are for debugging purposes (to check that my audio sent properly).
    blob = bucket.blob("audio.wav")
    blob.upload_from_filename("audio.wav")
    # Getting speech transcription
    speech_request = cloud_speech.RecognizeRequest(recognizer=f"projects/{PROJECT_ID}/locations/global/recognizers/_",
                                                   config=speech_config, content=data)
    response = speech_client.recognize(speech_request)
    most_likely = response.results[0].alternatives[0].transcript
    return {"status": "success", "data": most_likely}


@app.route('/answer', methods=['POST'])
def get_genai_answer():
    if request.get_json(force=True)["backend_pw"] != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    question_content = request.get_json(force=True)['data']
    genai_response = genai_client.models.generate_content(model="gemini-2.5-flash",
                                                          contents=build_prompt(question_content))
    return {"stauts": "success", "data": genai_response.text}


@app.route('/talk', methods=['POST'])
def get_text_2_speech():
    if request.get_json(force=True)["backend_pw"] != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    text_content = request.get_json(force=True)['data']
    synthesis_input = texttospeech.SynthesisInput(text=text_content, prompt="Speak at a moderately fast pace.")
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name="Gacrux", model_name="gemini-2.5-flash-tts")
    # LINEAR16 instead of MP3 so I can get a WAV file
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open("response.wav", "wb") as w:
        w.write(response.audio_content)
        print("Done!")
        w.close()
    return flask.send_file(open("response.wav", "rb"), mimetype="audio/wav")


@app.route('/bigquery', methods=['GET', 'POST'])
def connect_to_bigquery():
    """
    Handles communication with BigQuery.
    :return: Status of the request + data sent.
    """
    # TODO: For now, GET returns outdoor weather data => change so GET returns historical data
    # TODO: Update queries to be easily re-deployed!
    if request.method == 'POST':
        if request.get_json(force=True)["backend_pw"] != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
            raise Exception("Incorrect Password!")
        data = request.get_json(force=True)["values"]
        outdoor_weather = get_outdoor_weather()
        data["outdoor_temp"] = outdoor_weather["outdoor_temp"]
        data["outdoor_humidity"] = outdoor_weather["outdoor_humidity"]
        data["outdoor_weather"] = outdoor_weather["outdoor_weather"]
        pollen_data = meteoswiss_utils.get_pollen_concentration()
        for k in pollen_data.keys():
            new_key = k.lower().replace(" ", "_")
            data[new_key] = pollen_data[k]['value']
        q = f"""INSERT INTO `{PROJECT_ID}.IoT_Project_dataset.weather-records`"""
        names = """"""
        values = """"""
        for k, v in data.items():
            names += f"""{k},"""
            if df.dtypes[k] == float:
                values += f"""{v},"""
            else:
                values += f"""'{v}',"""
        names = names[:-1]
        values = values[:-1]
        q = q + f""" ({names})""" + f""" VALUES({values})"""
        query_job = client.query(q)
        print(query_job.result())
        return {"status": "success", "data": data}
    if request.method == 'GET':
        if request.args.get("backend_pw", str) != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
            raise Exception("Incorrect Password!")
        data = {}
        date_asked = request.args.get("date", datetime.datetime.today().strftime('%Y-%m-%d'), str)
        q = f"""SELECT `date`, `indoor_temp`, `indoor_humidity`, `indoor_co2`, `outdoor_temp`, `outdoor_humidity`,
         `indoor_pressure` FROM `{PROJECT_ID}.IoT_Project_dataset.weather-records` 
         WHERE `date` >= cast('{date_asked}' as date)"""
        data = client.query(q).to_dataframe().to_dict()
        return {"status": "success", "data": data}
    return {"status": "failed"}


@app.route("/outdoors", methods=['GET'])
def send_outdoor_weather():
    """
    Function to get and return outdoor weather information.
    :return: Dictionary with various weather information..
    """
    if request.args.get("backend_pw", str) != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    data = {}
    outdoor_weather = get_outdoor_weather()
    data["outdoor_temp"] = outdoor_weather["outdoor_temp"]
    data["outdoor_humidity"] = outdoor_weather["outdoor_humidity"]
    data["outdoor_weather"] = outdoor_weather["outdoor_weather"]
    data["weather_icon"] = outdoor_weather["weather_icon"]
    weather_forecast = meteoswiss_utils.get_daily_forecast_ogd()
    data["min_temp"] = weather_forecast["min_temp"]
    data["max_temp"] = weather_forecast["max_temp"]
    return {"status": "success", "data": data}


@app.route("/pollen", methods=['GET'])
def send_pollen_concentration():
    if request.args.get("backend_pw", str) != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    data = meteoswiss_utils.get_pollen_concentration()
    return {"status": "success", "data": data}


@app.route('/forecast/week', methods=['GET'])
def send_forecast_week():
    """
    :return: Forecasted information.
    """
    if request.args.get("backend_pw", str) != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    forecast_data = get_forecast_from_owm()
    data = {}
    for d in forecast_data.keys():
        # Meteorologically impossible values
        max_temp = -100
        min_temp = 100
        for t in forecast_data[d].keys():
            hourly_max = forecast_data[d][t]['main']['temp_max']
            max_temp = hourly_max if hourly_max > max_temp else max_temp
            hourly_min = forecast_data[d][t]['main']['temp_min']
            min_temp = hourly_min if hourly_min < min_temp else min_temp
        first_hour_available = list(forecast_data[d].keys())[0]
        day_of_week = datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%A')
        # calendar.day_name[datetime.datetime.strptime(d, '%Y-%m-%d').weekday()]
        day_of_week_short = datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%a')
        # calendar.day_abbr[datetime.datetime.strptime(d, '%Y-%m-%d').weekday()]
        data[d] = {'weekday': day_of_week, 'weekday_short': day_of_week_short,
                   'max_temp': max_temp, 'min_temp': min_temp,
                   'weather_description': forecast_data[d][first_hour_available]['weather'][0]['description'],
                   'weather_icon': forecast_data[d][first_hour_available]['weather'][0]['icon'][:-1]}
    return {"status": "success", "data": data}


@app.route('/forecast/day', methods=['GET'])
def send_forecast_day():
    """
    Detailed hourly forecast for the day.
    :return:
    """
    if request.args.get("backend_pw", str) != hashlib.sha256(BACKEND_PW.encode()).hexdigest():
        raise Exception("Incorrect Password!")
    forecast_data = get_forecast_from_owm()
    data = forecast_data[request.args.get("date", str)]
    return {"status": "success", "data": data}


def build_prompt(question: str):
    return f"""You are a home weather station assistant.
    ## Task:
    Answer the following question: '{question}'
    If the question requires a location and none is provided, assume the location is {CITY}.
    
    ## Additional information:
    The forecast for this week is {get_forecast_from_owm()}.
    
    ## Constraints:
    Keep your response under 25 words. Highlight critical information first.
    
    ## Format:
    Do not use any ASCII-extended characters in your response. For example, if you need to say °C, replace it with 'degrees'.
    """


def get_outdoor_weather():
    data = {}
    # TODO: Get city from IP
    url = f'http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_KEY}&units=metric'
    response = requests.get(url)
    temp = round(response.json()['main']['temp'])
    humidity = round(response.json()['main']['humidity'])
    weather = response.json()['weather'][0]['description']
    weather_icon = response.json()['weather'][0]['icon'][:-1]
    data["outdoor_temp"] = temp
    data["outdoor_humidity"] = humidity
    data["outdoor_weather"] = weather
    data["weather_icon"] = weather_icon
    return data


def get_forecast_from_owm():
    """
    Polls openweathermap for 5-day/3-hour forecast data.
    :return: A dictionary grouping the response by day, then hour, of the main and weather information.
    """
    data = {}
    # TODO: Get city from IP
    url = f'http://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={OWM_KEY}&units=metric'
    response = requests.get(url)
    for e in response.json()['list']:
        text_date = datetime.datetime.utcfromtimestamp(int(e["dt"])).strftime('%Y-%m-%d')
        text_hour = datetime.datetime.utcfromtimestamp(int(e["dt"])).strftime('%H:%M:%S')
        if text_date not in data.keys():
            data[text_date] = {text_hour: {'main': e['main'], 'weather': e['weather']}}
        else:
            data[text_date][text_hour] = {'main': e['main'], 'weather': e['weather']}
    return data


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

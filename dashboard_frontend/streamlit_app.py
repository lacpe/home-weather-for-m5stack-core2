import streamlit as st
import requests
import datetime
import os
from google.cloud import secretmanager
import pandas as pd
import hashlib

# Google authentication to run app locally (before deploying)
KEY_PATH = "./caa26project-6962c0d16621.json"
if os.path.isfile(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH

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


# Constants, keys, endpoints
PROJECT_ID = "caa26project"
BACKEND_ENDPOINT = "https://caa26-project-backend-211229885401.europe-west6.run.app"
BACKEND_PW = hashlib.sha256(access_secret(PROJECT_ID, "backend_pw", "latest").encode()).hexdigest()

def main():
    initialize_keys()
    # Leaving title in because I think it's cute but objectively doesn't look great
    # st.title("Loïc\'s M5 meteo app")
    # Section 1: Current weather data
    st.header("Current conditions")
    data = get_weekly_forecast()
    print(data)
    today = get_outdoor_weather()
    sum_col1, sum_col2 = st.columns(spec=2, gap="xsmall", vertical_alignment="top", border=True)
    with sum_col1:
        with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="bottom", width=200):
            st.markdown("**Lausanne**", width="stretch")
            st.text(datetime.datetime.today().strftime('%a %d %B %Y'))
        with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="top", width=300):
            outdoor_weather = get_outdoor_weather()
            st.metric("Temperature", f"{int(outdoor_weather['outdoor_temp'])}°C")
            st.metric("Humidity", f"{int(outdoor_weather['outdoor_humidity'])}%")
            st.image(f"icons/animated/{today['weather_icon']}.svg", width=100)
    with sum_col2:
        # This used to be section 3, but actually fits much better at the top of the app
        home_df = pd.DataFrame(get_bigquery_info(5))
        home_df['date'] = home_df['date'].apply(lambda x: datetime.datetime.strptime(x, '%a, %d %B %Y %H:%M:%S %Z')
                                                .strftime('%Y-%m-%d'))
        home_df = home_df.sort_values(by="date")
        home_date = datetime.datetime.strptime(home_df['date'].iloc[-1], '%Y-%m-%d').strftime('%a, %d %B %Y')
        home_co2 = home_df['indoor_co2'].iloc[-1]
        home_humidity = home_df['indoor_humidity'].iloc[-1]
        home_temp = home_df['indoor_temp'].iloc[-1]
        st.markdown(f"**Indoor measurements:** {home_date}")
        with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="top", width=300):
            st.metric("Temperature", f"{int(home_temp)}°C")
            st.metric("Humidity", f"{int(home_humidity)}%")
            st.metric("CO2 (in PPM)", f"{int(home_co2)}")
    st.text(f"{today['outdoor_weather'].capitalize()} with a max temperature of {int(today['max_temp'])}°C.")
    st.divider()
    # Section 2: Forecast for the upcoming week
    st.header("Forecast")
    keys = list(data.keys())
    keys.sort()
    week_col1, week_col2, week_col3, week_col4 = st.columns(spec=4, gap="xsmall", vertical_alignment="top", border=True)
    week_columns = [week_col1, week_col2, week_col3, week_col4]
    for i in range(0, len(week_columns)):
        k = i + 1
        day = data[keys[k]]
        with week_columns[i]:
            st.text(f"{day['weekday_short']} {keys[k][-2:]}")
            with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="top"):
                st.text(f"{int(day['max_temp'])}°C")
                st.image(f"icons/animated/{day['weather_icon']}.svg", width=30)
    st.divider()
    # Section 3: Historical data
    # TODO: Use session state to choose the time duration and data type
    st.header("Past data")
    with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="bottom"):
        st.selectbox(label="Time span", options=['1 week', '2 weeks', '1 month', '1 year'], key="time_span",
                     on_change=reload_time_span)
        st.selectbox(label="Data shown", options=['Temperature', 'Humidity', 'CO2', 'Pressure'], key="data_shown_label",
                     on_change=reload_data_shown)
    st.line_chart(data=st.session_state['historical_data'], y=st.session_state['data_shown'],
                  color=st.session_state['color_shown'])


def reload_data_shown():
    if st.session_state['data_shown_label'] == 'Temperature':
        st.session_state['data_shown'] = ['indoor_temp', 'outdoor_temp']
        st.session_state['color_shown'] = ['#ffd447', '#ff3322']
    if st.session_state['data_shown_label'] == 'Humidity':
        st.session_state['data_shown'] = ['indoor_humidity', 'outdoor_humidity']
        st.session_state['color_shown'] = ['#700353', '#2233ff']
    if st.session_state['data_shown_label'] == 'CO2':
        st.session_state['data_shown'] = ['indoor_co2']
        st.session_state['color_shown'] = ['#ffd447']
    if st.session_state['data_shown_label'] == 'Pressure':
        st.session_state['data_shown'] = ['indoor_pressure']
        st.session_state['color_shown'] = ['#2233ff']
    print(st.session_state['data_shown'])


def reload_time_span():
    time_span_days = {'1 week': 7, '2 weeks': 14, '1 month': 30, '1 year': 365}
    past_data = pd.DataFrame(get_bigquery_info(time_span_days[st.session_state['time_span']], datetime.datetime.today()
                                               .strftime('%Y-%m-%d %H')))
    past_data['date'] = past_data['date'].apply(lambda x: datetime.datetime.strptime(x, '%a, %d %b %Y %H:%M:%S %Z')
                                                .strftime('%Y-%m-%d'))
    past_data = past_data.groupby('date')[['indoor_temp', 'indoor_humidity', 'outdoor_temp', 'outdoor_humidity',
                                           'indoor_co2', 'indoor_pressure']].mean()
    past_data.sort_index(inplace=True)
    st.session_state['historical_data'] = past_data


def initialize_keys():
    if 'time_span' not in st.session_state.keys():
        st.session_state['time_span'] = "1 week"
        reload_time_span()
    if 'historical_data' not in st.session_state.keys():
        st.session_state['historical_data'] = pd.DataFrame.empty
    if 'data_shown' not in st.session_state.keys():
        st.session_state['data_shown'] = ['indoor_temp', 'outdoor_temp']
    if 'data_shown_label' not in st.session_state.keys():
        st.session_state['data_shown_label'] = ""
    if 'color_shown' not in st.session_state.keys():
        st.session_state['color_shown'] = ['#ffd447', '#ff3322']


def get_daily_forecast():
    url = f"{BACKEND_ENDPOINT}/forecast/day?date={datetime.datetime.today().strftime('%Y-%m-%d')}" \
          f"&backend_pw={BACKEND_PW}"

    response = requests.get(url)
    data = response.json()['data']
    return data


def get_weekly_forecast():
    url = f"{BACKEND_ENDPOINT}/forecast/week?backend_pw={BACKEND_PW}"
    response = requests.get(url)
    data = response.json()['data']
    return data


def get_outdoor_weather():
    url = f"{BACKEND_ENDPOINT}/outdoors?backend_pw={BACKEND_PW}"
    response = requests.get(url)
    data = response.json()['data']
    return data


@st.cache_data
def get_bigquery_info(date_diff: int = 0, date_of_asking: str = ""):
    """
    :param date_diff: How far back to look.
    :param date_of_asking: Not here to actually be used, but helps cache data that was loaded recently.
    :return: A dataframe containing all measurements since data was requested.
    """
    if date_diff != 0:
        start_date = (datetime.datetime.today() - datetime.timedelta(days=date_diff)).strftime('%Y-%m-%d')
    else:
        start_date = datetime.datetime.today().strftime('%Y-%m-%d')
    url = f"{BACKEND_ENDPOINT}/bigquery?backend_pw={BACKEND_PW}&date={start_date}"
    response = requests.get(url)
    data = response.json()['data']
    return data


if __name__ == '__main__':
    main()

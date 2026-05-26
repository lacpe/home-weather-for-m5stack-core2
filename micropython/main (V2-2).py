import gc
from numbers import Number
import math
from m5stack import *
from m5stack_ui import *
from uiflow import *
import urequests
import time
import json
import MicrophonePDM as MIC
import network
import ntptime
import unit

# Declaring hardware
screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0x222222)
env3_1 = unit.get(unit.ENV3, unit.PORTA)
pir_1 = unit.get(unit.PIR, unit.PORTB)
tvoc_0 = unit.get(unit.TVOC, (14,13))

# Constants
BACKEND_LINK = 'YOUR BACKEND LINK HERE'
BACKEND_PW = 'YOUR BACKEND PASSWORD HERE'

# Declaring variables
pollen_num = None
active_page = 0
is_recording = False
current_pollen = None
pollen_data = None
pollen_dict = None
current_hour = None
current_minute = None
record_start_time = None
slider_value = None
last_time_shown = None
wlan = None
speaker_volume = 6
duration_ms = 3000

# Initiating timer here since I need duration_ms to be defined
timerSch.setTimer('timer1', duration_ms*2, 0x01)

# Stuff that never disappears from page to page
menu_bar = M5Bar(x=0, y=0, w=320, h=20, min=0, max=100, bg_c=0x111111, color=0x333333, parent=None)
title_label = M5Label('Welcome', x=14, y=2, color=0xffffff, font=FONT_MONT_14, parent=None)
column = M5Label(':', x=160, y=1, color=0xffffff, font=FONT_MONT_14, parent=None)
minute_display = M5Label('58', x=165, y=1, color=0xffffff, font=FONT_MONT_14, parent=None)
hour_display = M5Label('13', x=145, y=1, color=0xffffff, font=FONT_MONT_14, parent=None)
wifi_status_image = M5Img("res/wifi_off.png", x=295, y=1, parent=None)

# Page 0
page_0_widgets = []
# Section labels
indoor_temp_label = M5Label('Indoors', x=10, y=30, color=0xffd447, font=FONT_MONT_18, parent=None)
page_0_widgets.append(indoor_temp_label)
outdoor_temp_label = M5Label('Outdoors', x=110, y=30, color=0xff3322, font=FONT_MONT_18, parent=None)
page_0_widgets.append(outdoor_temp_label)
forecast_label = M5Label('Forecast:', x=210, y=30, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(forecast_label)
day_1_name = M5Label('Mon', x=210, y=50, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(day_1_name)
day_2_name = M5Label('Tue', x=210, y=70, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(day_2_name)
day_3_name = M5Label('Wed', x=210, y=90, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(day_3_name)
weather_label = M5Label('Expected weather:', x=10, y=135, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(weather_label)
# Measurements
indoor_temp_display = M5Label('27', x=10, y=50, color=0xffd447, font=FONT_MONT_38, parent=None)
page_0_widgets.append(indoor_temp_display)
indoor_humidity_display = M5Label('65', x=10, y=85, color=0xffd447, font=FONT_MONT_38, parent=None)
page_0_widgets.append(indoor_humidity_display)
outdoor_temp_display = M5Label('31', x=110, y=50, color=0xff3322, font=FONT_MONT_38, parent=None)
page_0_widgets.append(outdoor_temp_display)
outdoor_humidity_display = M5Label('45', x=110, y=85, color=0xff3322, font=FONT_MONT_38, parent=None)
page_0_widgets.append(outdoor_humidity_display)
day_1_temp = M5Label('20', x=260, y=50, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(day_1_temp)
day_2_temp = M5Label('20', x=260, y=70, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(day_2_temp)
day_3_temp = M5Label('20', x=260, y=90, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(day_3_temp)
day_1_icon = M5Img("res/01.png", x=290, y=53, parent=None)
page_0_widgets.append(day_1_icon)
day_2_icon = M5Img("res/01.png", x=290, y=73, parent=None)
page_0_widgets.append(day_2_icon)
day_3_icon = M5Img("res/01.png", x=290, y=93, parent=None)
page_0_widgets.append(day_3_icon)
weather_display = M5Label('Slight clouds', x=10, y=160, color=0xffffff, font=FONT_MONT_18, parent=None)
page_0_widgets.append(weather_display)
# Measurement units
celsius_1 = M5Label('C', x=60, y=50, color=0xffd447, font=FONT_MONT_38, parent=None)
page_0_widgets.append(celsius_1)
celsius_2 = M5Label('C', x=160, y=50, color=0xff3322, font=FONT_MONT_38, parent=None)
page_0_widgets.append(celsius_2)
percent_1 = M5Label('%', x=60, y=85, color=0xffd447, font=FONT_MONT_38, parent=None)
page_0_widgets.append(percent_1)
percent_2 = M5Label('%', x=160, y=85, color=0xff3322, font=FONT_MONT_38, parent=None)
page_0_widgets.append(percent_2)
# Buttons
talk_button = M5Btn(text='Talk', x=110, y=190, w=100, h=40, bg_c=0x111111, text_c=0xffffff, font=FONT_MONT_14, parent=None)
page_0_widgets.append(talk_button)
# Other graphical elements
line_1 = M5Line(x1=100, y1=30, x2=100, y2=120, color=0xffffff, width=1, parent=None)
line_2 = M5Line(x1=200, y1=30, x2=200, y2=120, color=0xffffff, width=1, parent=None)
line_3 = M5Line(x1=10, y1=130, x2=310, y2=130, color=0xffffff, width=1, parent=None)

# Page 1
page_1_widgets = []
# Section labels
indoor_co2_label = M5Label('Indoor CO2', x=10, y=30, color=0xffd447, font=FONT_MONT_18, parent=None)
page_1_widgets.append(indoor_co2_label)
pollen_label = M5Label('Pollen', x=130, y=30, color=0xb84300, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_label)
indoor_pressure_label = M5Label('Indoor pressure', x=10, y=170, color=0xffffff, font=FONT_MONT_18, parent=None)
page_1_widgets.append(indoor_pressure_label)
# Measurements
indoor_co2_display = M5Label('400', x=10, y=50, color=0xffd447, font=FONT_MONT_38, parent=None)
page_1_widgets.append(indoor_co2_display)
co2_status_display = M5Label('OK!', x=10, y=120, color=0x33ff22, font=FONT_MONT_38, parent=None)
page_1_widgets.append(co2_status_display)
pollen_type_display = M5Label('Alder', x=190, y=50, color=0xb84300, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_type_display)
pollen_con_display = M5Label('400', x=190, y=70, color=0xb84300, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_con_display)
pollen_level_display = M5Label('low', x=190, y=90, color=0xb84300, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_level_display)
indoor_pressure_display = M5Label('900', x=10, y=190, color=0xffffff, font=FONT_MONT_38, parent=None)
page_1_widgets.append(indoor_pressure_display)
# Measurement units or labels
ppm_label = M5Label('PPM', x=10, y=80, color=0xffd447, font=FONT_MONT_38, parent=None)
page_1_widgets.append(ppm_label)
pollen_type_label = M5Label('Type:', x=130, y=50, color=0xffffff, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_type_label)
pollen_con_label = M5Label('Con:', x=130, y=70, color=0xffffff, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_con_label)
pollen_level_label = M5Label('Level:', x=130, y=90, color=0xffffff, font=FONT_MONT_18, parent=None)
page_1_widgets.append(pollen_level_label)
hpa_label = M5Label('hPa', x=120, y=190, color=0xffffff, font=FONT_MONT_38, parent=None)
page_1_widgets.append(hpa_label)
# Buttons
pollen_prev_button = M5Btn(text='Prev.', x=130, y=120, w=80, h=30, bg_c=0x111111, text_c=0xffffff, font=FONT_MONT_14, parent=None)
page_1_widgets.append(pollen_prev_button)
pollen_next_button = M5Btn(text='Next', x=230, y=120, w=80, h=30, bg_c=0x111111, text_c=0xffffff, font=FONT_MONT_14, parent=None)
page_1_widgets.append(pollen_next_button)

# Page 2
page_2_widgets = []
# Switches and buttons
blink_switch = M5Switch(x=10, y=30, w=50, h=25, bg_c=0x111111, color=0x2233ff, parent=None)
page_2_widgets.append(blink_switch)
send_data_switch = M5Switch(x=10, y=70, w=50, h=25, bg_c=0x111111, color=0x2233ff, parent=None)
page_2_widgets.append(send_data_switch)
send_button = M5Btn(text='Send data now', x=150, y=110, w=150, h=30, bg_c=0x111111, text_c=0xffffff, font=FONT_MONT_14, parent=None)
page_2_widgets.append(send_button)
volume_slider = M5Slider(x=150, y=160, w=150, h=12, min=0, max=6, bg_c=0x111111, color=0xffffff, parent=None)
page_2_widgets.append(volume_slider)
wifi_button = M5Btn(text='Wi-Fi', x=10, y=190, w=80, h=30, bg_c=0x111111, text_c=0xffffff, font=FONT_MONT_14, parent=None)
page_2_widgets.append(wifi_button)
# Legends
blink_label = M5Label('LED blink', x=70, y=32, color=0xffffff, font=FONT_MONT_22, parent=None)
page_2_widgets.append(blink_label)
send_data_label = M5Label('Activate data sending', x=70, y=72, color=0xffffff, font=FONT_MONT_22, parent=None)
page_2_widgets.append(send_data_label)
test_label = M5Label('For testing:', x=10, y=110, color=0xffffff, font=FONT_MONT_22, parent=None)
page_2_widgets.append(test_label)
volume_label = M5Label('Volume:', x=10, y=155, color=0xffffff, font=FONT_MONT_22, parent=None)
page_2_widgets.append(volume_label)
ssid_label = M5Label('SSID:', x=100, y=195, color=0xffffff, font=FONT_MONT_22, parent=None)
page_2_widgets.append(ssid_label)
# Other graphical elements
ssid_display = M5Label('Z-Flip5', x=165, y=195, color=0xffffff, font=FONT_MONT_14, parent=None)
page_2_widgets.append(ssid_display)


# Updates indoor indicators
def update_indoor_indicators():
  hour = str(ntp.hour())
  if len(hour) == 1:
    hour = "0" + hour
  minute = str(ntp.minute())
  if len(minute) == 1:
    minute = "0" + minute
  hour_display.set_text(hour)
  minute_display.set_text(minute)
  indoor_temp_display.set_text(str(int(env3_1.temperature)))
  indoor_humidity_display.set_text(str(int(env3_1.humidity)))
  co2_level = round(tvoc_0.eCO2)
  indoor_co2_display.set_text(str(co2_level))
  if co2_level > 1000:
    co2_status_display.set_text('NOK!')
    co2_status_display.set_text_color(0xff3322)
  else:
    co2_status_display.set_text('OK!')
    co2_status_display.set_text_color(0x33ff22)
  indoor_pressure_display.set_text(str(int(env3_1.pressure)))


# Updates pollen display based on current information
def show_pollen():
  global pollen_num, current_pollen, pollen_data, pollen_dict
  pollen_type_display.set_text(str(current_pollen))
  pollen_con_display.set_text(str(round(pollen_data['data'][current_pollen]['value'])))
  pollen_level = str(pollen_data['data'][current_pollen]['level'])
  pollen_level = pollen_level[0].upper() + pollen_level[1:]
  pollen_level_display.set_text(pollen_level)


# Updates outdoor indicators
def update_outdoor_indicators():
  try:
    req = urequests.request(method='GET', url=BACKEND_LINK+'/outdoors?backend_pw='+BACKEND_PW,
                            headers={'content-type': 'application/json'})
    if req.status_code == 200:
      outdoor_weather_data = json.loads(req.text)
      outdoor_temp_display.set_text(str(outdoor_weather_data['data']['outdoor_temp']))
      outdoor_humidity_display.set_text(str(outdoor_weather_data['data']['outdoor_humidity']))
      weather_desc = str(outdoor_weather_data['data']['outdoor_weather'])
      weather_desc = weather_desc[0].upper() + weather_desc[1:]
      weather_display.set_text(weather_desc)
      rgb.setColorAll(0xffffff)
      blink()
    else:
      print(req.status_code, req.text)
    gc.collect()
    req.close()
  except Exception as e:
    rgb.setColorAll(0xff0000)
    blink()
    print('Error updating outdoors indicators', e)


# Gets forecast data from cloud server
def update_forecast():
  try:
    req = urequests.request(method='GET', url=BACKEND_LINK+'/forecast/week?backend_pw='+BACKEND_PW,
                            headers={'content-type': 'application/json'})
    if req.status_code == 200:
      forecast_data = json.loads(req.text)['data']
      keys = list(forecast_data.keys())
      keys.sort()
      day_1_name.set_text(forecast_data[keys[0]]['weekday_short'])
      day_1_temp.set_text(str(int(forecast_data[keys[0]]['max_temp'])))
      day_1_icon.set_img_src("res/"+forecast_data[keys[0]]['weather_icon']+".png")
      day_2_name.set_text(forecast_data[keys[1]]['weekday_short'])
      day_2_temp.set_text(str(int(forecast_data[keys[1]]['max_temp'])))
      day_2_icon.set_img_src("res/"+forecast_data[keys[1]]['weather_icon']+".png")
      day_3_name.set_text(forecast_data[keys[2]]['weekday_short'])
      day_3_temp.set_text(str(int(forecast_data[keys[2]]['max_temp'])))
      day_3_icon.set_img_src("res/"+forecast_data[keys[2]]['weather_icon']+".png")
    else:
      print(req.status_code, req.text)
    gc.collect()
    req.close()
  except Exception as e:
    rgb.setColorAll(0xff0000)
    blink()
    print('Error updating forecast indicators:', e)


# Gets pollent data from server
def get_pollen():
  global pollen_data
  try:
    req = urequests.request(method='GET', url=BACKEND_LINK+'//pollen?backend_pw='+BACKEND_PW,
                            headers={'content-type': 'application/json'})
    if (req.status_code) == 200:
      pollen_data = json.loads(req.text)
    else:
      print(req.status_code, req.text)
    rgb.setColorAll(0xffffff)
    blink()
    gc.collect()
    req.close()
  except Exception as e:
    rgb.setColorAll(0xff0000)
    blink()
    print('Error getting pollen data:', e)


# Turns the LED on and off a couple times
def blink():
  if blink_switch.get_state():
    wait_ms(100)
    rgb.setBrightness(10)
    wait_ms(100)
    rgb.setBrightness(0)
    wait_ms(100)
    rgb.setBrightness(10)
    wait_ms(100)
    rgb.setBrightness(0)


# Uploads data to Google BigQuery
def send_data():
  try:
    req = urequests.request(method='POST', url=BACKEND_LINK,
                            json={'backend_pw': BACKEND_PW,
                                  'values': ({'date': ntp.formatDate('-'),
                                              'time': ntp.formatTime(':'),
                                              'indoor_temp': env3_1.temperature,
                                              'indoor_humidity': env3_1.humidity,
                                              'indoor_pressure': env3_1.pressure,
                                              'indoor_co2': tvoc_0.eCO2})},
                            headers={'content-type': 'application/json'})
    if req.status_code == 200:
      rgb.setColorAll(0x33ccff)
      blink()
    else:
      print(req.status_code, req.text)
    gc.collect()
    req.close()
  except Exception as e:
    rgb.setColorAll(0xff0000)
    blink()
    print('Error sending data to bigquery:', e)


# Start the recording
def talk_button_pressed():
  global is_recording, duration_ms
  if is_recording:
    return
  gc.collect()
  MIC.begin(pin_ws=0, pin_data=34, sample_rate_hz=16000, buffer_length_ms=1000, block_length_ms=100)
  is_recording = True
  # Waiting just to give time for the MIC to have actually initialized before we start recording
  wait_ms(100)
  MIC.recordStart(open('res/audio.wav', 'w'), duration_ms)
  timerSch.run('timer1', duration_ms*2, 0x01)
  pass
talk_button.pressed(talk_button_pressed)


@timerSch.event('timer1')
def ttimer1():
  """
  We could technically add a layer of abstraction with a handle_recording function, but I feel like that would be a
  waste of time.
  """
  global is_recording, duration_ms, speaker_volume
  try:
    MIC.recordStop()
  except Exception as e:
    print("Mic already stopped!")
  print("Waiting to make sure")
  MIC.deinit(100)
  wait_ms(500)
  gc.collect()
  print("Transcribing audio")
  text = transcribe_audio()
  if text == "":
    return
  print("Sending question to GenAI")
  genai_text = genai_answer(text)
  if genai_text == "":
    return
  print("Sending GenAI response to TTS")
  text_to_speech(genai_text)
  gc.collect()
  print("Playing file")
  speaker.playWAV('res/response.wav', volume=speaker_volume)
  is_recording = False
  pass


def get_quick_tip():
  global is_recording, speaker_volume
  if is_recording:
    return
  genai_text = genai_answer("Any quick tips regarding the weather right now?")
  text_to_speech(genai_text)
  speaker.playWAV('res/response.wav', volume=speaker_volume)
  pass


# Send recording to Google Cloud
def transcribe_audio():
  try:
    with open('res/audio.wav', 'rb') as w:
      data_to_send = w.read()
    print("Sending recording!")
    stt = ""
    req = urequests.request(method='POST', url=BACKEND_LINK+'/ask?backend_pw='+BACKEND_PW, data=data_to_send,
                            headers={'content-type': 'audio/wav'})
    print("Recording sent!")
    if req.status_code == 200:
      response = json.loads((req.text))
      stt = response['data']
    else:
      print(req.status_code, req.text)
    gc.collect()
    req.close()
    return stt
  except Exception as e:
    print('Error transcribing text:', e)


# Gets GenAI response from Cloud Server
def genai_answer(text):
  try:
    req = urequests.request(method='POST', url=BACKEND_LINK+'/answer', json={'backend_pw': BACKEND_PW, 'data': text},
                            headers={'content-type': 'application/json'})
    genai_text = ""
    if req.status_code == 200:
      response = json.loads((req.text))
      genai_text = response['data']
    else:
      print(req.status_code, req.text)
    gc.collect()
    req.close()
    return genai_text
  except Exception as e:
    print('Error getting GenAI answer:', e)


# Gets TTS thing from Cloud Server
def text_to_speech(text):
  try:
    req = urequests.request(method='POST', url=BACKEND_LINK+'/talk', json={'backend_pw': BACKEND_PW, 'data': text},
                            headers={'content-type': 'application/json'})
    if req.status_code == 200:
      print("Receiving audio!")
      with open("res/response.wav", "wb") as r:
        r.write(req.content)
        r.close()
    else:
      print(req.status_code, req.text)
    gc.collect()
    req.close()
  except Exception as e:
    print('Error converting text to speech:', e)


# Adjusts volume when volume slider is changed
def volume_slider_changed(slider_value):
  global speaker_volume
  speaker_volume = slider_value
  pass
volume_slider.changed(volume_slider_changed)


# Describe this function...
def load_active_page():
  global active_page
  # Displaying page 0 specific widgets
  if active_page == 0:
    menu_bar.set_value(30)
    title_label.set_text('Welcome')
    for w in page_0_widgets:
      w.set_hidden(False)
    for w in page_1_widgets:
      w.set_hidden(True)
    for w in page_2_widgets:
      w.set_hidden(True)
    line_1.set_points(100, 30, 100, 120)
    line_1.set_hidden(False)
    line_2.set_points(200, 30, 200, 120)
    line_2.set_hidden(False)
    line_3.set_points(10, 130, 310, 130)
    line_3.set_hidden(False)
  # Displaying page 1 specific widgets
  if active_page == 1:
    menu_bar.set_value(32)
    title_label.set_text('Air quality')
    for w in page_0_widgets:
      w.set_hidden(True)
    for w in page_1_widgets:
      w.set_hidden(False)
    for w in page_2_widgets:
      w.set_hidden(True)
    line_1.set_points(120, 30, 120, 150)
    line_1.set_hidden(False)
    line_2.set_points(10, 160, 310, 160)
    line_2.set_hidden(False)
    line_3.set_hidden(True)
  # Displaying page 2 specific widgets
  if active_page == 2:
    menu_bar.set_value(28)
    title_label.set_text('Settings')
    for w in page_0_widgets:
      w.set_hidden(True)
    for w in page_1_widgets:
      w.set_hidden(True)
    for w in page_2_widgets:
      w.set_hidden(False)
    line_1.set_hidden(True)
    line_2.set_hidden(True)
    line_3.set_hidden(True)


# The next 2 functions handle what happens when the pollen "Prev." and "Next buttons are pressed
def pollen_prev_button_pressed():
  global pollen_num, current_pollen, pollen_dict
  pollen_num = (pollen_num if isinstance(pollen_num, Number) else 0) - 1
  if pollen_num < 0:
    pollen_num = 6
  current_pollen = pollen_dict[str(pollen_num)]
  show_pollen()
  pass
pollen_prev_button.pressed(pollen_prev_button_pressed)


def pollen_next_button_pressed():
  global pollen_num, current_pollen, pollen_dict
  pollen_num = (pollen_num if isinstance(pollen_num, Number) else 0) + 1
  if pollen_num > 6:
    pollen_num = 0
  current_pollen = pollen_dict[str(pollen_num)]
  show_pollen()
  pass
pollen_next_button.pressed(pollen_next_button_pressed)

def send_button_pressed():
  global pollen_num, active_page, current_pollen, pollen_data, pollen_dict, current_hour, current_minute
  send_data()
  pass
send_button.pressed(send_button_pressed)


# These 2 next functions handle the navigation buttons
def buttonA_wasPressed():
  global pollen_num, active_page, current_pollen, pollen_data, pollen_dict, current_hour, current_minute
  active_page = active_page - 1
  if active_page < 0:
    active_page = 0
  load_active_page()
  pass
btnA.wasPressed(buttonA_wasPressed)


def buttonC_wasPressed():
  global pollen_num, active_page, current_pollen, pollen_data, pollen_dict, current_hour, current_minute
  active_page = (active_page if isinstance(active_page, Number) else 0) + 1
  if active_page > 2:
    active_page = 2
  load_active_page()
  pass
btnC.wasPressed(buttonC_wasPressed)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)


# Handles WiFi connection
def connect_wifi():
  global wlan
  connection_attempts = 3
  while wlan.status() != 1010 and connection_attempts > 0:
    rgb.setColorAll(0xff9900)
    blink()
    wlan.connect('SSID 1', 'PW 1')
    wait(5)
    if wlan.status() == 1010:
      wifi_status_image.set_img_src("res/wifi_on.png")
      break
    blink()
    wlan.connect('SSID 2', 'PW 2')
    wait(5)
    if wlan.status() == 1010:
      wifi_status_image.set_img_src("res/wifi_on.png")
      break
    blink()
    wlan.connect('SSID 3', 'PW 3')
    wait(5)
    if wlan.status == 1010:
      wifi_status_image.set_img_src("res/wifi_on.png")
      break
    connection_attempts = connection_attempts - 1
  if wlan.status == 1010:
    wifi_status_image.set_img_src("res/wifi_on.png")
  else:
    wifi_status_image.set_img_src("res/wifi_off.png")
  pass
wifi_button.pressed(connect_wifi)

"""
Below is the main function / section of the code. Normally, this would be wrapped in a main() function, but doing that
breaks everything, I suspect due to how micropython handles global versus local variables, so it'll stay like this for
now.
"""
load_active_page()
send_data_switch.set_on()
blink_switch.set_on()
connect_wifi()
if wlan.status == 1010:
  wifi_status_image.set_img_src("res/wifi_on.png")
pollen_num = 0
pollen_dict = {'0':'Alder','1':'Beech','2':'Birch','3':'Common ash','4':'Grasses','5':'Hazel','6':'Oak'}
current_pollen = pollen_dict[str(pollen_num)]
ntp = ntptime.client(host='de.pool.ntp.org', timezone=2)
current_hour = ntp.hour()
current_minute = ntp.minute()
update_outdoor_indicators()
update_indoor_indicators()
update_forecast()
get_pollen()
show_pollen()
rgb.setColorAll(0x33ff33)
blink()
while True:
  if pir_1.state == 1:
    if ntp.hour != last_time_shown:
      rgb.setColorAll(0x000000)
      blink()
      get_quick_tip()
      last_time_shown = ntp.hour
  if current_hour != (ntp.hour()):
    ntp = ntptime.client(host='de.pool.ntp.org', timezone=2)
    if send_data_switch.get_state():
      send_data()
    update_outdoor_indicators()
    update_forecast()
    get_pollen()
    show_pollen()
    current_hour = ntp.hour()
  if current_minute != (ntp.minute()):
    update_indoor_indicators()
    current_minute = ntp.minute()
  wait_ms(2)

import datetime
import os
import pandas as pd
import requests

# Meteoswiss item & asset tags
item_etags = {}
asset_etags = {}
item_etag = "*"
asset_etag = "*"

def get_daily_forecast_ogd():
    today = datetime.datetime.utcnow().strftime("%Y%m%d")
    print(today)
    # Fetching min and max temperature
    fetch_meteoswiss_ogd_object("ch.meteoschweiz.ogd-local-forecasting", f"{today}-ch",
                                f"vnut12.lssw.{today}0000.tre200dn.csv")
    fetch_meteoswiss_ogd_object("ch.meteoschweiz.ogd-local-forecasting", f"{today}-ch",
                                f"vnut12.lssw.{today}0000.tre200dx.csv")
    min_temp_df = pd.read_csv(f'vnut12.lssw.{today}0000.tre200dn.csv', sep=";")
    max_temp_df = pd.read_csv(f'vnut12.lssw.{today}0000.tre200dx.csv', sep=";")
    min_temp = min_temp_df.loc[(min_temp_df["point_id"] == 270) & (min_temp_df["Date"] == int(f'{today}0000'))]
    min_temp = float(min_temp["tre200dn"].values[0])
    max_temp = max_temp_df.loc[(max_temp_df["point_id"] == 270) & (max_temp_df["Date"] == int(f'{today}0000'))]
    max_temp = float(max_temp["tre200dx"].values[0])
    data = {'min_temp': min_temp, 'max_temp': max_temp}
    return data


def fetch_meteoswiss_ogd_object(collection_id, item_id, asset_id, filename=None):
    """Fetch data object from meteoswiss open data STAC API. Was initially dedicated to pollen, but was extended for
    other data sources."""
    if filename is None:
        filename = asset_id
    global item_etags
    global asset_etags

    if item_id not in item_etags.keys():
        item_etags[item_id] = "*"
    if asset_id not in asset_etags.keys():
        asset_etags[asset_id] = "*"

    # Accessing a specific item (like forecasting data, or a specific pollen station's measurements).
    item_url = f'http://data.geo.admin.ch/api/stac/v1/collections/{collection_id}/items/{item_id}'

    if os.path.isfile(f'./{asset_id}'):
        try:
            # We only want to download our data if it has changed
            item_response = requests.get(item_url, headers={'If-None-Match': f"{item_etags[item_id]}"})
            if item_response.status_code == 304:
                print('No changes to data since last checked!')
            elif item_response.status_code == 200:
                item_etags[item_id] = item_response.headers.get("ETag")
                asset_href = item_response.json()['assets'][asset_id]['href']
                obj_response = requests.get(asset_href, headers={'If-None-Match': f"{asset_etags[asset_id]}"})
                if obj_response.status_code == 304:
                    print('No changes to data since last checked!')
                elif obj_response.status_code == 200:
                    asset_etags[asset_id] = obj_response.headers.get("ETag")  # save the new asset etag
                    with open(f'{filename}', 'wb') as f:
                        f.write(obj_response.content)
                        f.close()
        except Exception as e:
            print(f"Error downloading {item_url}: {e}")
            return {'Status': 'Failure'}
    else:
        try:
            item_response = requests.get(item_url)
            item_etags[item_id] = item_response.headers.get("ETag")
            if item_response.status_code == 200:
                asset_href = item_response.json()['assets'][asset_id]['href']
                obj_response = requests.get(asset_href)
                if obj_response.status_code == 200:
                    asset_etags[asset_id] = obj_response.headers.get("ETag")  # save the new asset etag
                    with open(f'{filename}', 'wb') as f:
                        f.write(obj_response.content)
                        f.close()
        except Exception as e:
            print(f"Error downloading {item_url}: {e}")
            return {'Status': 'Failure'}
    return {'Status': 'Success'}


def get_pollen_concentration():
    """Returns pollen concentration levels for previous day, as well as a rating (very high, high, moderate, low). Each
    allergen has its own thresholds for these levels, so they must be calculated independently. Levels from
    meteoschweiz."""
    fetch_meteoswiss_ogd_object("ch.meteoschweiz.ogd-pollen", f"pls",
                                f"ogd-pollen_pls_d_recent.csv")
    pollen_data = {}
    p_levels = pd.read_csv("pollen_levels.csv", sep=";")
    columns = ["kaalnud1", "kabetud1", "kacoryd1", "kafagud1", "kafraxd1", "kaquerd1", "khpoacd1"]
    pdf = pd.read_csv("ogd-pollen_pls_d_recent.csv", sep=";")
    # We're keeping the timestamp for now, but this may not come in handy.
    pdf = pdf[["reference_timestamp"] + columns]
    prev_day_pollen = pdf.iloc[-1]
    for c in columns:
        pollen = prev_day_pollen[[c]]
        levels = p_levels.loc[p_levels["name"] == c]
        english_name = levels[["english name"]].values[0][0]
        if pollen.values[0] < levels[["low"]].values[0]:
            pollen_data[english_name] = {'level': 'low', 'value': pollen.values[0]}
        elif pollen.values[0] < levels[["moderate"]].values[0]:
            pollen_data[english_name] = {'level': 'moderate', 'value': pollen.values[0]}
        elif pollen.values[0] < levels[["high"]].values[0]:
            pollen_data[english_name] = {'level': 'high', 'value': pollen.values[0]}
        else:
            pollen_data[english_name] = {'level': 'very high', 'value': pollen.values[0]}
    return pollen_data

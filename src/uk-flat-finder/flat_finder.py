import datetime
import os
import re
import json

import numpy as np
import requests
from rightmove_webscraper import RightmoveData


def _extract_postcode_from_address(flats_dataframe):
    postcode_regex = re.compile(
        "([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z]["
        "A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z]["
        "A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s?[0-9][A-Za-z]{2})"
    )
    postcode = re.search(postcode_regex, flats_dataframe["address"])
    flats_dataframe.loc[flats_dataframe.postcode != np.NaN] = postcode
    return flats_dataframe


def get_rightmove_properties_from_url(url):
    rightmove_data = RightmoveData(url)
    flats_dataframe = rightmove_data.get_results
    return flats_dataframe


class FlatFinder:
    def __init__(self, destination, use_gcp=True):
        self.use_gcp = use_gcp
        self.travel_destination = destination

        if use_gcp:
            if os.path.isfile("api.key"):
                with open("api.key") as f:
                    self.api_key = f.read().strip("\n")
            else:
                raise Exception("No api key!")

            if os.path.isfile("../../google-api-endpoints.json"):
                with open("../../google-api-endpoints.json") as f:
                    api_urls = json.load(f)
                    self.url_geocode = api_urls["url-google-geocode"]
                    self.url_distance_matrix = api_urls[
                        "url-google-distance-matrix"
                    ]
            else:
                raise Exception("No GCP endpoints provided!")

    def _google_maps_query(
        self,
        origin,
        destination,
        mode,
        time=int(datetime.datetime(2020, 9, 2, 9, 0, 0, 0).timestamp()),
    ):

        params = {
            "origins": origin,
            "destinations": destination,
            "departure_time": time,
            "mode": mode,
            "units": "metric",
        }

        if self.api_key is not None:
            params = {"key": self.api_key}

        payload = {}
        headers = {}
        response = requests.request(
            "GET",
            self.url_distance_matrix,
            headers=headers,
            data=payload,
            params=params,
        )
        return response

    def _get_commute_times(self, origin, destination, time="commute"):
        times = {
            "distance": np.nan,
            "transit": np.nan,
            "bicycling": np.nan,
            "walking": np.nan,
        }
        if time == "night":
            time_of_day = int(
                datetime.datetime(2020, 9, 4, 2, 0, 0, 0).timestamp()
            )
        else:
            time_of_day = int(
                datetime.datetime(2020, 9, 2, 9, 0, 0, 0).timestamp()
            )

        for mode in ["transit", "bicycling", "walking"]:
            response = self._google_maps_query(
                origin, destination, mode, time_of_day
            )
            if response.status_code == 200:
                response_json = response.json()
                if len(response_json["rows"]) != 1:
                    print("wrong number of rows!")
                    print(response_json)
                try:
                    times[mode] = response_json["rows"][0]["elements"][0][
                        "duration"
                    ]["value"]
                    times["distance"] = response_json["rows"][0]["elements"][
                        0
                    ]["distance"]["value"]
                except:
                    print("Error!")

        return times

    def _google_geocoding_query(self, address):
        params = {"address": address}

        if self.api_key is not None:
            params["key"] = self.api_key

        payload = {}
        headers = {}
        response = requests.request(
            "GET",
            self.url_geocode,
            headers=headers,
            data=payload,
            params=params,
        )
        return response

    def _get_coordinates(self, address):
        response = self._google_geocoding_query(address)
        if response.status_code == 200:
            response_json = response.json()
            if len(response_json["results"]) != 1:
                print("wrong number of results!")
            try:
                lat = response_json["results"][0]["geometry"]["location"][
                    "lat"
                ]
                lng = response_json["results"][0]["geometry"]["location"][
                    "lng"
                ]
                return lat, lng
            except:
                print("Error!")
        else:
            return np.NaN, np.NaN

    def add_distances(self, flats_dataframe):
        transit = np.empty((len(flats_dataframe),))
        transit[:] = np.nan
        bicycling = np.empty((len(flats_dataframe),))
        bicycling[:] = np.nan
        walking = np.empty((len(flats_dataframe),))
        walking[:] = np.nan
        distance = np.empty((len(flats_dataframe),))
        distance[:] = np.nan

        for idx, row in flats_dataframe.iterrows():
            origin = row["address"]

            commute_times = self._get_commute_times(
                origin, self.travel_destination
            )
            transit[idx] = commute_times["transit"]
            bicycling[idx] = commute_times["bicycling"]
            walking[idx] = commute_times["walking"]
            distance[idx] = commute_times["distance"]

        flats_dataframe["bicycling"] = bicycling
        flats_dataframe["walking"] = walking
        flats_dataframe["distance"] = distance

        return flats_dataframe

    def add_return_at_night(self, flats_dataframe):
        late_transit = np.empty((len(flats_dataframe),))
        late_transit[:] = np.nan

        for idx, row in flats_dataframe.iterrows():
            destination = row["address"]

            commute_times = self._get_commute_times(
                self.nighttime_departure, destination, time="night"
            )
            late_transit[idx] = commute_times["transit"]

        flats_dataframe["late_transit"] = late_transit

        return flats_dataframe

    def add_coordinates(self, flats_dataframe):
        lat = np.empty((len(flats_dataframe),))
        lng = np.empty((len(flats_dataframe),))
        lat[:] = np.nan
        lng[:] = np.nan

        for idx, row in flats_dataframe.iterrows():
            lat_row, lng_row = self._get_coordinates(row["address"])
            lat[idx] = lat_row
            lng[idx] = lng_row

        flats_dataframe["latitude"] = lat
        flats_dataframe["longitude"] = lng

        return flats_dataframe

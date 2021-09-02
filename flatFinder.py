import datetime
import os

import numpy as np
import requests
from rightmove_webscraper import RightmoveData


class FlatFinder:
    def __init__(self):
        if os.path.isfile("api.key"):
            with open("api.key") as f:
                self.api_key = f.read().strip("\n")
        else:
            print("No api key!")
            self.api_key = None

    def _google_maps_query(self, origin, destination, mode):
        url = "https://maps.googleapis.com/maps/api/distancematrix/json?"
        params = {"origins": origin,
                  "destinations": destination,
                  "departure_time": int(datetime.datetime(2021, 9, 9, 9, 0, 0, 0).timestamp()),
                  "mode": mode,
                  "units": "metric"}

        if self.api_key is not None:
            params = {"key": self.api_key}

        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload, params=params)
        return response

    def _get_commute_times(self, origin, destination):
        times = {"distance": np.nan, "transit": np.nan, "bicycling": np.nan, "walking": np.nan}

        for mode in ["transit", "bicycling", "walking"]:
            response = self._google_maps_query(origin, destination, mode)
            if response.status_code == 200:
                response_json = response.json()
                if len(response_json["rows"]) != 1:
                    print("wrong number of rows!")
                    print(response_json)
                try:
                    times[mode] = response_json["rows"][0]["elements"][0]["duration"]["value"]
                    times["distance"] = response_json["rows"][0]["elements"][0]["distance"]["value"]
                except:
                    print("Error!")

        return times

    def get_rightmove_properties_from_url(self, url):
        rightmove = RightmoveData(url)
        flatsDF = rightmove.get_results
        return flatsDF

    def add_distances_to_rightmove_properties(self, flatsDF):
        transit = np.empty((len(flatsDF),))
        transit[:] = np.nan
        bicycling = np.empty((len(flatsDF),))
        bicycling[:] = np.nan
        walking = np.empty((len(flatsDF),))
        walking[:] = np.nan
        distance = np.empty((len(flatsDF),))
        distance[:] = np.nan

        for idx, row in flatsDF.iterrows():
            origin = row["address"]

            commute_times = self._get_commute_times(origin, "UCL Main Campus, London")
            transit[idx] = commute_times["transit"]
            bicycling[idx] = commute_times["bicycling"]
            walking[idx] = commute_times["walking"]
            distance[idx] = commute_times["distance"]

        flatsDF["bicycling"] = bicycling
        flatsDF["walking"] = walking
        flatsDF["distance"] = distance

        return flatsDF

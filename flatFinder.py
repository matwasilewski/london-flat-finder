import datetime
import os
import re

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

    def _google_maps_query(self, origin, destination, mode, time=int(datetime.datetime(2020, 9, 2, 9, 0, 0, 0).timestamp())):
        url = "https://maps.googleapis.com/maps/api/distancematrix/json?"
        params = {"origins": origin,
                  "destinations": destination,
                  "departure_time": time,
                  "mode": mode,
                  "units": "metric"}

        if self.api_key is not None:
            params = {"key": self.api_key}

        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload, params=params)
        return response

    def _get_commute_times(self, origin, destination, time="commute"):
        times = {"distance": np.nan, "transit": np.nan, "bicycling": np.nan, "walking": np.nan}
        if time == "night":
            time_of_day = int(datetime.datetime(2020, 9, 4, 2, 0, 0, 0).timestamp())
        else:
            time_of_day = int(datetime.datetime(2020, 9, 2, 9, 0, 0, 0).timestamp())

        for mode in ["transit", "bicycling", "walking"]:
            response = self._google_maps_query(origin, destination, mode, time_of_day)
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

    def _google_geocoding_query(self, address):
        url = "https://maps.googleapis.com/maps/api/geocode/json?"

        params = {"address": address}

        if self.api_key is not None:
            params["key"] = self.api_key

        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload, params=params)
        return response

    def _get_coordinates(self, address):
            response = self._google_geocoding_query(address)
            if response.status_code == 200:
                response_json = response.json()
                if len(response_json["results"]) != 1:
                    print("wrong number of results!")
                try:
                    lat = response_json["results"][0]["geometry"]["location"]["lat"]
                    lng = response_json["results"][0]["geometry"]["location"]["lng"]
                    return lat, lng
                except:
                    print("Error!")
            else:
                return np.NaN, np.NaN

    def _extract_postcode_from_address(self, flatsDF):
        postcode_regex = re.compile("([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s?[0-9][A-Za-z]{2})")
        postcode = re.search(postcode_regex, flatsDF["address"])
        flatsDF.loc[flatsDF.postcode != np.NaN] = postcode
        return flatsDF



    def get_rightmove_properties_from_url(self, url):
        rightmove = RightmoveData(url)
        flatsDF = rightmove.get_results
        return flatsDF

    def add_distances(self, flatsDF):
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

    def add_return_at_night(self, flatsDF):
        late_transit = np.empty((len(flatsDF),))
        late_transit[:] = np.nan

        for idx, row in flatsDF.iterrows():
            destination = row["address"]

            commute_times = self._get_commute_times("Soho Square, London W1D 3QP, United Kingdom", destination, time="night")
            late_transit[idx] = commute_times["transit"]

        flatsDF["late_transit"] = late_transit

        return flatsDF

    def add_coordinates(self, flatsDF):
        lat = np.empty((len(flatsDF),))
        lng = np.empty((len(flatsDF),))
        lat[:] = np.nan
        lng[:] = np.nan

        for idx, row in flatsDF.iterrows():
            lat_row, lng_row = self._get_coordinates(row["address"])
            lat[idx] = lat_row
            lng[idx] = lng_row

        flatsDF["latitude"] = lat
        flatsDF["longitude"] = lng

        return flatsDF

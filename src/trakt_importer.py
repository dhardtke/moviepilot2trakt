import os
from json import load, dump, dumps, decoder

import requests
from imdb import IMDb

CACHE_FILE = "imdb_cache.json"


class TraktImporter:
    ia = IMDb()
    cache = dict()

    def __init__(self, config: dict, moviepilot_lists: dict, debug: bool):
        self.debug = debug
        self.moviepilot_lists = moviepilot_lists
        self.headers = {
            "Content-Type": "application/json",
            "trakt-api-key": config["client_id"],
            "trakt-api-version": "2",
        }
        self.base = config["base"]

        oauth_token = config["oauth_token"]
        if config["oauth_token"] is None:
            oauth_token = self.__retrieve_oauth_token(config["client_id"], config["client_secret"])
            print("Save as 'oauth_token' in config: {}".format(oauth_token))

        self.headers["Authorization"] = "Bearer {}".format(oauth_token)
        if os.path.isfile(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                TraktImporter.cache = load(f)

    def __del__(self):
        if TraktImporter.cache is not None:
            with open(CACHE_FILE, "w+") as f:
                dump(TraktImporter.cache, f)
            TraktImporter.cache = None

    def __request(self, verb: str, endpoint: str, data: dict) -> dict:
        url = "{}/{}".format(self.base, endpoint)
        r = getattr(requests, verb)(url, headers=self.headers, json=data)
        if self.debug:
            print("[DEBUG] [Trakt] Sending {} request to {} with payload:".format(verb.upper(), url))
            print(dumps(data))
        try:
            deserialized = r.json()
        except decoder.JSONDecodeError as e:
            if self.debug:
                print("[DEBUG] [Trakt] Got JSONDecodeError for {}: {}".format(r.text, e))
            deserialized = None
        if not str(r.status_code).startswith("2") or deserialized is None:
            raise ValueError("{} request to {} failed with status {} and response {}".format(verb.upper(), url, r.status_code, deserialized))

        if self.debug:
            print("[DEBUG] [Trakt] Got API response:")
            print(dumps(deserialized))
        return deserialized

    @staticmethod
    def __init_stats():
        keys = ["added", "existing", "not_found"]
        stats = {}
        for key in keys:
            stats[key] = {"movies": 0, "episodes": 0, "shows": 0}
        return stats

    @staticmethod
    def __update_stats(stats: dict, result: dict, include_not_found=False) -> None:
        for key in stats:
            if key == "not_found" and not include_not_found:
                continue
            for what in stats[key]:
                if key not in result or what not in result[key]:
                    continue
                if key == "not_found":
                    stats[key][what] += len(result[key][what])
                else:
                    stats[key][what] += result[key][what]

    @staticmethod
    def __find_imdb_id(title):
        if title in TraktImporter.cache:
            return TraktImporter.cache[title]

        movie = TraktImporter.ia.search_movie(title)
        imdbid = None
        if len(movie) > 0:
            imdbid = "tt{}".format(movie[0].movieID)
        TraktImporter.cache[title] = imdbid
        return imdbid

    def __process(self, description: str, moviepilot_select: str, endpoint: str, date_key: str = None):
        data = {"movies": [], "shows": []}
        transform_keys = {"movies": "movies", "series": "shows"}  # a mapping of moviepilot.de keys => trakt.tv keys
        for moviepilot_key in transform_keys.keys():
            for moviepilot_entry in self.moviepilot_lists[moviepilot_select][moviepilot_key]:
                trakt_entry = {
                    "title": moviepilot_entry["title"]
                }
                if date_key is not None:
                    trakt_entry[date_key] = moviepilot_entry["date"].isoformat()
                data[transform_keys[moviepilot_key]].append(trakt_entry)

        stats = TraktImporter.__init_stats()
        # first attempt by title
        result = self.__request("post", endpoint, data)
        TraktImporter.__update_stats(stats, result)
        if len(result["not_found"]["movies"]) > 0 or len(result["not_found"]["shows"]) > 0:
            data = {"movies": [], "shows": []}
            for key in data.keys():
                for entry in result["not_found"][key]:
                    trakt_entry = {
                        "title": entry["title"],
                        "ids": {
                            "imdb": TraktImporter.__find_imdb_id(entry["title"])
                        }
                    }
                    if date_key is not None:
                        trakt_entry[date_key] = entry[date_key].isoformat()
                    data[key].append(trakt_entry)
            result = self.__request("post", endpoint, data)
            TraktImporter.__update_stats(stats, result, True)
        print("[INFO] [Trakt] {} completed: {}".format(description, stats))
        if len(result["not_found"]["movies"]) > 0 or len(result["not_found"]["shows"]) > 0:
            print("[WARN] [Trakt] {} could not find the following items on trakt.tv: {}".format(description, result["not_found"]))
            print("[WARN] [Trakt] Try to add them manually to your watchlist.")

    def add_to_watchlist(self):
        self.__process("Watchlist Import", "watchlisted", "sync/watchlist")

    def add_to_history(self):
        self.__process("Rated List (History)", "rated", "sync/history")

    def work(self):
        # self.add_to_watchlist()
        self.add_to_history()

    def __retrieve_oauth_token(self, client_id, client_secret) -> str:
        print("Open the link in a browser and paste the pincode when prompted")
        print("https://trakt.tv/oauth/authorize?response_type=code&client_id={}&redirect_uri=urn:ietf:wg:oauth:2.0:oob".format(client_id))
        pincode = str(input('PIN Code: '))
        url = "{}/oauth/token".format(self.base)
        values = {
            "code": pincode,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "authorization_code"
        }

        request = requests.post(url, data=values)
        response = request.json()

        return response["access_token"]

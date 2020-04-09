from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup


class MoviepilotScraper:
    BASE = "https://www.moviepilot.de"

    def __init__(self, config: dict, debug: bool):
        self.debug = debug
        self.username = config["username"]
        self.password = config["password"]
        self.authenticated = False
        self.cookie_jar = requests.cookies.RequestsCookieJar()
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0"
        }
        if config["sessionid"]:
            print("[INFO] [Moviepilot] Using specified sessionid instead of logging in with credentials")
            self.authenticated = True
            self.cookie_jar.set("_moviepilot_de_session", config["sessionid"], domain="www.moviepilot.de")

    def __request(self, url):
        if not self.authenticated:
            r = requests.post("{base}/api/session".format(base=MoviepilotScraper.BASE), json={
                "username": self.username,
                "password": self.password
            }, cookies=self.cookie_jar, headers=self.headers)
            self.cookie_jar = r.cookies
            if r.status_code != 200:
                raise ValueError("Could not login")
            self.authenticated = True
        r = requests.get(url, cookies=self.cookie_jar, headers=self.headers)
        self.cookie_jar = r.cookies
        if r.status_code != 200:
            raise ValueError("GET Request to {} failed".format(url))
        return r.text

    def __find_profile_url(self):
        html = self.__request("{base}/myprofile".format(base=MoviepilotScraper.BASE))
        bs = BeautifulSoup(html, features="lxml")
        return "{base}{path}".format(base=MoviepilotScraper.BASE, path=bs.select_one("#tab_show a")['href'])

    @staticmethod
    def __build_url(profile_url: str, select: str, what: str) -> str:
        """

        :param profile_url:
        :param select:
        :param what:
        :return: a constructed URL like https://www.moviepilot.de/users/username/watchlisted/movies
        """
        return "{}/{}/{}".format(profile_url, select, what)

    def __collect(self, url: str) -> List[dict]:
        entries = []
        urls = [url]
        while len(urls) > 0:
            html = self.__request(urls.pop(0))
            bs = BeautifulSoup(html, features="lxml")
            for row in bs.select(".table-plain-list tbody tr"):
                tds = row.find_all("td")
                entries.append({
                    "title": tds[0].select_one("a").text.strip(),
                    "rating": float("0" + tds[1].text.strip()),  # can also be the prediction
                    "date": datetime.strptime(tds[2].text.strip(), '%d.%m.%Y')
                })
            pagination_next = bs.select_one(".pagination--next")
            if pagination_next:
                urls.append("{}{}".format(MoviepilotScraper.BASE, pagination_next["href"]))

        return entries

    def extract_lists(self):
        profile_url = self.__find_profile_url()
        lists = {
            "watchlisted": {
                "movies": [],
                "series": []
            },
            "rated": {
                "movies": [],
                "series": []
            },
        }
        for select in lists.keys():
            for what in lists[select].keys():
                url = MoviepilotScraper.__build_url(profile_url, select, what)
                lists[select][what] = self.__collect(url)

        if self.debug:
            print("[DEBUG] [Moviepilot] Scraped the following lists from Moviepilot:")
            print(lists)

        return lists

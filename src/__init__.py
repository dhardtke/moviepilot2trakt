#!/usr/bin/env python3
# requirements: requests, bs4, imdbpy
import configparser
import os
import sys
from argparse import ArgumentParser

from moviepilot_scraper import MoviepilotScraper
from trakt_importer import TraktImporter

CONFIG_FILE = "config.ini"


def main():
    parser = ArgumentParser(description="Moviepilot.de to trakt.tv migration script.")
    parser.add_argument("-d", "--debug", dest="debug", help="Enable debug output", default=False, action="store_true")

    args = parser.parse_args()
    config = configparser.ConfigParser(interpolation=None)
    os.chdir(os.path.join(os.path.dirname(sys.argv[0]), "..", "data"))
    config.read(CONFIG_FILE)
    validate_config(config)
    scrapper = MoviepilotScraper(dict(config["moviepilot"]), args.debug)
    importer = TraktImporter(dict(config["trakt"]), scrapper.extract_lists(), args.debug)
    importer.work()


def validate_config(config: configparser.ConfigParser):
    def _error(what):
        print(what)
        sys.exit(1)

    sections = {"moviepilot": ["username", "password"], "trakt": ["client_id", "client_secret", "base"]}
    for section in sections.keys():
        if not config.has_section(section):
            _error("Section {} is missing in config".format(section))
        for option in sections[section]:
            if not config.has_option(section, option):
                _error("Section {} is missing option {} in config".format(section, option))


if __name__ == "__main__":
    main()

# Moviepilot2Trakt
This script allows you to migrate your [moviepilot.de](https://moviepilot.de) lists to [trakt.tv](https://trakt.tv).

## Requirements
This script is written in Python 3.

In order to install the script's dependencies you can use `pip`:

`pip install -r requirements.txt`

## Config
Create the file data/config.ini with the following contents:
```ini
[moviepilot]
username = 
password = 
sessionid = 

[trakt]
client_id = 
client_secret = 
oauth_token = 
base = https://api.trakt.tv
```

You can omit the `sessionid` from the moviepilot section if you don't know what it is for.
You will be prompted for a trakt PIN to generate the `oauth_token` if you don't specify one. 

## Known Issues
# Adding items to the history adds a play to them
You can use https://github.com/anthofo/trakt-tv-duplicates-removal to remove all but the oldest one.

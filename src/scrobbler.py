#!/usr/bin/env python3

from collections import OrderedDict
from datetime import datetime, timedelta
import re

from pylast import LastFMNetwork, SessionKeyGenerator

import config


TRACK_LENGTH = 300
FEAT_REGEX = r"\s+((?:feat|ft)\.?\s+.*)"


def get_track_artist_string(artist):
    return re.sub(FEAT_REGEX, '', artist)


def get_track_title_string(artist, title, extra_info):
    if extra_info != '':
        title = "{} ({})".format(title, extra_info)

    feat = re.findall(FEAT_REGEX, artist)
    if len(feat) > 0:
        title = "{} ({})".format(title, feat[0])

    return title


def track_is_id(track):
    return track['artist'].lower() == 'id' or track['title'].lower().startswith('id')


class Scrobbler():
    def __init__(self):
        self.network = LastFMNetwork(api_key=config.API_KEY,
                                     api_secret=config.API_SECRET,
                                     username=config.USERNAME)

    def authenticate_interactively(self):
        key_gen = SessionKeyGenerator(self.network)
        auth_url = key_gen.get_web_auth_url()
        print("Please auth at: {}".format(auth_url))
        input("Press enter when done...")
        session_key = key_gen.get_web_auth_session_key(auth_url)
        print("Session key is: {} (update your config.py!)".format(session_key))
        return session_key

    def set_session_key(self, session_key):
        self.network.session_key = session_key

s = Scrobbler()
s.set_session_key(config.SESSION_KEY or s.authenticate_interactively())

print("Enter tracklist. End with ^D (or ^Z in windows).")
lines = []
while True:
    try:
        line = input()
    except EOFError:
        break
    lines.append(line)
tracklist = "\n".join(lines)

regexes = OrderedDict([
    ("ABGT Youtube", r"\d+\.\s*(.*?)\s*[’‘'](.*?)[’‘']\s*(?:\[(.*?)\])?"),
    ("1001 Tracklists export", r"(?:\d+\.|\[(?:\d+:)*\d+\]) (.+?) - (.+?)(?: \((.+?)\))?( \[.*\])?$"),
    ("Artist - Track", r"^(?:\d+\.\s*)?(.*?)\s+[-–]\s+(.*)()$"),
    ("01. Artist - Track (Remix) [Label]", r"^\d+\.\s*(.*?)\s*-\s*([^([]+)(?:\s+\((.*?)\))?\s*(?:\[.*?\])?$"),
    ("01. Artist - Track", r"\d+\.\s*(.*?) - (.*)()"),
    ("01:18:52 Artist - Track", r"\d?\d:\d\d:\d\d (.*?) - (.*)()"),
    ("(01:18:52) 01. Artist - Track [Something] (Something)", r"^\([\d:]+\) \d+\. (.*?) - ([^[]*?)(?: \[([^]]*)\])?(?: \(.*?\))?$"),
    ("Traktor export", r".* \t(.*) \t(.*)()")
])

print("\nAvailable matchers:")
for index, (description, _regex) in enumerate(regexes.items(), start=1):
    print("{}. {}".format(index, description))
regex = list(regexes.values())[int(input("Pick a matcher by number: ")) - 1]

print("\nRegex is {}\n".format(regex))

results = re.findall(regex, tracklist, re.MULTILINE)

time_format = '%Y-%m-%d %H:%M:%S'
format_example = datetime.strftime(datetime.utcnow(), time_format)
time_input = input("Enter start time (e.g. {}) in UTC (or empty for end time now): "
                   .format(format_example))
if time_input == "":
    start_time = (datetime.utcnow() - timedelta(seconds=TRACK_LENGTH * len(results)))
else:
    start_time = datetime.strptime(time_input, time_format)

tracks = [{'artist': get_track_artist_string(r[0]),
           'title': get_track_title_string(r[0], r[1], r[2]),
           'timestamp': start_time + timedelta(seconds=TRACK_LENGTH * i)}
          for i, r in enumerate(results)]

ids = [track for track in tracks if track_is_id(track)]
tracks = [track for track in tracks if not track_is_id(track)]

if len(tracks) == 0:
    print("No tracks found")
else:
    print("\nFound following tracks:")
    for track in tracks:
        print("[{}] {} - {}".format(track['timestamp'], track['artist'], track['title']))

    if len(ids) > 0:
        print("\nIgnoring {} ID tracks:".format(len(ids)))
        for track in ids:
            print("{} - {}".format(track['artist'], track['title']))

    print("\n{} tracks in total".format(len(tracks)))

    if input("\nInput y to submit these tracks (check date!)") == 'y':
        print("Submitting...")
        s.network.scrobble_many(tracks)
        print("Done")
    else:
        print("Cancelled")

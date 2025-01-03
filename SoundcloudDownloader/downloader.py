import re
import os
from pathlib import Path

import requests
import m3u8

from .util import HttpClient, clean_filename, add_metadata_to_music


class SCDL:
    base_url = "https://soundcloud.com"
    base_api_url = "https://api-v2.soundcloud.com"
    track_url_regex = re.compile(r"(https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+)")

    def __init__(self):
        self.user_agent = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.user_agent)
        self.client_id = "TeyyF4yyJvOCHG1txg8Z4jfrHt8gcLzc"
        self.session.params.update({"client_id": self.client_id})
        self.session_m3u8 = requests.Session()
        self.session_m3u8.headers.update(self.user_agent)

    def _get_track_info(self, track_url):
        response = self.session.get(
            SCDL.base_api_url + "/resolve", params={"url": track_url}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def _get_track_download_url_and_protocol(self, track_info):
        if "downloadable" in track_info and "download_url" in track_info:
            return (
                track_info["download_url"],
                track_info.get("original_format", "mp3"),
                "direct",
            )

        elif track_info["streamable"]:
            if "stream_url" in track_info:
                return (
                    track_info["stream_url"],
                    track_info.get("original_format", "mp3"),
                    "stream",
                )
            for transcoding in track_info["media"]["transcodings"]:
                if transcoding["format"]["protocol"] == "progressive":
                    response = self.session.get(transcoding["url"])
                    if response.status_code == 200:
                        return (response.json()["url"], "mp3", "stream")

                elif transcoding["format"]["protocol"] == "hls":
                    response = self.session.get(transcoding["url"])
                    if response.status_code == 200:
                        return (response.json()["url"], "mp3", "m3u8")

        return (None, None, None)

    def _parse_track_info(self, track_info):
        artist = "Unknown"
        album = "Unknown Album"
        if "publisher_metadata" in track_info and track_info["publisher_metadata"]:
            artist = track_info["publisher_metadata"]["artist"]
            if "album_title" in track_info["publisher_metadata"]:
                album = track_info["publisher_metadata"]["album_title"]

        elif "user" in track_info and track_info["user"]:
            artist = track_info["user"]["username"]

        year = "Unknown"
        if "release_year" in track_info and track_info["release_year"]:
            year = track_info["release_year"]

        elif "release_date" in track_info and track_info["release_date"]:
            year = track_info["release_date"].split("-", 1)[0]

        download_url, extension, protocol = self._get_track_download_url_and_protocol(
            track_info
        )

        return {
            "title": track_info["title"],
            "artist": artist,
            "download_url": download_url,
            "extension": extension,
            "protocol": protocol,
            "artwork_url": track_info["artwork_url"],
            "genre": track_info["genre"],
            "year": year,
            "album": album,
        }

    def _get_filename(self, metadata):
        filename = "{artist} - {title}.{ext}".format(
            artist=metadata["artist"],
            title=metadata["title"],
            ext=metadata["extension"],
        )
        return clean_filename(filename)

    def download_artwork(self, metadata, filename):
        if metadata["artwork_url"]:
            artwork = b""
            for chunk in self.session_m3u8.get(metadata["artwork_url"], stream=True):
                artwork += chunk

        return artwork

    def download(self, track_url=None, _path=None):
        print("Checking track url")
        if track_url is None:
            raise ValueError("Track URL is required")

        if not self.track_url_regex.match(track_url):
            raise ValueError("Invalid track URL")

        print("Getting track information from SoundCloud")
        track_info = self._get_track_info(track_url)
        if track_info is None:
            raise ValueError("Track not found")

        metadata = self._parse_track_info(track_info)
        filename = self._get_filename(metadata)
        print(filename)
        for k in metadata:
            if k != "download_url":
                print(str(k) + ": ", metadata[k])

        path = Path(".") / filename
        if _path is not None:
            path = Path(_path) / filename

        if os.path.exists(path):
            raise FileExistsError("File already exists")

        print("Downloading...")
        if metadata["protocol"] in ("direct", "stream"):
            with open(path, "wb") as f:
                for chunk in self.session.get(metadata["download_url"], stream=True):
                    f.write(chunk)

        elif metadata["protocol"] == "m3u8":
            playlist = m3u8.load(
                metadata["download_url"], http_client=HttpClient(self.session)
            )
            with open(path.resolve(), "wb") as f:
                for segment in playlist.segments:
                    for chunk in self.session_m3u8.get(
                        segment.absolute_uri, stream=True
                    ):
                        f.write(chunk)
        print("Track Downloaded")
        print("Getting track cover")
        artwork = self.download_artwork(metadata, filename)
        print("Adding metadata information")
        add_metadata_to_music(path.resolve(), artwork, metadata)
        print("Done.")

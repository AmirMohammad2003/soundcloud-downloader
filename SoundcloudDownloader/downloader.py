import re
import os

import requests
import m3u8

from .util import HttpClient, add_artwork_to_music


class SCDL:
    base_url = 'https://soundcloud.com'
    base_api_url = 'https://api-v2.soundcloud.com'
    track_url_regex = \
        re.compile(r'(https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+)')

    def __init__(self):
        self.user_agent = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.user_agent)
        self.client_id = "0vyDB4rxVEprGutWT0xQ2VZhYpVZxku4"
        self.session.params.update({"client_id": self.client_id})
        self.session_m3u8 = requests.Session()
        self.session_m3u8.headers.update(self.user_agent)

    def _get_track_info(self, track_url):
        response = self.session.get(
            SCDL.base_api_url + '/resolve',
            params={"url": track_url}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def _get_track_download_url_and_protocol(self, track_info):
        if "downloadable" in track_info and "download_url" in track_info:
            return (track_info["download_url"], track_info.get("original_format", "mp3"), "direct")

        elif track_info["streamable"]:
            if "stream_url" in track_info:
                return (
                    track_info["stream_url"],
                    track_info.get("original_format", "mp3"),
                    "stream"
                )
            for transcoding in track_info["media"]["transcodings"]:
                if transcoding['format']['protocol'] == "progressive":
                    response = self.session.get(transcoding['url'])
                    if response.status_code == 200:
                        return (
                            response.json()["url"],
                            "mp3",
                            "stream"
                        )

                elif transcoding['format']['protocol'] == "hls":
                    response = self.session.get(transcoding['url'])
                    if response.status_code == 200:
                        return (
                            response.json()["url"],
                            "mp3",
                            "m3u8"
                        )

        return (None, None, None)

    def _parse_track_info(self, track_info):
        artist = "Unknown"
        if "publisher_metadata" in track_info and track_info["publisher_metadata"]:
            artist = track_info["publisher_metadata"]["artist"]
        elif "user" in track_info and track_info["user"]:
            artist = track_info["user"]["username"]

        download_url, extension, protocol = \
            self._get_track_download_url_and_protocol(track_info)

        return {
            'title': track_info['title'],
            'artist': artist,
            'download_url': download_url,
            'extension': extension,
            'protocol': protocol,
            'artwork_url': track_info['artwork_url']
        }

    def _get_filename(self, metadata):
        return "{artist} - {title}.{ext}".format(
            artist=metadata["artist"],
            title=metadata['title'],
            ext=metadata['extension']
        )

    def download_artwork(self, metadata, filename):
        if metadata['artwork_url']:
            artwork_filename = os.path.splitext(filename)[0] + '.jpg'
            with open(artwork_filename, 'wb') as f:
                for chunk in self.session_m3u8.get(metadata['artwork_url'], stream=True):
                    f.write(chunk)

        return artwork_filename

    def download(self, track_url=None):
        if track_url is None:
            raise ValueError("Track URL is required")

        if not self.track_url_regex.match(track_url):
            raise ValueError('Invalid track URL')

        track_info = self._get_track_info(track_url)
        if track_info is None:
            raise ValueError('Track not found')

        metadata = self._parse_track_info(track_info)
        filename = self._get_filename(metadata)

        if metadata['protocol'] == "direct" or metadata['protocol'] == "stream":
            with open(filename, 'wb') as f:
                for chunk in self.session.get(metadata['download_url'], stream=True):
                    f.write(chunk)

        elif metadata['protocol'] == "m3u8":
            playlist = \
                m3u8.load(
                    metadata['download_url'],
                    http_client=HttpClient(self.session)
                )
            for segment in playlist.segments:
                with open(filename, 'ab') as f:
                    for chunk in self.session_m3u8.get(segment.absolute_uri, stream=True):
                        f.write(chunk)

        artwork_filename = self.download_artwork(metadata, filename)
        add_artwork_to_music(filename, artwork_filename)

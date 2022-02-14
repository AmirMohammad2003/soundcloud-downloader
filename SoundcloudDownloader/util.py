import re

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TDRC, TCON, TALB


class HttpClient:

    def __init__(self, session):
        self.session = session

    def download(self, url, timeout=None, headers={}, verify_ssl=True):
        response = self.session.get(url, timeout=timeout, headers=headers)
        return response.text, response.url


def clean_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '', filename)


def add_metadata_to_music(filename, artwork, metadata):
    audio = MP3(filename, ID3=ID3)
    audio.add_tags()
    if artwork:
        audio.tags.add(APIC(
            encoding=3,  # urf-8
            mime="image/jpeg",
            type=3,  # front cover
            desc=u'cover',
            data=artwork
        ))
    audio.tags["TIT2"] = TIT2(encoding=3, text=metadata['title'])
    audio.tags["TPE1"] = TPE1(encoding=3, text=metadata['artist'])
    audio.tags["TDRC"] = TDRC(encoding=3, text=metadata['year'])
    audio.tags["TCON"] = TCON(encoding=3, text=metadata['genre'])
    audio.tags["TALB"] = TALB(encoding=3, text=metadata['album'])
    audio.save()

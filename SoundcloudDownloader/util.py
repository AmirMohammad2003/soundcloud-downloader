from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC


class HttpClient:

    def __init__(self, session):
        self.session = session

    def download(self, url, timeout=None, headers={}, verify_ssl=True):
        response = self.session.get(url, timeout=timeout, headers=headers)
        return response.text, response.url


def add_artwork_to_music(filename, artwork):
    audio = MP3(filename, ID3=ID3)
    audio.add_tags()
    audio.tags.add(
        APIC(
            encoding=3,  # urf-8
            mime="image/jpeg",
            type=3,  # front cover
            desc=u'cover',
            data=artwork
        )
    )
    audio.save()

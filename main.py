"""
This is a command line interface for SoundcloudDownloader.
"""

import argparse
from SoundcloudDownloader import SCDL


def main():
    parser = argparse.ArgumentParser(
        description="Download songs from Soundcloud."
    )
    # TODO: Download Directory
    # parser.add_argument('-d', '--directory', help='Directory to download to.')
    parser.add_argument('-u', '--url', help='Music url to download.')
    args = parser.parse_args()

    if args.url is None:
        parser.print_help()
        return

    scdl = SCDL()
    scdl.download(args.url)


if __name__ == "__main__":
    main()

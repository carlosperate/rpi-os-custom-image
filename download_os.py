#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download a Raspberry PI OS image."""
import os
from zipfile import ZipFile

import requests


###############################################################################
# Configuration data start

# URL of the Raspberry Pi OS Lite zip file to download and check
# Find options in https://downloads.raspberrypi.org/raspios_lite_armhf/images/
OS_IMAGE_ZIP = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2021-03-25/2021-03-04-raspios-buster-armhf-lite.zip"
ZIP_SHA_256  = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2021-03-25/2021-03-04-raspios-buster-armhf-lite.zip.sha256"

# Configuration data end
###############################################################################

IMAGE_SAVE_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "rpiosimage"
)


def download_image_zip(zip_url=OS_IMAGE_ZIP):
    """Download a zip image from the internet.

    :param zip_url: URL to the zip file to download.
    :return: Absolute path to the downloaded zip file.
    """
    print("Downloading OS image: {}".format(zip_url))

    if not zip_url.startswith("http") or not zip_url.endswith(".zip"):
        raise Exception("Provided URL must be a zip file.")

    if not os.path.exists(IMAGE_SAVE_LOCATION):
        os.makedirs(IMAGE_SAVE_LOCATION)
    zip_img_filename = os.path.join(IMAGE_SAVE_LOCATION, zip_url.split('/')[-1])

    response = requests.get(zip_url, stream=True)
    if response.status_code == 200:
        with open(zip_img_filename, 'wb') as f:
            for i, chunk in enumerate(response.iter_content(chunk_size=10*1024*1024)):
                if chunk:
                    print("\t-> Downloaded {}0MB...".format(i), end='\r')
                    f.write(chunk)
            print("Download done!                  ")
    else:
        raise Exception("Could not reach the zip URL, error code {}: {}".format(
            response.status_code, zip_url
        ))
    return os.path.abspath(zip_img_filename)


def unzip_image(zip_path):
    """Unzips a file with a img file inside.

    :param zip_path: Path to the zip file to uncompress.
    :raises Exception: If there is no .img file inside the zip.
    :return: Absolute path to an uncompressed .img file from the zip.
    """
    print("Unzipping OS image: {}".format(zip_path))

    if not os.path.exists(IMAGE_SAVE_LOCATION):
        os.makedirs(IMAGE_SAVE_LOCATION)
    with ZipFile(zip_path, 'r') as z:
        name_list = z.namelist()
        z.extractall(path=IMAGE_SAVE_LOCATION)
    for file_name in name_list:
        if file_name.endswith('.img'):
            return os.path.abspath(os.path.join(IMAGE_SAVE_LOCATION, file_name))
    raise Exception("Could not find img file inside zip")


def main(img_zip_url=None):
    zip_path = download_image_zip(img_zip_url)
    img_path = unzip_image(zip_path)


if __name__ == "__main__":
    # We only use the first argument to receive a URL to the .img file
    main(sys.argv[1])

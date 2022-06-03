#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download a Raspberry PI OS image."""
import os
import sys
import lzma
import hashlib
from typing import Optional
from zipfile import ZipFile
from collections import namedtuple

import requests


###############################################################################
# Configuration data start

# URL of the Raspberry Pi OS Lite zip file to download and check
# Find options in https://downloads.raspberrypi.org/raspios_lite_armhf/images/
# Legacy version in https://downloads.raspberrypi.org/raspios_oldstable_lite_armhf/images/
# Legacy info https://www.raspberrypi.com/news/new-old-functionality-with-raspberry-pi-os-legacy/
OS_IMAGE_ZIP = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2022-01-28/2022-01-28-raspios-bullseye-armhf-lite.zip"
ZIP_SHA_256  = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2022-01-28/2022-01-28-raspios-bullseye-armhf-lite.zip.sha256"

# Configuration data end
###############################################################################

IMAGE_SAVE_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "rpiosimage"
)

# NamedTuple of a img URL and its SHA256 hash
ImageURL = namedtuple("ImageURL", ["url", "sha256_url"])
DEFAULT_IMAGE_URL = ImageURL(url=OS_IMAGE_ZIP, sha256_url=ZIP_SHA_256)


def download_compressed_image(img: ImageURL = DEFAULT_IMAGE_URL) -> str:
    """Download a compressed image from the internet.

    :param img: URL to the compressed file and sha256 to download.
    :return: Absolute path to the downloaded compressed file.
    """
    print("Downloading OS image: {}".format(img.url))

    if not img.url.startswith("http") or \
        (not img.url.endswith(".zip") and not img.url.endswith(".xz")):
        raise Exception("Provided URL must be a zip/xz file.")

    if not os.path.exists(IMAGE_SAVE_LOCATION):
        os.makedirs(IMAGE_SAVE_LOCATION)
    compressed_img_filename = os.path.join(IMAGE_SAVE_LOCATION, img.url.split('/')[-1])

    response = requests.get(img.url, stream=True)
    if response.status_code != 200:
        raise Exception("Could not reach the file URL, error code {}: {}".format(
            response.status_code, img.url
        ))
    with open(compressed_img_filename, 'wb') as f:
        for i, chunk in enumerate(response.iter_content(chunk_size=10*1024*1024)):
            if chunk:
                print("\t-> Downloaded {}0MB...".format(i), end='\r')
                f.write(chunk)
    print("\nDownload done!                  ")

    print("Verifying SHA256 hash...  ", end="")
    with open(compressed_img_filename, 'rb') as img_f:
        img_data = img_f.read()
    response = requests.get(img.sha256_url)
    if response.status_code != 200:
        raise Exception("Could not reach the SHA256 file URL, error code {}: {}".format(
            response.status_code, img.sha256_url
        ))
    sha_hash = response.text.split()[0]
    print(sha_hash)
    if sha_hash != hashlib.sha256(img_data).hexdigest():
        raise Exception("SHA256 hash does not match the file.")
    print("SHA256 hash verified!")

    return os.path.abspath(compressed_img_filename)


def decompress_image(compressed_path: str) -> str:
    """Decompress a file with a img file inside.

    :param compressed_path: Path to the zip or xz file to decompress.
    :raises Exception: If there is no .img file inside the compressed file.
    :return: Absolute path to an uncompressed .img file from the zip.
    """
    print("Decompressing OS image: {}".format(compressed_path))
    img_path = None
    if not os.path.exists(IMAGE_SAVE_LOCATION):
        os.makedirs(IMAGE_SAVE_LOCATION)
    if compressed_path.endswith(".zip"):
        with ZipFile(compressed_path, "r") as z:
            name_list = z.namelist()
            z.extractall(path=IMAGE_SAVE_LOCATION)
        for file_name in name_list:
            if file_name.endswith('.img'):
                img_path = os.path.abspath(os.path.join(IMAGE_SAVE_LOCATION, file_name))
                break
        else:
            raise Exception("Could not find img file inside zip")
    elif compressed_path.endswith(".xz"):
        img_filename = os.path.basename(compressed_path)[:-len(".xz")]
        img_path = os.path.join(IMAGE_SAVE_LOCATION, img_filename)
        with lzma.open(compressed_path) as xz_f, open(img_path, 'wb') as img_f:
            img_f.write(xz_f.read())
    else:
        raise Exception("Provided file is not a zip or xz file.")
    print("Decompression done!")
    return img_path


def main(img_zip_url: Optional[ImageURL] = None):
    compressed_path = download_compressed_image(img_zip_url)
    img_path = decompress_image(compressed_path)
    return 0


if __name__ == "__main__":
    # We only use the first argument to receive a URL to the .img file
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_URL))

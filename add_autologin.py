#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a Raspberry PI OS image with Docker and QEMU to configure autologin."""
import os
import sys
import uuid
import shutil
from zipfile import ZipFile

import pexpect
import requests


###############################################################################
# Configuration data start

# URL of the Raspberry Pi OS Lite zip file to download and check
# Find options in https://downloads.raspberrypi.org/raspios_lite_armhf/images/
OS_IMAGE_ZIP = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2020-08-24/2020-08-20-raspios-buster-armhf-lite.zip"
OS_IMAGE_SHA = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2020-08-24/2020-08-20-raspios-buster-armhf-lite.zip.sha256"
OS_IMAGE_SHA_TYPE = "256"

# Configuration data end
###############################################################################

IMAGE_SAVE_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "rpiosimage"
)

DOCKER_IMAGE = "lukechilds/dockerpi:vm"
DOCKER_CONTAINER_NAME= "rpi-os-autologin-{}".format(str(uuid.uuid4())[:8])

RPI_OS_USERNAME = "pi"
RPI_OS_PASSWORD = "raspberry"

BASH_PROMPT = "{}@raspberrypi:~$ ".format(RPI_OS_USERNAME)

TTY_SERVICE_AUTOLOGIN_CONF ="""[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin {} --noclear %I $TERM
""".format(RPI_OS_USERNAME)
SERIAL_TTY_SERVICE_AUTOLOGIN_CONF ="""[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin {} --keep-baud 115200,38400,9600 %I $TERM
""".format(RPI_OS_USERNAME)


def download_image_zip(zip_url):
    """Download a zip image from the internet.

    :param zip_url: URL to the zip file to download.
    :return: Absolute path to the downloaded zip file.
    """
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
    if not os.path.exists(IMAGE_SAVE_LOCATION):
        os.makedirs(IMAGE_SAVE_LOCATION)
    with ZipFile(zip_path, 'r') as z:
        name_list = z.namelist()
        z.extractall(path=IMAGE_SAVE_LOCATION)
    for file_name in name_list:
        if file_name.endswith('.img'):
            return os.path.abspath(os.path.join(IMAGE_SAVE_LOCATION, file_name))
    raise Exception("Could not find img file inside zip")


def update_os_image(img_path):
    """Creates a copy of the provided Raspberry Pi OS Lite image and runs it in
    QEMU inside a Docker container to configure autologin.

    :param img_path: Path to the Raspberry Pi OS Lite image to update.
    """
    if not img_path.endswith(".img"):
        raise Exception("Provided OS .img file does not have the right extension.")
    original_img = img_path
    new_img = img_path.replace(".img", "-autologin.img")
    shutil.copyfile(img_path, new_img)
    new_img = os.path.abspath(new_img)

    docker_cmd = " ".join([
        "docker",
        "run",
        "-it",
        "--rm",
        "--name {}".format(DOCKER_CONTAINER_NAME),
        "-v {}:/sdcard/filesystem.img".format(new_img),
        DOCKER_IMAGE
    ])
    print("Docker cmd: {}".format(docker_cmd))

    try:
        child = pexpect.spawn(docker_cmd, timeout=600, encoding='utf-8')
        child.logfile = sys.stdout
        # Login
        child.expect_exact("raspberrypi login: ")
        child.sendline(RPI_OS_USERNAME)
        child.expect_exact("Password: ")
        child.sendline(RPI_OS_PASSWORD)
        child.expect_exact(BASH_PROMPT)
        # Setup a service to configure autologin in ttyAMA0, which is what QEMU uses
        child.sendline("sudo mkdir -pv /etc/systemd/system/serial-getty@ttyAMA0.service.d")
        child.expect_exact(BASH_PROMPT)
        child.sendline('echo -en "{}" >> autologin.conf'.format(
            SERIAL_TTY_SERVICE_AUTOLOGIN_CONF.replace("\n", "\\n"))
        )
        child.expect_exact(BASH_PROMPT)
        child.sendline("sudo mv autologin.conf /etc/systemd/system/serial-getty@ttyAMA0.service.d/autologin.conf")
        child.expect_exact(BASH_PROMPT)
        child.sendline("sudo systemctl enable serial-getty@ttyAMA0.service")
        child.expect_exact(BASH_PROMPT)
        # Setup a service to autologin in the default tty
        child.sendline("sudo mkdir -pv /etc/systemd/system/getty@tty1.service.d")
        child.expect_exact(BASH_PROMPT)
        child.sendline('echo -en "{}" >> autologin.conf'.format(
            TTY_SERVICE_AUTOLOGIN_CONF.replace("\n", "\\n"))
        )
        child.expect_exact(BASH_PROMPT)
        child.sendline("sudo mv autologin.conf /etc/systemd/system/getty@tty1.service.d/autologin.conf")
        child.expect_exact(BASH_PROMPT)
        child.sendline("sudo systemctl enable getty@tty1.service")
        child.expect_exact(BASH_PROMPT)
        # We are done, let's exit
        child.sendline("sudo shutdown now")
        child.expect(pexpect.EOF)
        child.wait()
    # Let ay exceptions bubble up, but ensure clean-up is run
    finally:
        try:
            print('! Attempting to close process.')
            child.close()
            print("! Exit status: {}".format(child.exitstatus))
            print("! Signal status: {}".format(child.signalstatus))
        finally:
            print('! Check if {} container is still running'.format(DOCKER_CONTAINER_NAME))
            container_id = pexpect.run(
                'docker ps --filter "name={}" -q'.format(DOCKER_CONTAINER_NAME),
            )
            print(container_id)
            if container_id:
                print('! Stopping {} container'.format(DOCKER_CONTAINER_NAME))
                cmd_op, exit_status  = pexpect.run(
                    'docker stop {}'.format(DOCKER_CONTAINER_NAME), withexitstatus=True,
                )
                print("{}\n! Exit status: {}".format(cmd_op, exit_status))
            else:
                print('! Docker container was already stopped.')


def main():
    print("Downloading OS image: {}".format(OS_IMAGE_ZIP))
    zip_path = download_image_zip(OS_IMAGE_ZIP)
    print("Unzipping OS image: {}".format(zip_path))
    img_path = unzip_image(zip_path)
    print("Configuring OS to autologin: {}".format(img_path))
    update_os_image(img_path)


if __name__ == "__main__":
    main()

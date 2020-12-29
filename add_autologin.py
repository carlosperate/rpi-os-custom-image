#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a Raspberry PI OS image with Docker and QEMU to customise it."""
import os
import sys
import uuid
import shutil

import pexpect


###############################################################################
# Configuration data start

# If this script is run on its own, select here what features to update
AUTOLOGIN = True

# Configuration data end
###############################################################################

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


def launch_docker_spawn(img_path):
    """Creates a copy of the provided Raspberry Pi OS Lite image and runs it in
    QEMU inside a Docker container to configure autologin.

    :param img_path: Path to the Raspberry Pi OS Lite image to update.
    """
    img_path = os.path.abspath(img_path)
    if not os.path.isfile(img_path):
        raise Exception("Provided OS file cannot be found: {}".format(img_path))
    if not img_path.endswith(".img"):
        raise Exception("Provided OS .img file does not have the right extension: {}".format(img_path))

    original_img = img_path
    # TODO: .replace will cause issues if `.img` is present somewhere else in path
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

    child = pexpect.spawn(docker_cmd, timeout=600, encoding='utf-8')
    child.logfile = sys.stdout
    return child


def login(child):
    child.expect_exact("raspberrypi login: ")
    child.sendline(RPI_OS_USERNAME)
    child.expect_exact("Password: ")
    child.sendline(RPI_OS_PASSWORD)
    child.expect_exact(BASH_PROMPT)


def add_autologin(child):
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


def run_edits(img_path, needs_login=True, autologin=None):
    print("Staring Raspberry Pi OS customisation: {}".format(img_path))
    try:
        child = launch_docker_spawn(img_path)
        if needs_login:
            login(child)
        if autologin or (autologin is None and AUTOLOGIN):
            add_autologin(child)
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


if __name__ == "__main__":
    # We only use the first argument to receive a path to the .img file
    run_edits(sys.argv[1])

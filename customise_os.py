#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a Raspberry PI OS image with Docker and QEMU to customise it."""
import os
import sys
import uuid
import time
import subprocess
from datetime import datetime

import pexpect


###############################################################################
# Configuration data start

# If this script is run on its own, select here what features to update
AUTOLOGIN = True
SSH = False
EXPAND_FS = False

# Configuration data end
###############################################################################

DOCKER_IMAGE = "lukechilds/dockerpi:vm"

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


def set_username_password(img_path, username=RPI_OS_USERNAME, password=RPI_OS_PASSWORD):
    """Create the user and password in the Raspberry Pi OS image."""
    cmds_to_run = [
        # Create a userconf file with the username and encrypted password
        f'echo -n "{username}:" >> userconf',
        f'echo "{password}" | openssl passwd -6 -stdin | tee -a userconf',
        # Workout the FAT32 boot filesystem offset (offset in bytes,
        # fdisk info in sectors) and copy the userconf there
        f"OFFSET=$(fdisk -lu {img_path} "
            "| awk '/^Sector size/ {sector_size=$4} /FAT32 \(LBA\)/ {print $2 * sector_size}') && "
            f"mcopy -o -i {img_path}" "@@${OFFSET} userconf ::/",
        f"rm -d userconf",
    ]

    for cmd in cmds_to_run:
        print(f"Running command: {cmd}")
        subprocess.run(cmd, shell=True, check=True)


def launch_docker_spawn(img_path):
    """Runs the provided Raspberry Pi OS Lite image in QEMU inside a Docker
    container and returns a child process to run commands inside it.

    :param img_path: Path to the Raspberry Pi OS Lite image to update.
    """
    img_path = os.path.abspath(img_path)
    if not os.path.isfile(img_path):
        raise Exception("Provided OS file cannot be found: {}".format(img_path))
    if not img_path.endswith(".img"):
        raise Exception("Provided OS .img file does not have the right extension: {}".format(img_path))

    docker_container_name = "rpi-os-{}".format(str(uuid.uuid4())[:8])
    docker_cmd = " ".join([
        "docker",
        "run",
        "-it",
        "--rm",
        "--name {}".format(docker_container_name),
        "-v {}:/sdcard/filesystem.img".format(img_path),
        DOCKER_IMAGE
    ])
    print("Docker cmd: {}".format(docker_cmd))

    child = pexpect.spawn(docker_cmd, timeout=600, encoding='utf-8')
    child.logfile = sys.stdout

    return child, docker_container_name


def login(child):
    child.expect_exact("raspberrypi login: ")
    # Since the 2022-04 bullseye release the first boot wizard creates an
    # an account based on userconf.
    # This first boot wizard runs in a different session as a different user,
    # so sometimes it can take a while before it's able to create the user
    time.sleep(90)
    child.sendline(RPI_OS_USERNAME)
    child.expect_exact("Password: ")
    time.sleep(5)
    child.sendline(RPI_OS_PASSWORD)
    child.expect_exact(BASH_PROMPT)


def enable_autologin(child):
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


def enable_ssh(child, img_tag):
    """Enable SSH on boot.

    From Bullseye 2022-09-26, the 'systemctl' method SSH fails to start on boot:
        [FAILED] Failed to start Regenerate SSH host keys.
        [FAILED] Failed to start OpenBSD Secure Shell server.
    So we can use 'raspi-config' as the "new method", but the do_ssh option
    might not be available in older Pi OS releases, so still run the
    "old method" in those.
    https://www.raspberrypi.com/documentation/computers/configuration.html#the-raspi-config-command-line-interface

    For versions newer than 2022-09-26, and older than ????-??-??, it also
    need to update 'raspberrypi-sys-mods'
    https://github.com/RPi-Distro/pi-gen/issues/682#issuecomment-1001047955
    https://github.com/raspberrypi/linux/issues/5390
    https://github.com/RPi-Distro/pi-gen/issues/682
    https://github.com/RPi-Distro/raspberrypi-sys-mods/pull/71

    :param child: The pexpect spawn child process to run commands in.
    :param img_tag: The date of the image in YYYY-MM-DD format.
    """
    try:
        img_date = datetime.strptime(img_tag, "%Y-%m-%d")
    except ValueError:
        # Not a valid date to compare, default to the new method
        pass
    else:
        # Old method should still work in older versions where raspi-config might not have 'do_ssh'
        if img_date < datetime(year=2022, month=9, day=26):
            child.sendline("sudo systemctl enable ssh")
            child.expect_exact(BASH_PROMPT)
            return
        if img_date <= datetime(year=2022, month=9, day=26):
            # For versions between 2022-09-26 and ????-??-??, we need to
            # update 'raspberrypi-sys-mods' and then run 'raspi-config'
            child.sendline("sudo apt install -y raspberrypi-sys-mods")
            child.expect_exact(BASH_PROMPT)

    # Current method uses raspi-config, which should be supported in all buster+ releases
    child.sendline("sudo raspi-config nonint do_ssh 0")
    child.expect_exact(BASH_PROMPT)


def expand_root_fs(child):
    # Temporary solution for older Raspbian issue: sda2 is not on SD card. Don't know how to expand
    # https://www.raspberrypi.org/forums/viewtopic.php?t=44856#p563673
    # child.sendline("sed -e 's/mmcblk0p/sda/' -e 's/mmcblk0/sda/' /usr/bin/raspi-config > ~/raspi-config")
    # child.expect_exact(BASH_PROMPT)
    # child.sendline("chmod +x ~/raspi-config")
    # child.expect_exact(BASH_PROMPT)
    # child.sendline("sudo ~/raspi-config --expand-rootfs")
    # child.expect_exact(BASH_PROMPT)
    # child.sendline("rm ~/raspi-config")
    # child.expect_exact(BASH_PROMPT)
    # end of old solution
    child.sendline("sudo raspi-config --expand-rootfs")
    child.expect_exact(BASH_PROMPT)


def close_container(child, docker_container_name):
    try:
        print('! Attempting to close process.')
        child.close()
        print("! Exit status: {}".format(child.exitstatus))
        print("! Signal status: {}".format(child.signalstatus))
    finally:
        print('! Check if {} container is still running'.format(docker_container_name))
        container_id = pexpect.run(
            'docker ps --filter "name={}" -q'.format(docker_container_name),
        )
        print(container_id)
        if container_id:
            print('! Stopping {} container'.format(docker_container_name))
            cmd_op, exit_status  = pexpect.run(
                'docker stop {}'.format(docker_container_name), withexitstatus=True,
            )
            print("{}\n! Exit status: {}".format(cmd_op, exit_status))
        else:
            print('! Docker container was already stopped.')


def run_edits(img_path, img_tag=None, needs_login=True, autologin=None, ssh=None, expand_fs=None):
    print("Staring Raspberry Pi OS customisation: {}".format(img_path))

    # Since bullseye 2022-04-07 an extra step is needed to create a username and password
    set_username_password(img_path)

    # Increase the image by 1 GB using qemu-img
    if expand_fs or (expand_fs is None and EXPAND_FS):
        print("Expanding {} image +1GB:".format(img_path))
        print(pexpect.run("qemu-img resize {} +1G".format(img_path)))

    child, docker_container_name = None, None
    try:
        child, docker_container_name = launch_docker_spawn(img_path)
        if needs_login:
            login(child)
        if autologin or (autologin is None and AUTOLOGIN):
            enable_autologin(child)
        if ssh or (ssh is None and SSH):
            enable_ssh(child, img_tag)
        if expand_fs or (expand_fs is None and EXPAND_FS):
            expand_root_fs(child)
        # We are done, let's exit
        child.sendline("sudo shutdown now")
        child.expect(pexpect.EOF)
        child.wait()
    # Let ay exceptions bubble up, but ensure clean-up is run
    finally:
        if child:
            close_container(child, docker_container_name)


if __name__ == "__main__":
    # We only use the first argument to receive a path to the .img file
    run_edits(sys.argv[1])

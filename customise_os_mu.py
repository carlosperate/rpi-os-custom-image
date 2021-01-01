#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run a Raspberry PI OS image with Docker and QEMU to add:
- Autologin
- SSH
- Larger disk space
- Installed the Mu apt packages
"""
import os
import sys
import uuid

import pexpect

import customise_os


def install_mu_apt_dependencies(child):
    child.sendline("df -h")
    child.expect_exact(customise_os.BASH_PROMPT)
    child.sendline("sudo apt-get update -qq")
    child.expect_exact(customise_os.BASH_PROMPT)
    # Break down the install in multiple commands to kee the time per command low 
    child.sendline("sudo apt-get install -y git xvfb python3-pip")
    child.expect_exact(customise_os.BASH_PROMPT)
    child.sendline(
        "sudo apt-get install -y python3-pyqt5 python3-pyqt5.qtserialport"
    )
    child.expect_exact(customise_os.BASH_PROMPT)
    child.sendline(
        "sudo apt-get install -y python3-pyqt5.qsci python3-pyqt5.qtsvg python3-pyqt5.qtchart"
    )
    child.expect_exact(customise_os.BASH_PROMPT)
    child.sendline(
        "sudo apt-get install -y libxmlsec1-dev libxml2 libxml2-dev libxkbcommon-x11-0 libatlas-base-dev"
    )
    child.expect_exact(customise_os.BASH_PROMPT)
    child.sendline("df -h")
    child.expect_exact(customise_os.BASH_PROMPT)


def run_edits(img_path, needs_login=True):
    print("Staring Raspberry Pi OS Mu customisation: {}".format(img_path))

    try:
        child, docker_container_name = customise_os.launch_docker_spawn(img_path)
        if needs_login:
            customise_os.login(child)
        else:
            child.expect_exact(customise_os.BASH_PROMPT)
        install_mu_apt_dependencies(child)
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


if __name__ == "__main__":
    # We only use the first argument to receive a path to the .img file
    run_edits(sys.argv[1])

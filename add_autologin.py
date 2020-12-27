import sys
import uuid
from datetime import datetime

import pexpect

###############################################################################
# Configuration data start

# Add your path to the Raspberry Pi OS Lite image here
OS_IMG_PATH = "/Users/microbit-carlos/Downloads/pidocktest/2020-12-02-raspios-buster-armhf-lite.img"

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


def get_docker_run_cmd():
    docker_cmd = [
        "docker",
        "run",
        "-it",
        "--rm",
        "--name {}".format(DOCKER_CONTAINER_NAME),
        "-v {}:/sdcard/filesystem.img".format(OS_IMG_PATH),
        DOCKER_IMAGE
    ]
    return " ".join(docker_cmd)


def main():
    try:
        child = pexpect.spawn(get_docker_run_cmd(), timeout=600, encoding='utf-8')
        child.logfile = sys.stdout
        child.expect_exact("raspberrypi login: ")
        child.sendline(RPI_OS_USERNAME)
        child.expect_exact("Password: ")
        child.sendline(RPI_OS_PASSWORD)
        child.expect_exact(BASH_PROMPT)
        child.sendline("ls -a")
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
        # We done, let's exit
        child.sendline("sudo shutdown now")
        child.expect(pexpect.EOF)
        child.wait()
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
    main()

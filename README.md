# Raspberry Pi OS customised images

Minimally customised Raspberry Pi OS images.

The main reason these have been created is to be able to run them in automated
CI testing with https://github.com/carlosperate/docker-qemu-rpi-os.

Currently the following images are being created:
- Raspberry Pi OS Lite + autologin enabled

Other upcoming images:
- Raspberry Pi OS Lite + autologin enabled + resized image (+1GB)
- Raspberry Pi OS Lite + autologin enabled + resized image (+1GB) + specific app dependencies
    - This is a special case image for doing CI testing on personal projects


## How does it work

It uses a method very similar to this article (thank you Ben!):
https://www.hardill.me.uk/wordpress/2020/02/21/building-custom-raspberry-pi-sd-card-images/

In this case all is encapsulated in a Python script:
- Download an official Raspberry Pi OS Lite image
- Uncompress it
- Load the .img in QEMU using the Docker images provided by
  [dockerpi](https://github.com/lukechilds/dockerpi/)
- Use the [Pexpect(https://pexpect.readthedocs.io) library to interact with
  the Raspberry Pi OS terminal and configure everything necessary
- Zip the image for release

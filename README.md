# Raspberry Pi OS customised images

Minimally customised Raspberry Pi OS images.

The main reason these have been created is to be able to run them in automated
CI testing with https://github.com/carlosperate/docker-qemu-rpi-os.

Currently the following images are being created:
- Raspberry Pi OS Lite + autologin enabled
- Raspberry Pi OS Lite + autologin + ssh enabled

Other upcoming images:
- Raspberry Pi OS Lite + autologin + ssh + resized image (+1GB)
- Raspberry Pi OS Lite + autologin + ssh + resized image (+1GB) + specific app dependencies
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


## How to run this project

Requirements:
- Linux or macOS (it uses `expect`)
- Docker
- Python 3
- An internet connection while the Python script is running

Install the Python dependencies (much better in a virtual environment):

```
pip install -r requirements.txt
```

Run the Python script:
```
python run_all.py
```

### Change default options

Ideally the options should be selectable via command line arguments, but
until that is implemented there are other options in the meantime.

#### OS customisation options

You can run the `customise_os.py` Python script directly if you'd like to
modify an existing Raspberry Pi OS image (e.g., if you've downloaded a specific
one).

The path to the `.img` file needs to be provided as a command line argument:

```
python customise_os.py path/to/my.img
```

The options in the `customise_os.py` header can be changed to select what to
modify:

```python
###############################################################################
# Configuration data start

# If this script is run on its own, select here what features to update
AUTOLOGIN = True
SSH = True

# Configuration data end
###############################################################################
```

These options do not affect `run_all.py` runs, only `customise_os.py`.

### Download OS image options

You can run the `download_os.py` Python script directly if you'd like to
download an unzip a different Raspberry Pi OS image.


The URL should be passed as a command line argument:

```
python download_os.py https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2020-08-24/2020-08-20-raspios-buster-armhf-lite.zip
```

Executing the script without arguments will download the default image:

```
python download_os.py 
```

The global variables at the top of `download_os.py` can be edited to change the
default:

```python
###############################################################################
# Configuration data start

# URL of the Raspberry Pi OS Lite zip file to download and check
# Find options in https://downloads.raspberrypi.org/raspios_lite_armhf/images/
OS_IMAGE_ZIP = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2020-08-24/2020-08-20-raspios-buster-armhf-lite.zip"
OS_IMAGE_SHA = "https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2020-08-24/2020-08-20-raspios-buster-armhf-lite.zip.sha256"
OS_IMAGE_SHA_TYPE = "256"

# Configuration data end
###############################################################################
```

Changing these URLs *__will affect__* `run_all.py` as well.

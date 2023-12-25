FROM ubuntu:22.04

LABEL org.opencontainers.image.title="RPi OS Custome Imager"
LABEL org.opencontainers.image.description="Docker image with the tooling to customise Raspberry Pi OS images."
LABEL org.opencontainers.image.authors="Carlos Pereira Atencio <carlosperate@embeddedlog.com>"
LABEL org.opencontainers.image.source="https://github.com/carlosperate/rpi-os-custom-image"

# Installing dependencies to download, run and modify the OS images
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends qemu-utils docker.io systemctl fdisk mtools openssl python3 python3-pip && \
    apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Enable docker & configure python as python3
RUN systemctl enable docker && \
    usermod -aG docker $(whoami) && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Installing Python dependencies
COPY requirements.txt /home/
RUN python3 -m pip --no-cache-dir install --upgrade pip && \
    python3 -m pip --no-cache-dir install -r /home/requirements.txt && \
    rm /home/requirements.txt

WORKDIR /home/

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download and run a Raspberry PI OS image with Docker and QEMU to customise it.
"""
import shutil

import download_os
import customise_os
import customise_os_mu


def main():
    # Download and unzip OS image
    compressed_path = download_os.download_compressed_image()
    img_path = download_os.decompress_image(compressed_path)
    img_tag = download_os.DEFAULT_IMG_TAG

    # Create a copy of the original image and configure it with autologin
    autologin_img = img_path.replace(".img", "-autologin.img")
    shutil.copyfile(img_path, autologin_img)
    customise_os.run_edits(
        autologin_img, img_tag=img_tag, needs_login=True, autologin=True, ssh=False, expand_fs=False
    )

    # Create a copy of the original image and configure it autologin + ssh
    autologin_ssh_img = img_path.replace(".img", "-autologin-ssh.img")
    shutil.copyfile(img_path, autologin_ssh_img)
    customise_os.run_edits(
        autologin_ssh_img,  img_tag=img_tag, needs_login=True, autologin=True, ssh=True, expand_fs=False
    )

    # Copy original image and configure it autologin + ssh + expanded filesystem
    autologin_ssh_fs_img = img_path.replace(".img", "-autologin-ssh-expanded.img")
    shutil.copyfile(img_path, autologin_ssh_fs_img)
    customise_os.run_edits(
       autologin_ssh_fs_img, img_tag=img_tag, needs_login=True, autologin=True, ssh=True, expand_fs=True
    )

    # Copy expanded image (last one created) and install Mu dependencies
    mu_img = img_path.replace(".img", "-mu.img")
    shutil.copyfile(autologin_ssh_fs_img, mu_img)
    customise_os_mu.run_edits(mu_img, needs_login=False)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dowload and run a Raspberry PI OS image with Docker and QEMU to customise it.
"""
import shutil

import download_os
import customise_os
import customise_os_mu


def main():
    # Download and unzip OS image
    zip_path = download_os.download_image_zip()
    img_path = download_os.unzip_image(zip_path)

    # Create a copy and configure image with autologin
    autologin_img = img_path.replace(".img", "-autologin.img")
    shutil.copyfile(img_path, autologin_img)
    customise_os.run_edits(
        autologin_img, needs_login=True, autologin=True, ssh=False, expand_fs=False
    )

    # Create a copy and configure image with autologin + ssh
    autologin_ssh_img = img_path.replace(".img", "-autologin-ssh.img")
    shutil.copyfile(img_path, autologin_ssh_img)
    customise_os.run_edits(
        autologin_ssh_img, needs_login=True, autologin=True, ssh=True, expand_fs=False
    )

    # Create a copy and configure image with autologin + ssh + expanded filesystem
    autologin_ssh_img = img_path.replace(".img", "-autologin-ssh-expanded.img")
    shutil.copyfile(img_path, autologin_ssh_img)
    customise_os.run_edits(
       autologin_ssh_img, needs_login=True, autologin=True, ssh=True, expand_fs=True
    )

    # Create a copy and configure image with autologin + ssh
    mu_img = img_path.replace(".img", "-mu.img")
    shutil.copyfile(autologin_ssh_img, mu_img)
    customise_os_mu.run_edits(mu_img, needs_login=False)


if __name__ == "__main__":
    main()

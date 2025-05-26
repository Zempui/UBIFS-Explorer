#!/bin/bash
# CLEAN or unmount script:
sudo umount ./mount
rmdir ./mount
sudo ubidetach -p /dev/mtd0
sudo modprobe -a -r ubifs ubi nandsim mtdblock mtd
# deleted if required
#unlink files.img ubi.img

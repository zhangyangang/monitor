#!/bin/bash

CURRENT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
DRIVER_DIR=/var/lib/nvidia-docker/volumes/nvidia_driver/latest
MNT_DIR=/host
MNT_DRIVER_DIR=${MNT_DIR}${DRIVER_DIR}
DRIVER_TARGET=/usr/local/nvidia

# DRIVER_DIR is a symlink
if [ -L $MNT_DRIVER_DIR ]; then
    TARGET=$(readlink $MNT_DRIVER_DIR)
    MNT_TARGET=${MNT_DIR}${TARGET}
    echo Found driver in $MNT_TARGET
    ln -s $MNT_TARGET $DRIVER_TARGET
else
   echo No driver found
fi
python3 ${CURRENT_DIR}/monitor.py

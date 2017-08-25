#!/bin/bash

CURRENT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
MNT_DIR=/host
MNT_DRIVER_DIR=${MNT_DIR}${NVIDIA_DRIVER_DIR}
DRIVER_TARGET=/usr/local/nvidia

# DRIVER_DIR is a symlink
if [ -L $MNT_DRIVER_DIR ]; then
    DRIVER=$(cd $MNT_DRIVER_DIR; pwd -P)
    echo Found driver in $DRIVER
    ln -s $DRIVER $DRIVER_TARGET
else
   echo No driver found
fi

export PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:${PATH}
export LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64

python3 ${CURRENT_DIR}/monitor.py

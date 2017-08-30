#!/bin/bash

CURRENT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
MNT_DIR=/host
MNT_DRIVER_DIR=${MNT_DIR}${NVIDIA_DRIVER_DIR}
DRIVER_TARGET=/usr/local/nvidia

# DRIVER_DIR is a symlink
if [ -L $MNT_DRIVER_DIR ]; then
    LINK_TARGET=$(readlink $MNT_DRIVER_DIR)
    if [[ ${LINK_TARGET:0:1} = / ]]; then
        DRIVER=$(realpath $MNT_DIR/$LINK_TARGET)
    else
        DRIVER=$(realpath $MNT_DRIVER_DIR)
    fi
    #DRIVER=$(cd $MNT_DRIVER_DIR; pwd -P)
    echo Found driver in $DRIVER
    ln -s $DRIVER $DRIVER_TARGET
else
   echo No driver found. $NVIDIA_DRIVER_DIR must be a link.
fi

export PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:${PATH}
export LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64

python3 ${CURRENT_DIR}/monitor.py

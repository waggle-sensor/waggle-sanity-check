#!/bin/bash

check_device() {
    dev="$1"
    for _ in $(seq 10); do
        echo R > "$dev"
        if timeout 5 grep -q -m 1 Acc "$dev"; then
            return
        fi
    done
    return 1
}

if ! devices=$(ls /dev/serial/by-id/*FTDI_FT232R*); then
    echo "no device found"
    exit 1
fi

for device in $devices; do
    if ! check_device "$device"; then
        echo "could not read Acc value for $device"
        exit 2
    fi
done

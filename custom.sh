#!/bin/bash -e

apt-get update
apt-get install --no-install-recommends -y python3-pip

# install python package dependencies
pip3 install --ignore-installed --target="${1}/etc/waggle/sanity/python-deps/" \
    https://github.com/waggle-sensor/unifi_switch_client/releases/download/0.0.8/unifi_switch_client-0.0.8-py3-none-any.whl

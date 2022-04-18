#!/usr/bin/env python3

import argparse
import json
import sys

import urllib3
from unifi_switch_client import UnifiSwitchClient

# work-around to suppress `InsecureRequestWarning` warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user",
        dest="user",
        action="store",
        type=str,
        default="ubnt",
        help="Switch username",
    )
    parser.add_argument(
        "--password",
        dest="password",
        action="store",
        type=str,
        default="ubnt",
        help="Switch password",
    )
    args = parser.parse_args()

    with UnifiSwitchClient(
        host=f"https://switch", username=args.user, password=args.password
    ) as client:
        ret, info = client.get_device_info()
        if ret:
            fwvers = info["identification"]["firmwareVersion"]
            print(f"Firmware Version: {fwvers}")
            sys.exit(0)
        else:
            print(f"Could not get system information: {info}")
            sys.exit(1)

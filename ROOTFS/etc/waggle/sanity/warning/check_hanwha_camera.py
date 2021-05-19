#!/usr/bin/env python3

import sys
import json
import urllib.error, urllib.request
import time

def read_camera_manifest(path='/etc/waggle/node_manifest.json'):
    with open(path, 'r') as file:
        manifest = json.loads(file.read())
        if 'cameras' not in manifest:
            raise Exception(f'No cameras in the manifest: {path}')
        else:
            for camera in manifest['cameras']:
                if camera['present'] == True:
                    yield camera


def http_request(url, user='waggle', pw='Waggle1@34', timeout=2):
    passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, user, pw)
    authhandler = urllib.request.HTTPDigestAuthHandler(passman)
    opener = urllib.request.build_opener(authhandler)
    urllib.request.install_opener(opener)
    headers = {'Accept': 'application/json'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.code, response.read()
    except urllib.error.URLError:
        return 404, b''


def check():
    code_when_exit = 0
    cameras = list(read_camera_manifest())
    # if no camera listed, we do not check
    if len(cameras) == 0:
        print('No cameras listed in the manifest. Exiting...')
        exit(code_when_exit)

    for n in range(10, 20, 1):
        # get device info
        return_code, body_json = http_request(f'http://10.31.81.{n}/stw-cgi/system.cgi?msubmenu=deviceinfo&action=view')
        if return_code != 200:
            continue
        device_info = json.loads(body_json)

        return_code, body_json = http_request(f'http://10.31.81.{n}/stw-cgi/video.cgi?msubmenu=snapshot&action=view')
        if return_code != 200:
            print(f'[ERROR] Failed to get a snapshot from 10.31.81.{n}', file=sys.stderr)
            code_when_exit = 1

        # check if the device model is listed in manifest
        camera_to_delete = []
        for camera in cameras:
            if camera['model'] in device_info['Model']:
                camera_to_delete.append(camera)
                break

        if len(camera_to_delete) == 0:
            print(f'[ERROR] The camera model {device_info["Model"]} of 10.31.81.{n} is not listed in the manifest', file=sys.stderr)
            code_when_exit = 1
        else:
            for c in camera_to_delete:
                cameras.remove(c)
            print(f'Checked: {device_info["Model"]} at 10.31.81.{n}')

    if len(cameras) > 0:
        code_when_exit = 1
        for remaining_camera in cameras:
            print(f'[ERROR]{remaining_camera} remained unchecked', file=sys.stderr)
    
    exit(code_when_exit)

if __name__ == '__main__':
    check()

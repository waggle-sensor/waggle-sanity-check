#!/bin/bash -e

docker run --rm \
  -e NAME="waggle-sanity-check" \
  -e DESCRIPTION="NX Sanity Check Services" \
  -e LATE_CMD="./custom.sh" \
  -v "$PWD:/repo" \
  joe_deb:latest

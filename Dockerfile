FROM python:3-buster

RUN mkdir -p /deb/ /ROOTFS/
ADD deb /deb/
ADD ROOTFS /ROOTFS/

COPY release.sh .

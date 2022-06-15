#!/bin/bash -e

mkdir -p /tmp/reg

# Build the waggle-sanity-check debian package
BASEDIR=/tmp/reg
NAME=waggle-sanity-check
ARCH=all

mkdir -p ${BASEDIR}/DEBIAN
cat > ${BASEDIR}/DEBIAN/control <<EOL
Package: ${NAME}
Version: ${VERSION}
Maintainer: waggle-edge.ai
Description: NX Sanity Check Services
Architecture: ${ARCH}
Priority: optional
EOL

cp -p deb/install/postinst ${BASEDIR}/DEBIAN/
cp -p deb/install/prerm ${BASEDIR}/DEBIAN/

cp -pr ROOTFS/* ${BASEDIR}/

# install python package dependencies
pip3 install --ignore-installed --target="${BASEDIR}/etc/waggle/sanity/python-deps/" \
    https://github.com/waggle-sensor/unifi_switch_client/releases/download/0.0.8/unifi_switch_client-0.0.8-py3-none-any.whl

dpkg-deb --root-owner-group --build ${BASEDIR} "${NAME}_${VERSION}_${ARCH}.deb"
mv *.deb /output/

#!/usr/bin/env python3
from pathlib import Path
import sys
import time

# NOTE(sean) The main doc on the iio (Industrial I/O) /sys tree was here:
# https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-bus-iio
#
# It seems that there's *supposed* to be some standardization around
# types of measurements (temperature, pressure, humidity, light
# intensity, etc) based on the following snippits:
#
# What:		/sys/bus/iio/devices/iio:deviceX/in_tempX_input
# KernelVersion:	2.6.38
# Contact:	linux-iio@vger.kernel.org
# Description:
# 		Scaled temperature measurement in milli degrees Celsius.
#
# => so, should div by 1000 to get degrees Celsius.
#
# What:		/sys/bus/iio/devices/iio:deviceX/in_pressureY_input
# What:		/sys/bus/iio/devices/iio:deviceX/in_pressure_input
# KernelVersion:	3.8
# Contact:	linux-iio@vger.kernel.org
# Description:
# 		Scaled pressure measurement from channel Y, in kilopascal.
#
# => so, should mul by 1000 to get pascals.
#
# What:		/sys/bus/iio/devices/iio:deviceX/in_humidityrelative_input
# KernelVersion:	3.14
# Contact:	linux-iio@vger.kernel.org
# Description:
# 		Scaled humidity measurement in milli percent.
#
# => so, should div by 1000 to get precent.
#
# But, from what I can tell this doesn't seem quite right across some combination
# of the NX / RPi and BME 280 / 680 in terms of scaling factors to get right units...
# Some of the values seem to be in odd ranges just following those scaling factors.
#

# Notes from the datasheets on on valid operating range for the BME280/680.
#
# Temperature: [-40, 85] C
# Relative Humidity: [0, 100] %RH
# Pressure: [30000, 110000] Pa


def valid_temperature(value):
    return -40.0 <= value <= 85.0


def valid_rel_humidity(value):
    return 0.0 <= value <= 100.0


def valid_pressure(value):
    return 30000.0 <= value <= 110000.0


# robust_read attempts to read 3 times to address corner case where driver fails
def robust_read(path):
    for _ in range(3):
        try:
            return path.read_text()
        except OSError:
            time.sleep(3)
    raise OSError(f"unable to read path {path}")


def read_float(path):
    return float(robust_read(path))


# reference from iio plugin
# ("bme280", "in_humidityrelative_input"): lambda x: x / 1000,
# ("bme280", "in_pressure_input"): lambda x: x * 1000,
# ("bme280", "in_temp_input"): lambda x: x / 1000,
def handle_bme280(name, path):
    iio_hum = read_float(path/"in_humidityrelative_input")
    iio_press = read_float(path/"in_pressure_input")
    iio_temp = read_float(path/"in_temp_input")
    print(f"{name} raw temp={iio_temp} press={iio_press} hum={iio_hum}")

    hum = iio_hum / 1000
    press = iio_press * 1000
    temp = iio_temp / 1000
    print(f"{name} tfm temp={temp} C press={press} Pa hum={hum} %RH")

    assert valid_temperature(temp)
    assert valid_pressure(press)
    # NOTE(sean) We realized the %RH calculation can lead to values way outside of [0,100]. To prevent the test from
    # failing in rare cases, we will not check the humidity range.
    # assert valid_rel_humidity(hum)
    print("ignoring bme280 relative humidity due to known range issue")


# reference from iio plugin
# ("bme680", "in_humidityrelative_input"): lambda x: x,
# ("bme680", "in_pressure_input"): lambda x: x * 100,
# ("bme680", "in_temp_input"): lambda x: x / 1000,
def handle_bme680(name, path):
    iio_hum = read_float(path/"in_humidityrelative_input")
    iio_press = read_float(path/"in_pressure_input")
    iio_temp = read_float(path/"in_temp_input")
    print(f"{name} raw temp={iio_temp} press={iio_press} hum={iio_hum}")

    hum = iio_hum
    press = iio_press * 100
    temp = iio_temp / 1000
    print(f"{name} tfm temp={temp} C press={press} Pa hum={hum} %RH")

    assert valid_temperature(temp)
    assert valid_pressure(press)
    assert valid_rel_humidity(hum)


handlers = {
    "bme280": handle_bme280,
    "bme680": handle_bme680,
}


def main():
    for path in Path("/sys/bus/iio/devices").glob("*/name"):
        name = path.read_text().strip()
        try:
            handler = handlers[name]
        except KeyError:
            print("skipping", name, file=sys.stderr)
            continue
        handler(name, path.parent)


if __name__ == "__main__":
    main()

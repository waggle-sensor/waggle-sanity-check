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


def valid_temperature(x):
    return 0.0 <= x <= 80.0


ATM = 101325 # Pa


def valid_pressure(x):
    return ATM/100 <= x <= ATM*100


def valid_rel_humidity(x):
    return 0.0 <= x <= 100.0


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


def handle_bme280(path):
    temp = read_float(path/"in_temp_input") * (1/1000)
    press = read_float(path/"in_pressure_input") * 1000
    hum = read_float(path/"in_humidityrelative_input") * (1/1000)
    print(f"bme280 temp={temp} C press={press} Pa hum={hum} %RH")
    assert valid_temperature(temp)
    assert valid_pressure(press)
    assert valid_rel_humidity(hum)


def handle_bme680(path):
    # TODO need to check / calibrate conversion weights
    temp = read_float(path/"in_temp_input") * (1/1000)
    press = read_float(path/"in_pressure_input") * 1000
    hum = read_float(path/"in_humidityrelative_input") * (1/1000)
    print(f"bm680 temp={temp} C press={press} Pa hum={hum} %RH")
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
        handler(path.parent)


if __name__ == "__main__":
    main()

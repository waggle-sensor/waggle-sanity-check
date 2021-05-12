from pathlib import Path
import sys

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
# => so, should mul by 100 to get pascals.
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


def handle_bme280(path):
    temp = float(Path(path, "in_temp_input").read_text()) * (1/1000)
    press = float(Path(path, "in_pressure_input").read_text()) * 100
    hum = float(Path(path, "in_humidityrelative_input").read_text()) * (1/1000)
    assert valid_temperature(temp)
    assert valid_pressure(press)
    assert valid_rel_humidity(hum)
    print(f"bme280 temp={temp} C press={press} Pa hum={hum} %RH")


def handle_bme680(path):
    # TODO need to check / calibrate conversion weights
    temp = float(Path(path, "in_temp_input").read_text()) * (1/1000)
    press = float(Path(path, "in_pressure_input").read_text()) * 100
    hum = float(Path(path, "in_humidityrelative_input").read_text()) * (1/1000)
    assert valid_temperature(temp)
    assert valid_pressure(press)
    assert valid_rel_humidity(hum)
    print(f"bm680 temp={temp} C press={press} Pa hum={hum} %RH")


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

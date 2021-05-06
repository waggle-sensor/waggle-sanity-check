#!/usr/bin/env python3
from pathlib import Path
import subprocess
import time
import logging
import socket
from glob import glob
import configparser
from typing import NamedTuple, Callable
import os
import json

class SanityCheckConfig(NamedTuple):
    fatal_tests: str
    warning_tests: str
    check_mins: int
    warning_fail_led: list
    fatal_fail_led: list
    success_led: list

def read_config_section_dict(filename, section):
    config = configparser.ConfigParser()

    if not config.read(filename):
        logging.warning(f"could not read config file {filename}")
        return {}

    try:
        return dict(config[section])
    except Exception:
        logging.warning("could not read config section [%s]", section)

    return {}

def read_sanity_check_config(filename, section="all"):
    d = read_config_section_dict(filename, section)

    return SanityCheckConfig(
        fatal_tests=d.get("fatal_tests", None),
	warning_tests=d.get("warning_tests", None),
	check_mins=int(d.get("check_mins", 1)),
	fatal_fail_led=json.loads(d.get("fatal_fail_led", None)),
	warning_fail_led=json.loads(d.get("warning_fail_led", None)),
	success_led=json.loads(d.get("success_led", None)),
    )

def reset_all_sanity_leds(sanity_conf):
    for led in sanity_conf.success_led:
        subprocess.Popen( 'echo 0 > ' + led + 'brightness', shell=True, stdout=subprocess.PIPE)

    for led in sanity_conf.warning_fail_led:
        subprocess.Popen( 'echo 0 > ' + led + 'brightness', shell=True, stdout=subprocess.PIPE)

    for led in sanity_conf.fatal_fail_led:
        subprocess.Popen( 'echo 0 > ' + led + 'brightness', shell=True, stdout=subprocess.PIPE)

def set_sanity_check_led(sanity_conf, led):
    reset_all_sanity_leds(sanity_conf)
    for l in led:
        subprocess.Popen( 'echo 255 > ' + l + 'brightness', shell=True, stdout=subprocess.PIPE)

def execute_tests_in_path(tests_dir):
    led_set = False
    totalTests = 0
    totalFailed = 0
    
    logging.info(f"Executing Tests in Dir: {tests_dir}")
    for filename in os.listdir(tests_dir):    
        if filename.endswith(".test"):
            totalTests+=1

            logging.info(f"executing test {filename}")
            test_path = tests_dir+filename
            test_failed = subprocess.call(test_path)
            logging.info(f"test produced result: {test_failed}")
            
            if test_failed:
                totalFailed+=1
                led_set = True

    return led_set, totalTests, totalFailed

def update_systemd_watchdog():
    try:
        subprocess.check_call(["systemd-notify", "WATCHDOG=1"])
    except Exception:
        logging.warning("skipping reset of systemd watchdog")

def main():
    logging.basicConfig(level=logging.INFO)
    sanity_config = read_sanity_check_config("/etc/waggle/sanity/config.ini")

    while True:
        # update software watchdog
        update_systemd_watchdog()
       
        #run through plugins here
        logging.info("Executing Warning Tests")
        warning_led_set, totalNumWarnTests, numberOfWarnTestsFailed = execute_tests_in_path(sanity_config.warning_tests)
        
        logging.info("Warning Tests Complete")
        logging.info("Executing Fatal Tests")

        fatal_led_set, totalNumFatalTests, numberOfFatalTestsFailed = execute_tests_in_path(sanity_config.fatal_tests)

        logging.info("Fatal Tests Complete")
        
        logging.info("Statistics:\n")
        logging.info(f"Out of {totalNumWarnTests} warning tests {numberOfWarnTestsFailed} failed")
        logging.info(f"Out of {totalNumFatalTests} warning tests {numberOfFatalTestsFailed} failed")
        
        if not (fatal_led_set or warning_led_set):
            logging.info(f"All Tests Passed, setting led to {sanity_config.success_led}")
            set_sanity_check_led(sanity_config, sanity_config.success_led)
        elif not fatal_led_set:
            logging.info(f"Only Warning Tests Failed, setting led to {sanity_config.warning_fail_led}")
            set_sanity_check_led(sanity_config, sanity_config.warning_fail_led)
        else:
            logging.info(f"Fatal Test Failed, setting led to {sanity_config.fatal_fail_led}")
            set_sanity_check_led(sanity_config, sanity_config.fatal_fail_led)
 
        time.sleep(sanity_config.check_mins*60)

if __name__ == "__main__":
    main()

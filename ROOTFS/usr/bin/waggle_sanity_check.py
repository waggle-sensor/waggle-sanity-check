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
from os import path

class SanityCheckConfig(NamedTuple):
    fatal_tests: str
    warning_tests: str
    check_mins: int
    warning_fail_led: list
    fatal_fail_led: list
    success_led: list
    timeout_secs: int

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
	check_mins=int(d.get("check_mins", 60)),
	fatal_fail_led=json.loads(d.get("fatal_fail_led", None)),
	warning_fail_led=json.loads(d.get("warning_fail_led", None)),
	success_led=json.loads(d.get("success_led", None)),
        timeout_secs=int(d.get("timeout_secs", 60)),
    )

def report_sanity_metrics(testName, testExitCode, testSeverity):
    try:
        subprocess.check_call(["waggle-publish-metric", "sys.sanity_status." + testName, str(testExitCode), "--meta", "severity=" + testSeverity])
    except Exception:
        logging.warning("waggle-publish-metric not found. no metrics will be published")


def reset_all_sanity_leds(sanity_conf):
    for led in sanity_conf.success_led:
        subprocess.Popen( 'echo 0 > ' + led + 'brightness', shell=True, stdout=subprocess.PIPE)

    for led in sanity_conf.warning_fail_led:
        subprocess.Popen( 'echo 0 > ' + led + 'brightness', shell=True, stdout=subprocess.PIPE)

    for led in sanity_conf.fatal_fail_led:
        subprocess.Popen( 'echo 0 > ' + led + 'brightness', shell=True, stdout=subprocess.PIPE)

def set_sanity_check_led(sanity_conf, led):
    if not led_paths_exist(sanity_conf):
        logging.warning("LED Paths don't exist")
        return
    
    reset_all_sanity_leds(sanity_conf)
    for l in led:
        subprocess.Popen( 'echo 255 > ' + l + 'brightness', shell=True, stdout=subprocess.PIPE)

def led_paths_exist(sanity_config):
    success_paths = True
    warning_paths = True
    fatal_paths = True

    for led in sanity_config.success_led:
        success_paths = success_paths and path.exists(led)

    for led in sanity_config.warning_fail_led:
        warning_paths = warning_paths and path.exists(led)

    for led in sanity_config.fatal_fail_led:
        fatal_paths = fatal_paths and path.exists(led)

    return fatal_paths and success_paths and warning_paths

def execute_tests_in_path(tests_dir, tests_severity, timeout_secs):
    led_set = False
    totalTests = 0
    totalFailed = 0
    testsFailed = []

    logging.info(f"Executing Tests in Dir: {tests_dir}")
    for filename in os.listdir(tests_dir):    
        if filename.endswith(".test"):
            totalTests+=1

            logging.info(f"executing test {filename}")
            test_path = tests_dir+filename
            
            try:
                test_failed = subprocess.call(test_path, timeout=timeout_secs)
            except Exception:
                logging.info(f"Timed out while executing {filename} after {timeout_secs} seconds")
                test_failed = 127

            logging.info(f"test produced result: {test_failed}")
            report_sanity_metrics(filename[:-5], test_failed, tests_severity) 

            if test_failed:
                testsFailed.append((filename[:-5], test_failed))
                totalFailed+=1
                led_set = True

    # pet systemd watchdog
    update_systemd_watchdog() 
    return led_set, totalTests, totalFailed, testsFailed

def update_systemd_watchdog():
    try:
        subprocess.check_call(["systemd-notify", "WATCHDOG=1"])
    except Exception:
        logging.warning("skipping reset of systemd watchdog")

def main():
    logging.basicConfig(level=logging.INFO)
    sanity_config = read_sanity_check_config("/etc/waggle/sanity/config.ini")
    
    # update software watchdog
    update_systemd_watchdog()

    while True:
        #run through plugins here
        logging.info("Executing Warning Tests")
        warning_led_set, totalNumWarnTests, numberOfWarnTestsFailed, warningTestsFailed = execute_tests_in_path(sanity_config.warning_tests, "warning", sanity_config.timeout_secs)
        
        logging.info("Warning Tests Complete")
        logging.info("Executing Fatal Tests")

        fatal_led_set, totalNumFatalTests, numberOfFatalTestsFailed, fatalTestsFailed = execute_tests_in_path(sanity_config.fatal_tests, "fatal", sanity_config.timeout_secs)

        logging.info("Fatal Tests Complete\n")
        
        logging.info("Test Resuslts:")
        logging.info(f"Warning [{totalNumWarnTests-numberOfWarnTestsFailed} | {totalNumWarnTests}]: {str(warningTestsFailed)}")
        logging.info(f"Fatal   [{totalNumFatalTests-numberOfFatalTestsFailed} | {totalNumFatalTests}]: {str(fatalTestsFailed)}\n")

        if not (fatal_led_set or warning_led_set):
            logging.info(f"All Tests Passed, setting led to {sanity_config.success_led}")
            set_sanity_check_led(sanity_config, sanity_config.success_led)
        elif not fatal_led_set:
            logging.info(f"Only Warning Tests Failed, setting led to {sanity_config.warning_fail_led}")
            set_sanity_check_led(sanity_config, sanity_config.warning_fail_led)
        else:
            logging.info(f"Fatal Test Failed, setting led to {sanity_config.fatal_fail_led}")
            set_sanity_check_led(sanity_config, sanity_config.fatal_fail_led)

        logging.info(f"Going to sleep for {sanity_config.check_mins} mins\n")

        minutesSlept = 0
        while True:
            time.sleep(60)
            minutesSlept += 1
            # update software watchdog
            update_systemd_watchdog()

            if (minutesSlept >= sanity_config.check_mins):
                break

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import configparser
import json
import logging
import os
import subprocess

from typing import NamedTuple


class SanityCheckConfig(NamedTuple):
    fatal_tests: str
    warning_tests: str
    check_mins: int
    warning_fail_led: list
    fatal_fail_led: list
    success_led: list
    timeout_secs: int
    interactive_tests: str


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
        interactive_tests=d.get("interactive_tests", None),
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
        subprocess.check_call(
            [
                "waggle-publish-metric",
                "sys.sanity_status." + testName,
                str(testExitCode),
                "--meta",
                "severity=" + testSeverity,
            ]
        )
    except Exception:
        logging.warning("waggle-publish-metric not found. no metrics will be published")


def execute_tests_in_path(tests_dir, tests_severity):
    totalTests = 0
    totalFailed = 0
    testsFailed = []

    logging.info(f"Executing Tests in Dir: {tests_dir}")
    for filename in os.listdir(tests_dir):
        if filename.endswith(".test"):
            totalTests += 1

            logging.info(f"executing test {filename}")
            test_path = tests_dir + filename
            test_failed = subprocess.call(test_path)
            logging.info(f"test produced result: {test_failed}")
            report_sanity_metrics(filename[:-5], test_failed, tests_severity)

            if test_failed:
                testsFailed.append((filename[:-5], test_failed))
                totalFailed += 1

    return totalTests, totalFailed, testsFailed


def main():
    logging.basicConfig(level=logging.INFO)
    sanity_config = read_sanity_check_config("/etc/waggle/sanity/config.ini")

    logging.info("Executing Interactive Tests")
    (
        totalInteractiveTests,
        numberOfInteractiveTestsFailed,
        interactiveTestsFailed,
    ) = execute_tests_in_path(sanity_config.interactive_tests, "interactive")

    logging.info("Interactive Tests Complete\n")

    logging.info("Test Resuslts:")
    logging.info(
        f"Interactive [{totalInteractiveTests-numberOfInteractiveTestsFailed} | {totalInteractiveTests}]: {str(interactiveTestsFailed)}"
    )


if __name__ == "__main__":
    main()

#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

"""
Wrapper Script for the JMX Modular Input

Copyright (C) 2021 Splunk, Inc.
All Rights Reserved

Because Splunk can't directly invoke Java , we use this python wrapper script that
simply proxys through to the Java program
"""

import import_declare_test  # isort: skip # noqa: F401
import sys
from subprocess import PIPE, Popen
from traceback import format_exc

import java_const
import splunk_ta_jmx_logger_helper as log_helper
from lxml import etree
from solnlib import utils
from splunk_ta_jmx_rh_server_field_validation import RequiredFieldValidation
from task_monitor import update_inputs

LOGGER = log_helper.setup_logging(log_name="jmx")


def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    sys.exit(2)


def loadXML():
    xml_str = sys.stdin.read()
    sys.argv.append(xml_str)
    return xml_str


def monitor_tasks(process, token, splunkd_uri):
    import time

    while process.poll() is None:
        if update_inputs:
            update_inputs(
                java_const.CONFIG_HOME[len(java_const.SPLUNK_HOME) + 1 :],  # noqa: E203
                token,
                splunkd_uri,
            )
        time.sleep(60)


# jscpd:ignore-start
def setup_signal_handler(process):
    """
    Setup signal handlers
    """

    def _handle_exit(signum, frame):
        process.kill()

    utils.handle_teardown_signals(_handle_exit)


if __name__ == "__main__":

    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            pass
        elif sys.argv[1] == "--validate-arguments":
            loadXML()
        else:
            usage()

        java_const.JAVA_MAIN_ARGS.extend(sys.argv[1:])
        # jscpd:ignore-end
        try:
            process = Popen(  # nosemgrep false-positive : The value JAVA_MAIN_ARGS is a static value which comes from the java_const.py file. It doesn't take any external/user inputs. # noqa: E501
                java_const.JAVA_MAIN_ARGS
            )
        except Exception:
            LOGGER.warning(
                "Failed to open the invoke the input. Reason: {}".format(format_exc())
            )
        else:
            process.wait()
            sys.exit(process.returncode)
    else:
        xml_str = loadXML()
        xml_str = xml_str.encode()
        token = (
            etree.fromstring(  # nosemgrep false-positive : The 'xml_str' is the arg which is fetched from the stdin while invoking the modular input. It doesn't take any user/external inputs. # noqa: E501
                xml_str
            )
            .find("session_key")
            .text
        )
        splunkd_uri = (
            etree.fromstring(  # nosemgrep false-positive : The 'xml_str' is the arg which is fetched from the stdin while invoking the modular input. It doesn't take any user/external inputs. # noqa: E501
                xml_str
            )
            .find("server_uri")
            .text
        )
        try:
            (
                java_main_args,
                cert_passwords,
            ) = RequiredFieldValidation.get_java_certificate_password(
                validation_args=java_const.JAVA_MAIN_ARGS, session_key=token
            )
            process = Popen(  # type: ignore[assignment] # nosemgrep false-positive : The value JAVA_MAIN_ARGS is a static value which comes from the java_const.py file. It doesn't take any external/user inputs. # noqa: E501
                java_main_args, stdin=PIPE, text=True
            )

        except Exception:
            LOGGER.error(
                "Failed to open the invoke the input. Reason: {}".format(format_exc())
            )

        else:
            setup_signal_handler(process)

            process.stdin.write(  # type: ignore
                xml_str.decode().replace("\n", "").replace("\r", "")
            )
            modified_cert_passwords = "\n"
            if len(cert_passwords) > 0:
                # Appending "||" as a delimiter for two inputs and "|" as delimiter for passwords
                modified_cert_passwords = (
                    "||"
                    + RequiredFieldValidation.get_key_value_format(
                        cert_passwords
                    ).replace("\n", "|")
                    + "\n"
                )
            process.stdin.write(modified_cert_passwords)
            process.stdin.flush()  # type: ignore

            monitor_tasks(process, token, splunkd_uri)

#!/usr/bin/env python
import sys
import os
import platform
import ssl
import logging
import subprocess
import socket
import requests
from requests import get
from requests.packages.urllib3.exceptions import InsecureRequestWarning

def output_subprocess(cmd1, cmd2="", timeout1=20, timeout2=20):
    """
    Execute the first command and take the output of first command as input to second command
    If cmd2 is empty, run only first command and return the result
    By default timeout for both comnnad is 20s
    """

    cmd1 = cmd1.split(" ")
    cmd2 = cmd2.split(" ")
    # if second command is empty

    ps = subprocess.run(cmd1, check=True, capture_output=True, timeout=timeout1)

    if len(cmd2)<=1:
        return ps.stdout.decode('utf-8').strip()

    final_ps = subprocess.run(cmd2, input = ps.stdout, capture_output=True, timeout=timeout2)
    return final_ps.stdout.decode('utf-8').strip()


# Create logger for consumer (logs will be emitted when poll() is called)
logger = logging.getLogger('consumer')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("cas_siem_consumer_debug.log", mode="a")
handler.setFormatter(logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s'))
logger.addHandler(handler)

# Import confluent_kafka lib
current_confluent_kafka = os.path.join(os.path.dirname(__file__), "..", "lib", "confluent_kafka_python374")
sys.path.append(current_confluent_kafka)
from confluent_kafka import Consumer, KafkaException, version, libversion
# Import Splunk Lib - http://dev.splunk.com/python
current_splunklib = os.path.join(os.path.dirname(__file__), "..", "lib", "splunklib_python374")
sys.path.append(current_splunklib)
import splunklib

logger.debug("##############################################")
logger.debug("## Citrix Analytics Splunk APP Debugging ")
logger.debug("##############################################")
logger.debug("##############################################")
logger.debug("## OS/Splunk details ")
logger.debug("##############################################")
logger.debug("Linux Details: " + str(platform.uname()))
logger.debug("Kernel Version: " + str(platform.platform()))
logger.debug("Splunk SDK Version: " + str(splunklib.__version__))
#try:
#    output_packages = output_subprocess("yum list installed")
#    logger.debug("Installed yum packages: \n" + str(output_packages))
#except:
#    pass
#try:
#    output_packages = output_subprocess("apt list --installed")
#    logger.debug("Installed apt packages: \n" + str(output_packages))
#except:
#    pass
try:
    output_splunk_version = output_subprocess(os.environ['_'] +" --version")
    logger.debug("Splunk version: " + str(output_splunk_version))
except:
    logger.warning("Splunk version: not available")
logger.debug("Splunk OpenSSL version: " + str(ssl.OPENSSL_VERSION))
logger.debug("Python Splunk version: " + str(sys.version))
logger.debug("Python Splunk version info: " + str(sys.version_info))
logger.debug("Python Splunk Confluent Kafka version: " + str(version()))
logger.debug("Python Splunk Confluent Kafka lib version: " + str(libversion()))
logger.debug("##############################################")
logger.debug("## OPENSSL/TSL details ")
logger.debug("##############################################")
try:
    pemList = output_subprocess("find -name *.pem").split('\n')
    output_m5sum = ""
    for pem in pemList:
        output_m5sum += output_subprocess("md5sum " + os.environ['SPLUNK_HOME'] + "/etc/apps/TA_CTXS_AS/bin"+pem[1:])+"/n"
    logger.debug("MD5Sum certificates: \n" + str(output_m5sum))
except:
    logger.warning("List MD5Sum failed")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logger.debug("TLS version check: " + requests.get('https://www.howsmyssl.com/a/check').json()['tls_version'])
try:
    logger.debug("## OPENSSL/TLS details - US \n")
    certificates_folder_US = os.path.join(os.path.dirname(__file__), "certificates/US/CARoot.pem")
    output_kafka_tls_1_2_broker_0_us = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-0.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_US+" -status")
    logger.debug("Kafka TLS 1_2 check US broker 0: \n" + str(output_kafka_tls_1_2_broker_0_us))
    output_kafka_tls_1_2_broker_1_us = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-1.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_US+" -status")
    logger.debug("Kafka TLS 1_2 check US broker 1: \n" + str(output_kafka_tls_1_2_broker_1_us))
    output_kafka_tls_1_2_broker_2_us = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-2.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_US+" -status")
    logger.debug("Kafka TLS 1_2 check US broker 2: \n" + str(output_kafka_tls_1_2_broker_2_us))
except:
    logger.warning("Kafka check broker US failed")
try:
    logger.debug("## OPENSSL/TLS details - EU \n")
    certificates_folder_EU = os.path.join(os.path.dirname(__file__), "certificates/EU/CARoot.pem")
    output_kafka_tls_1_2_broker_0_eu = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-eu-0.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_EU+" -status")
    logger.debug("Kafka TLS 1_2 check EU broker 0: \n" + str(output_kafka_tls_1_2_broker_0_eu))
    output_kafka_tls_1_2_broker_1_eu = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-eu-1.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_EU+" -status")
    logger.debug("Kafka TLS 1_2 check EU broker 1: \n" + str(output_kafka_tls_1_2_broker_1_eu))
    output_kafka_tls_1_2_broker_2_eu = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-eu-2.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_EU+" -status")
    logger.debug("Kafka TLS 1_2 check EU broker 2: \n" + str(output_kafka_tls_1_2_broker_2_eu))
except Exception as E:
    logger.warning(E)
try:
    logger.debug("## OPENSSL/TLS details - APS \n")
    certificates_folder_APS = os.path.join(os.path.dirname(__file__), "certificates/APS/CARoot.pem")
    output_kafka_tls_1_2_broker_0_aps = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-aps-0.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_APS+" -status")
    logger.debug("Kafka TLS 1_2 check APS broker 0: \n" + str(output_kafka_tls_1_2_broker_0_aps))
    output_kafka_tls_1_2_broker_1_aps = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-aps-1.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_APS+" -status")
    logger.debug("Kafka TLS 1_2 check APS broker 1: \n" + str(output_kafka_tls_1_2_broker_1_aps))
    output_kafka_tls_1_2_broker_2_aps = output_subprocess("echo Q", os.environ['_'] + " cmd openssl s_client -connect casnb-aps-2.citrix.com:9094 -tls1_2 -CAfile "+certificates_folder_APS+" -status")
    logger.debug("Kafka TLS 1_2 check APS broker 2: \n" + str(output_kafka_tls_1_2_broker_2_aps))
except:
    logger.warning("Kafka check broker APS failed")

logger.debug("##############################################")
logger.debug("## Network details ")
logger.debug("##############################################")
logger.debug("External IP: " + str(get('https://api.ipify.org').text))
try:
    ### US check ###
    result = len(output_subprocess("echo Q" , "telnet casnb-0.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-0.citrix.com")
    else:
        logger.debug("Connectivity check: NOT Successful to Port 9094 for host casnb-0.citrix.com, connect_ex returned: " + str(result))

    result = len(output_subprocess("echo Q" , "telnet casnb-1.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-1.citrix.com")
    else:
        logger.debug("Connectivity check: NOT Successful to Port 9094 for host casnb-1.citrix.com, connect_ex returned: " + str(result))

    result = len(output_subprocess("echo Q" , "telnet casnb-2.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-2.citrix.com")
    else:
        logger.debug("Connectivity check: NOT Successful to Port 9094 for host casnb-2.citrix.com, connect_ex returned: " + str(result))
except:
    logger.warning("Telnet US Kafka 9094 broker failed")
try:
    ### EU check ###
    result = len(output_subprocess("echo Q" , "telnet casnb-eu-0.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-eu-0.citrix.com")
    else:
        logger.debug(
            "Connectivity check: NOT Successful to Port 9094 for host casnb-eu-0.citrix.com, connect_ex returned: " + str(
                result))
    result = len(output_subprocess("echo Q" , "telnet casnb-eu-1.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-eu-1.citrix.com")
    else:
        logger.debug(
            "Connectivity check: NOT Successful to Port 9094 for host casnb-eu-1.citrix.com, connect_ex returned: " + str(
                result))
    result = len(output_subprocess("echo Q" , "telnet casnb-eu-2.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-eu-2.citrix.com")
    else:
        logger.debug(
            "Connectivity check: NOT Successful to Port 9094 for host casnb-eu-2.citrix.com, connect_ex returned: " + str(
                result))
except Exception as e:
    logger.warning(e)
try:
    ### APS check ###
    result = len(output_subprocess("echo Q" , "telnet casnb-aps-0.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-aps-0.citrix.com")
    else:
        logger.debug(
            "Connectivity check: NOT Successful to Port 9094 for host casnb-aps-0.citrix.com, connect_ex returned: " + str(
                result))
    result = len(output_subprocess("echo Q" , "telnet casnb-aps-1.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-aps-1.citrix.com")
    else:
        logger.debug(
            "Connectivity check: NOT Successful to Port 9094 for host casnb-aps-1.citrix.com, connect_ex returned: " + str(
                result))
    result = len(output_subprocess("echo Q" , "telnet casnb-aps-2.citrix.com 9094", timeout2=60))
    if result != 0:
        logger.debug("Connectivity check: Successful to Port 9094 for host casnb-aps-2.citrix.com")
    else:
        logger.debug(
            "Connectivity check: NOT Successful to Port 9094 for host casnb-aps-2.citrix.com, connect_ex returned: " + str(
                result))
except:
    logger.warning("Telnet APS Kafka 9094 broker failed")
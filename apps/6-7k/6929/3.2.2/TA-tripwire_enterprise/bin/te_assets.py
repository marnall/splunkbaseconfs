import configparser
import csv
import inspect
import logging
import os
import sys
from io import open
from sys import platform as _platform

import requests
from requests.auth import HTTPBasicAuth

import splunk_helper
from lxml import etree  # nosec
from tripwire import check_te_connection, pyDes_decrypt
from tripwire_logging import setup_logger

logger = logging.getLogger('tripwire')


def is_windows():
    return _platform == "win32"


def main():
    setup_logger()
    logger.info('Starting te_assets.py')
    session_token = splunk_helper.token_from_stdin()

    # gather parameters from setup info
    cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    cfg = configparser.ConfigParser()
    configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
    # utf-8-sig is necessary to handle config files in Windows environments
    cfg.read(configpath, encoding="utf-8-sig")

    ip_address = cfg.get("te_parameters", "workflow_host", fallback="127.0.0.1")
    # nosec
    url = f"https://{ip_address}/assetview/api/assets"
    user = cfg.get('te_parameters', 'te_username', fallback='')
    te_sslverify = cfg.get("te_parameters", "te_sslverify", fallback="0") == "1"
    directory = cfg.get('te_parameters', 'data_location', fallback='/opt/teexports')

    outputXML = os.path.join(directory, 'te_assets.xml')
    outputFile = os.path.join(directory, 'te_assets.csv')

    logger.info('Setting output to %s', outputFile)

    # decrypt password
    pm = splunk_helper.PasswordManager(auth_token=session_token)
    password = pm.get_password(username=user)
    if not password:  # if password is an empty string, fallback to DES password
        password = cfg.get("te_parameters", "te_pass", fallback="")
        password = pyDes_decrypt(password)

    logger.info("Connecting to Asset View REST API")
    check_te_connection(ip_address, user, password, te_sslverify, logger)

    # gather request params
    auth = HTTPBasicAuth(user, password)
    headers = {
        'Accept': 'application/xml',
        'Content-Type': 'application/xml',
    }

    # make request, store results
    logger.info(f"Reaching to {url}")
    location = ""
    location = cfg.get('te_parameters','te_ssl_cert_path',fallback="")

    if (te_sslverify) and (location !=""):
        logger.info(f"Enabling cert validatation, looking in {location}")
    else:
        location = te_sslverify
        logger.info(f"Cert validation in the default trust store is set: {str(te_sslverify)}")
        if (te_sslverify):
            import certifi
            logger.info(f"looking in {certifi.where()}")

    results = requests.get(url, headers=headers, auth=auth, verify=location)
    if not results.ok:
        logger.warning("Could not get asset data")
        sys.exit(1)

    # output request results to file
    logger.info(f"Saving data to {outputXML}")
    with open(outputXML, 'w') as f:
        f.write(results.text)
        f.flush()

    # set params to iterate through XML tree
    NS = 'http://scap.nist.gov/schema/asset-identification/1.1'
    header = (
        "resource",
        "assetviewid",
        "hostname",
        "tenodetype",
        "make",
        "model",
        "version",
        "ipv4",
        "ipv6",
    )

    # iterate through XML tree to generate CSV lookup file
    logger.info(f"Parsing data from {outputXML} into {outputFile}")
    with open(outputFile, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        # use the ETCompatXMLParser as the parser to overcome some
        # intermittent issue in Splunk that makes the lxml parser fail
        root = etree.parse(outputXML, etree.ETCompatXMLParser()).getroot()  # nosec
        for cd in root.iter('{%s}computing-device' % NS):
            hostname = cd.find('{%s}hostname' % NS).text

            for ei in cd.iter('{%s}extended-information' % NS):
                make = 'None'
                model = 'None'
                version = 'None'

                for eip in ei.getchildren():
                    tenodetype = ei.find('te-node-type').text

                    if eip.tag == 'make':
                        make = ei.find('make').text

                    elif eip.tag == 'model':
                        model = ei.find('model').text
                    elif eip.tag == 'version':
                        version = ei.find('version').text

            for si in cd.iter('{%s}synthetic-id' % NS):
                assetviewid = si.get('id')
                resource = si.get('resource')
                ipv4 = 'None'
                ipv6 = 'None'

                for conns in cd.iter('{%s}connections' % NS):
                    for conn in conns.iter('{%s}connection' % NS):
                        for add in conn.iter('ipAddress'):
                            for ip in add.getchildren():
                                if ip.tag == 'ip-v6':
                                    ipv6 = add.find('ip-v6').text
                                elif ip.tag == 'ip-v4':
                                    ipv4 = add.find('ip-v4').text
                                else:
                                    pass
                # write row out to lookup csv
                row = (
                    resource,
                    assetviewid,
                    hostname,
                    tenodetype,
                    make,
                    model,
                    version,
                    ipv4,
                    ipv6,
                )
                writer.writerow(row)
    logger.info("Done getting Asset Data")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logger.exception("Exception in te_assets.py")

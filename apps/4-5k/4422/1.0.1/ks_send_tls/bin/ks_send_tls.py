import datetime
import json
import os
import socket
import ssl
import sys
import logging
from logging.handlers import TimedRotatingFileHandler


def remove_file(path):
    try:
        os.remove(path)
    except OSError as e:
        print >> sys.stderr, "ERROR Could not remove the certificate file", e


"""
due to receiving the PEM certificate in one line with newlines replaced by spaces, we need to do the following:
1. remove both header and footer of the certificate
2. replace newlines by spaces
3. put back the header and footer
"""
def build_certificate(cert):
    cert = cert.replace("-----BEGIN CERTIFICATE-----", "") \
        .replace("-----END CERTIFICATE-----", "") \
        .replace(" ", "\n")
    cert = "-----BEGIN CERTIFICATE-----" + cert + "-----END CERTIFICATE-----"
    return cert


def main():
    try:
        path = os.path.join(os.environ["SPLUNK_HOME"], "var", "log", "splunk", "alert_shipper.log")
    except KeyError as e:
        print >> sys.stderr, "ERROR SPLUNK_HOME environment variable is not set, defaulting to /tmp/ks_send_tls.log", e
        path = "/tmp/ks_send_tls.log"

    logger = logging.getLogger("ks_send_tls")
    logger.setLevel(logging.DEBUG)

    handler = TimedRotatingFileHandler(path,
                                       when="d",
                                       interval=1,
                                       backupCount=5)
    logger.addHandler(handler)

    logger.info("Input arguments: {}".format(sys.argv))

    print >> sys.stderr, "INFO Firing alert action"
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        payload = json.loads(sys.argv[2])
        print(payload)
    else:
        logger.error("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)

    results_file = payload.get('results_file')
    settings = payload.get('configuration')

    logger.debug("results_file: {}".format(results_file))
    logger.debug("settings: {}".format(settings))

    host = settings.get('shipper_host')
    port = settings.get('shipper_port')

    certificate_str = settings.get('shipper_certificate')
    if certificate_str:
        certificate_str = build_certificate(certificate_str)
    logger.debug("certificate_str: {}".format(certificate_str))

    # unfortunately, the function ssl.wrap_socket only accepts the certificate as a file path.
    if certificate_str:
        with open("server.crt", "w+") as f:
            logger.debug("Writing certificate temporarily")
            f.write(certificate_str)

    logger.debug("Socket settings before creation: {}".format(settings))

    # Socket creation
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        logger.error("FATAL Failed to create the socket".format(e))
        if certificate_str:
            remove_file("server.crt")
        sys.exit(1)

    # Wrapping socket in TLS 1.2
    try:
        if certificate_str:
            ssock = ssl.wrap_socket(sock, ca_certs="server.crt", cert_reqs=ssl.CERT_REQUIRED)
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ssock = context.wrap_socket(sock, server_hostname=host)
    except ssl.SSLError as e:
        logger.error("FATAL Failed to create the SSL socket, {}".format(e))
        if certificate_str:
            remove_file("server.crt")
        sys.exit(1)

    # Socket connection
    try:
        ssock.connect((host, int(port)))
        ssock.send(json.dumps(payload))
        logger.info("Sending {}".format(json.dumps(payload)))
    except socket.error as e:
        logger.error("FATAL Failed to connect the socket: {}".format(e))
    except TypeError as e:
        logger.error("FATAL Could not parse the port, not an int: {}".format(e))
    finally:
        ssock.close()
        if certificate_str:
            remove_file("server.crt")
        sys.exit(1)


if __name__ == "__main__":
    main()

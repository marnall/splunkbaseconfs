"""manage_cacert.py. Appends custom certificates to Splunk's builtin cacert.pem"""

import os
import stat
import sys
import logging
import shutil
import glob
from logging.handlers import RotatingFileHandler


def get_and_configure_logger(logger_name: str, splunkhome: str):
    """
    Get a logger with specified name, then set up a rotating file handler.
    """

    log_level = logging.INFO

    filename = os.path.join(splunkhome, "var", "log", "splunk", f"{logger_name}.log")

    logger = logging.getLogger(logger_name)

    logger.setLevel(log_level)

    file_handler = RotatingFileHandler(
        filename, mode="a", maxBytes=10485760, backupCount=5
    )

    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    file_handler.setLevel(log_level)

    return logger


def find_app_cacerts(splunk_home):
    """
    Recently, more and more apps are shipping with their own CA bundles (nice). This
    function attempts to automatically find and patch these bundles in addition to the
    builtin Splunk ones.
    """
    app_cacerts = []
    for appdir in ["apps", "manager-apps", "master-apps"]:
        app_cacerts += glob.glob(
            os.path.join(splunk_home, "etc", appdir, "**", "cacert.pem"), recursive=True
        )

    return app_cacerts


def main(splunk_home, logger):
    """Main function"""

    # At or around Splunk 8, Splunk switched to using certifi. Before then cacert.pem is found in
    # the requests module.
    cacert_paths = [
        os.path.join(
            splunk_home, "lib", "python2.7", "site-packages", "requests", "cacert.pem"
        ),
        os.path.join(
            splunk_home, "lib", "python2.7", "site-packages", "certifi", "cacert.pem"
        ),
        os.path.join(
            splunk_home, "lib", "python3.7", "site-packages", "certifi", "cacert.pem"
        ),
        os.path.join(
            splunk_home, "lib", "python3.9", "site-packages", "certifi", "cacert.pem"
        ),
    ]

    cacert_paths += find_app_cacerts(splunk_home)

    # Look in slave/peer-apps first, and if those don't exist just use what's in apps
    appdirs = ["slave-apps", "peer-apps", "apps"]
    custom_cert_path = None
    for appdir in appdirs:
        custom_cert_path = os.path.join(
            splunk_home, "etc", appdir, "TA-certmanager", "cert", "[!README]*"
        )
        if os.path.exists(custom_cert_path):
            break

    if not custom_cert_path:
        logger.error("Failed to find a custom cert path.")
        sys.exit()

    for cacert_path in cacert_paths:
        parent_path = os.path.dirname(cacert_path)
        backup_path = os.path.join(parent_path, "cacert_orig.pem")

        # Try to give self write permission if possible
        try:
            with open(cacert_path, "ab") as cacert_f:
                if not cacert_f.writable():
                    raise IOError()
        except IOError:
            try:
                current_perms = os.stat(cacert_path).st_mode
                os.chmod(cacert_path, current_perms | stat.S_IWUSR)
                logger.info("Added write permission to %s", cacert_path)
            except:  # noqa: E722
                logger.error("Failed to add write permission to %s", cacert_path)
                continue

        if not os.path.isfile(cacert_path):
            continue
        if not os.path.isfile(backup_path):
            shutil.copyfile(cacert_path, backup_path)
        with open(cacert_path, "rb") as cacert_f_read:
            cacert_content = cacert_f_read.read()

        try:
            with open(cacert_path, "ab") as cacert_f_append:
                for custom_cert in glob.glob(custom_cert_path):
                    with open(custom_cert, "rb") as custom_f:
                        # Custom certs may have Windows-style newlines. This fixes that.
                        chain = custom_f.read().replace(b"\r\n", b"\n")
                        if chain not in cacert_content:
                            logger.info("Appending %s to %s", custom_cert, cacert_path)
                            if cacert_content and cacert_content[-1] != b"\n":
                                cacert_f_append.write(b"\n")
                            cacert_f_append.write(chain)
                        else:
                            logger.debug(
                                "Skipping write because cacert.pem already includes "
                                "custom cert"
                            )
        except IOError:
            logger.error(
                "Couldn't open %s. TA-certmanager needs to be able to write to this file",
                cacert_path,
            )
            sys.exit()


if __name__ == "__main__":
    try:
        SPLUNK_HOME = os.environ["SPLUNK_HOME"]  # pylint: disable=invalid-name
    except KeyError:
        sys.exit("SPLUNK_HOME environment variable not found")

    certmanager_logger = get_and_configure_logger("certmanager", splunkhome=SPLUNK_HOME)
    try:
        main(SPLUNK_HOME, certmanager_logger)
    except Exception as exc:  # pylint: disable=broad-except
        certmanager_logger.error(
            "Unhandled exception during execution: %s", str(exc), exc_info=True
        )

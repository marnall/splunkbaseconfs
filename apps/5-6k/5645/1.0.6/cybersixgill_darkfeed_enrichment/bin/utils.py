"""Provide common utility functions for the CyberSixgill Darkfeed enrichment app."""

from logging import Formatter, Logger, getLogger, handlers
from pathlib import Path
from sys import path as sys_path
from typing import Any, Optional, Union

from proxy_setup import getproxy

sys_path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from os import environ

from requests import Session
from splunk import setupSplunkLogger
from splunklib.client import StoragePasswords

CHANNEL_ID = "7d274d05e666cfa5a95aac2182a142b7"
APP_NAME = "cybersixgill_darkfeed_enrichment"
SPLUNK_HOME = environ["SPLUNK_HOME"]


# get_credentials
def get_credentials(
    passwords: StoragePasswords,
    realm: str = "cybersixgill_realm",
) -> tuple[Optional[str], Optional[str]]:
    """Retrieve client credentials from Splunk's storage passwords.

    Args:
        passwords (StoragePasswords): Splunk storage passwords object
        realm (str, optional): The realm to search for credentials. Defaults to "cybersixgill_realm".

    Returns:
        tuple[Optional[str], Optional[str]]: A tuple containing (client_id, client_secret)

    """
    client_id = client_secret = None
    for credential in passwords:
        if credential.content.get("realm") == realm:
            client_id, client_secret = (
                credential.content.get("username"),
                credential.content.get("clear_password"),
            )
    return client_id, client_secret


# Get session with proxy
def get_session_with_proxy() -> Session:
    """Create and return a requests Session object configured with proxy settings.

    Returns:
        Session: A requests Session object with proxy configuration

    """
    client_session = Session()
    client_session.proxies = getproxy()
    return client_session


# process records
def process_records(
    records: list[dict[str, Any]], logger: Logger,
) -> Union[list[dict[str, Any]], Exception]:
    """Process and transform CyberSixgill records into a standardized format.

    Args:
        records (list[dict[str, Any]]): List of raw CyberSixgill records
        logger (Logger): Logger instance for error logging

    Returns:
        Union[list[dict[str, Any]], Exception]: 
            - List of processed records with standardized fields if successful
            - Exception object if processing fails

    """
    try:
        data_list = []
        for rec in records:
            data_dict = {
                "Description": rec.get("description"),
                "Feedname": rec.get("sixgill_feedname"),
                "Source": rec.get("sixgill_source"),
                "Post Title": rec.get("sixgill_posttitle"),
                "Actor": rec.get("sixgill_actor"),
                "Post ID": "https://portal.cybersixgill.com/#/search?q=_id:"
                + rec.get("sixgill_postid", ""),
                "Labels": ",".join(rec.get("labels")),
                "Confidence": rec.get("sixgill_confidence"),
                "Severity": rec.get("sixgill_severity"),
                "Created": rec.get("created"),
                "Modified": rec.get("modified"),
                "Valid From": rec.get("valid_from"),
            }
            external_reference = rec.get("external_reference", [])
            for obj in external_reference:
                if obj.get("source_name", "") == "VirusTotal":
                    data_dict.update(
                        {
                            "Virustotal PR": obj.get("positive_rate"),
                            "Virustotal Url": obj.get("url"),
                        },
                    )
                if obj.get("source_name", "") == "mitre-attack":
                    data_dict.update(
                        {
                            "Mitre Description": obj.get("description"),
                            "Mitre Tactic": obj.get("mitre_attack_tactic"),
                            "Mitre Tactic Id": obj.get("mitre_attack_tactic_id"),
                            "Mitre Tactic Url": obj.get("mitre_attack_tactic_url"),
                        },
                    )
            data_list.append(data_dict)
        return data_list
    except Exception as err:
        logger.exception("An error occurred while processing records")
        return err


# https://dev.splunk.com/enterprise/docs/developapps/addsupport/logging/loggingsplunkextensions/
def setup_logging(
    file_name: str,
    log_format: str = "%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",
) -> Logger:
    """Set up a Splunk-compatible logger with rotating file handler.

    Args:
        file_name (str): Base name for the log file
        log_format (str, optional): Log message format string. Defaults to a comprehensive format.

    Returns:
        Logger: Configured logger instance

    """
    log_file_name = f"{APP_NAME}.{file_name.split('.')[0]}"
    custom_logger = getLogger(log_file_name)
    full_log_file_path = (
        Path(SPLUNK_HOME) / "var" / "log" / "splunk" / f"{file_name}.log"
    )
    default_log_config = Path(SPLUNK_HOME) / "etc" / "log.cfg"
    local_log_config = Path(SPLUNK_HOME) / "etc" / "log-local.cfg"

    splunk_log_handler = handlers.RotatingFileHandler(
        full_log_file_path.resolve(),
        mode="a",
    )
    splunk_log_handler.setFormatter(Formatter(log_format))
    custom_logger.addHandler(splunk_log_handler)
    setupSplunkLogger(custom_logger, default_log_config, local_log_config, "python")
    return custom_logger

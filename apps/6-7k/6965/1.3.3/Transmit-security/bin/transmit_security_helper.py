"""
Transmit Security Add-on for Splunk - Helper Module

Collects events from Transmit Security API and writes them to Splunk.
"""

import json
import logging

import import_declare_test
import requests
from solnlib import conf_manager, credentials, log
from splunklib import modularinput as smi

ADDON_NAME = "Transmit-security"


def get_client_secret(session_key: str, input_name: str, logger: logging.Logger) -> str:
    """Retrieve the client_secret from Splunk's credential store."""
    realm = f"__REST_CREDENTIAL__#{ADDON_NAME}#data/inputs/transmit_security"

    credential_manager = credentials.CredentialManager(
        session_key=session_key,
        app=ADDON_NAME,
        realm=realm,
    )

    passwords = credential_manager.get_clear_passwords_in_realm()

    for pwd in passwords:
        if pwd.get("username") == input_name:
            clear_password = pwd.get("clear_password", "")
            try:
                password_data = json.loads(clear_password)
                if "client_secret" in password_data:
                    return password_data["client_secret"]
            except json.JSONDecodeError:
                return clear_password

    raise credentials.CredentialNotExistException(
        f"No credential found for input: {input_name}"
    )


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_access_token(oauth_token_url: str, client_id: str, client_secret: str) -> str:
    """Fetch OAuth 2 access token using client credentials flow."""
    response = requests.post(
        oauth_token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_events(events_endpoint: str, access_token: str) -> list:
    """Fetch events from Transmit Security API using POST request."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(events_endpoint, headers=headers, json={})
    response.raise_for_status()
    return response.json()


def validate_urls(oauth_endpoint: str, endpoint: str):
    """Validate that both URLs start with https://"""
    if not (oauth_endpoint.startswith("https://") and endpoint.startswith("https://")):
        raise ValueError("Both oauth_endpoint and endpoint must start with 'https://'.")


def validate_input(definition: smi.ValidationDefinition):
    """Validate input configuration."""
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    """Main entry point for the modular input."""
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="transmit_security_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, input_name)

            oauth_endpoint = input_item.get("oauth_endpoint")
            endpoint = input_item.get("endpoint")
            client_id = input_item.get("client_id")
            index = input_item.get("index", "default")
            sourcetype = "Transmit-security"

            try:
                client_secret = get_client_secret(
                    session_key, normalized_input_name, logger
                )
            except Exception:
                client_secret = input_item.get("client_secret")

            if not all([oauth_endpoint, endpoint, client_id, client_secret]):
                raise ValueError(
                    "Missing required configuration: oauth_endpoint, endpoint, client_id, client_secret"
                )

            validate_urls(oauth_endpoint, endpoint)

            access_token = get_access_token(oauth_endpoint, client_id, client_secret)
            events = fetch_events(endpoint, access_token)

            event_count = 0
            for event in events:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(event),
                        index=index,
                        sourcetype=sourcetype,
                    )
                )
                event_count += 1

            log.events_ingested(logger, input_name, sourcetype, event_count, index)
            log.modular_input_end(logger, input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "transmit_security_error",
                msg_before=f"Exception raised while ingesting data for {normalized_input_name}: ",
            )
            try:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(
                            {"error": str(e), "input_name": normalized_input_name}
                        ),
                        index=input_item.get("index", "default"),
                        sourcetype="Transmit-security:error",
                    )
                )
            except Exception:
                pass

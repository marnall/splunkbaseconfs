import json
import sys
import logging
import os
import requests
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")
LOG_FILENAME = os.path.join(SPLUNK_HOME, "var", "log", "splunk", "niksms_alert.log")

# Logger setup
logger = logging.getLogger('niksms_alert')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d", interval=1, backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

# API endpoint
NIKSMS_API_URL = "https://webservice.niksms.com/api/v1/web-service/sms/send/group"

def send_sms_group(api_key, sender_number, phones, message):
    """
    Send SMS to a group of phone numbers using Niksms API.
    """
    if isinstance(phones, str):
        phones = [p.strip() for p in phones.split(",") if p.strip()]

    recipients = [{"Phone": phone} for phone in phones]

    payload = {
        "ApiKey": api_key,
        "SenderNumber": sender_number or "",  # Use empty string if sender_number is not provided
        "Message": message,
        "Recipients": recipients
    }

    try:
        resp = requests.post(NIKSMS_API_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()
        logger.info("Group SMS sent to %s: %s", phones, result)
        return result
    except Exception as e:
        logger.error("Failed to send group SMS: %s", e)
        raise


if __name__ == "__main__":
    logger.info("Received arguments: %s", sys.argv)
    try:
        # Read payload JSON from stdin
        payload = json.load(sys.stdin)
        logger.info("Received payload: %s", payload)

        # Extract configuration parameters
        config = payload.get('configuration', {})
        api_key = config.get('apikey', '')
        sender_number = config.get('sender', '')
        phones = config.get('phones', '')
        message = config.get('message', 'Splunk Alert: Default Message')

        # Validate Parameters
        if not api_key:
            logger.error("No API key provided")
            print("Error: No API key provided")
            sys.exit(1)
        if not phones:
            logger.error("No phone numbers provided")
            print("Error: No phone numbers provided")
            sys.exit(1)
        if not message:
            logger.error("No message provided")
            print("Error: No message provided")
            sys.exit(1)

        logger.info("Message: %s", message)
        logger.info("Sendto (Phones): %s", phones)
        logger.info("Sender: %s", sender_number or "[EMPTY]")
        logger.info("API Key: [REDACTED]")

        send_sms_group(api_key, sender_number, phones, message)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON payload: %s", e)
        print(f"Error: Failed to parse JSON payload: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error("Script failed: %s", str(e))
        print(f"Error: {str(e)}")
        sys.exit(1)

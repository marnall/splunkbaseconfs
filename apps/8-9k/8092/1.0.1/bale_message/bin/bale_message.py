import json
import sys
import requests
import logging
import time
import os
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME, "var", "log", "splunk", "bale_alert.log")

# Set up a specific logger
logger = logging.getLogger('bale_alert')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Bale api url
API_URL = "https://tapi.bale.ai"

def send_message(chat_id, text, bot_token, retries=3, delay=5):
    url = f"{API_URL}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            logger.info("Message sent to %s: %s", chat_id, resp.json())
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 503 and attempt < retries - 1:
                logger.warning("503 error, retrying (%d/%d) after %d seconds", attempt + 1, retries, delay)
                time.sleep(delay)
                continue
            logger.error("Error sending message to %s: %s", chat_id, e)
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Error sending message to %s: %s", chat_id, e)
            raise

if __name__ == "__main__":
    logger.info("Received arguments: %s", sys.argv)
    try:
        # Read payload JSON from stdin
        payload = json.load(sys.stdin)
        logger.info("Received payload: %s", payload)

        # Extract configuration parameters
        config = payload.get('configuration', {})
        bot_token = config.get('bottoken', '')
        chat_id = config.get('chatid', '')
        message = config.get('message', 'Anomaly Detected: Default Message')

        # Validation
        if not bot_token:
            logger.error("No bot_token provided in configuration")
            print("Error: No bot_token provided")
            sys.exit(1)
        if not chat_id.isdigit():
            logger.error("Invalid chat_id: %s", chat_id)
            print(f"Error: Invalid chat_id {chat_id}")
            sys.exit(1)
        if not message:
            logger.error("No message provided in configuration")
            print("Error: No message provided")
            sys.exit(1)

        logger.info("Message: %s", message)
        logger.info("Sendto (CHAT_ID): %s", chat_id)
        logger.info("Bot Token: [REDACTED]") # Do not log sensitive info

        # Send message
        send_message(chat_id, message, bot_token)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON payload: %s", e)
        print(f"Error: Failed to parse JSON payload: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error("Script failed: %s", str(e))
        print(f"Error: {str(e)}")
        sys.exit(1)

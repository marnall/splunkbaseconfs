import requests
import urllib3
import logging
import config 


# Constants for token generation
API_TOKEN_URL_TEMPLATE = '{platform_base_url}/api/apikeys/token'
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def create_token(api_key, platform_base_url,proxies=None):
   
    headers = {
        'X-API-KEY': api_key
    }
    API_TOKEN_URL=API_TOKEN_URL_TEMPLATE.format(platform_base_url=platform_base_url)
    try:
        response = requests.post(API_TOKEN_URL, headers=headers,proxies=proxies)
        response.raise_for_status()
        resp_json = response.json()
        return resp_json.get('token', '')
    except urllib3.exceptions.TimeoutError as e:
        logging.error(f"Token creation request timed out.: {e} with api key {api_key}")
        raise
    except Exception as e:
        logging.error(f"Failed to create token: {str(e)} with api key {api_key}")
        raise

def get_token(appconfig):
    logging.info("Fetching API token.")
    API_KEY = appconfig.api_key
    PLATFORM_BASE_URL = appconfig.platform_base_url
    PROXIES = config.build_proxies_dict(appconfig.proxies)
    if not API_KEY:
        logging.error("No API key found in configuration. Please set up the app and provide an API key.")
        raise ValueError("No API key found in configuration.")

    # Read token from Splunk storage/passwords (written by token.py)
    API_TOKEN = getattr(appconfig, 'api_token', None)
    if not API_TOKEN:
        logging.warning("No API token found in Splunk storage/passwords. Generating a new token now.")
        try:
            API_TOKEN = create_token(API_KEY, PLATFORM_BASE_URL,PROXIES)
        except Exception as e:
            logging.error(f"Failed to generate API token: {e}")
            raise RuntimeError(f"Failed to generate API token: {e}")
        if not API_TOKEN:
            logging.error("Failed to generate API token. Exiting.")
            raise RuntimeError("Failed to generate API token.")
        # Store the token for future runs
        if hasattr(appconfig, 'StoreToken'):
            if appconfig.StoreToken(API_TOKEN):
                logging.info("API token generated and stored in Splunk storage/passwords.")
            else:
                logging.warning(f"API token generated but failed to store in Splunk storage/passwords with api key {API_KEY}.")
    return API_TOKEN

def main():
    logging.info("Updating Token in splunk storage using scheduling")
    appconfig = config.Config()
    if not appconfig.LoadConfiguration():
        logging.error("Error loading configuration.")
        return
    api_key = appconfig.api_key
    PROXIES = config.build_proxies_dict(appconfig.proxies)
    if not api_key:
        logging.error("No API key found in configuration.")
        return
    try:
        token = create_token(api_key, appconfig.platform_base_url,PROXIES)
    except Exception:
        logging.error("Failed to generate token.")
        return
    # Store token in Splunk storage/passwords
    if appconfig.StoreToken(token):
        logging.info("Token updated in Splunk storage/passwords as 'api_token'.")
    else:
        logging.error("Failed to store token in Splunk storage/passwords.")


if __name__ == "__main__":
    main()

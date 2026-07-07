import sys
import os
import configparser
import requests
import json
import logging
from datetime import datetime

def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'bitbucket_commits.log')

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    logging.info("----- Script Started -----")

def read_inputs_conf():
    inputs_path = os.path.join(os.path.dirname(__file__), '..', 'default', 'user_inputs.conf')
    config = configparser.ConfigParser()
    config.read(inputs_path)

    stanza = 'user_inputs'
    if stanza not in config:
        logging.error(f"Stanza {stanza} not found in inputs.conf")
        raise ValueError(f"Stanza {stanza} not found in inputs.conf")

    workspace = config[stanza].get('workspace')
    repo = config[stanza].get('repo')
    token = config[stanza].get('token')
    url = config[stanza].get('url', f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/commits")
    print("url",url)

    if not all([workspace, repo, token]):
        logging.error("Missing required fields: workspace, repo, or token")
        raise ValueError("One or more required fields (workspace, repo, token) are missing in inputs.conf")

    logging.info(f"Configuration loaded: workspace={workspace}, repo={repo}")
    return workspace, repo, token, url

def fetch_commits(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    logging.info(f"Sending GET request to URL: {url}")

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    logging.info("Received successful response from Bitbucket API")
    return response.json()

def main():
    setup_logging()

    try:
        workspace, repo, token, url = read_inputs_conf()
        commits = fetch_commits(url, token)

        for commit in commits.get("values", []):
            print(json.dumps(commit))
            logging.info(f"Commit fetched: {commit.get('hash', 'N/A')}")

    except Exception as e:
        logging.error(f"Exception occurred: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    main()

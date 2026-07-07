#!/usr/bin/env python3

import os
import sys
import json
import time
import requests
import configparser
from pathlib import Path
import logging

# Setup logger
LOG_FILE = os.path.join(os.path.dirname(__file__), "graphql_poller_new.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def read_inputs_conf():
    conf_paths = [
        Path(__file__).resolve().parents[1] / 'default' / 'userinputs.conf'
    ]
    parser = configparser.ConfigParser()
    parser.optionxform = str  # preserve case
    for path in conf_paths:
        if path.exists():
            parser.read(path)
            for section in parser.sections():
                if 'script://' in section and 'graphql_poller_new.py' in section:
                    cfg = parser[section]
                    return {
                        'endpoint': cfg.get('endpoint', '').strip(),
                        'query': cfg.get('query', '').strip(),
                        'headers': json.loads(cfg.get('headers', '{}')),
                        'variables': json.loads(cfg.get('variables', '{}')),
                        'sourcetype': cfg.get('sourcetype', 'graphql_api').strip(),
                        'index': cfg.get('index', 'main').strip()
                    }
    return {}


def validate_graphql_response(resp_json):
    if 'errors' in resp_json:
        raise ValueError(f"GraphQL errors: {resp_json['errors']}")
    if 'data' not in resp_json:
        raise ValueError("Invalid GraphQL response: 'data' field missing")
    return True

def fetch_graphql_data(endpoint, query, headers, variables):
    try:
        payload = {
            'query': query,
            'variables': variables
        }
        response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        resp_json = response.json()
        validate_graphql_response(resp_json)
        return resp_json['data']
    except Exception as e:
        logging.error(f"Error fetching GraphQL data: {e}")
        return {"_error": str(e)}


def emit_to_stdout(event_dict, sourcetype, index):
    event = {
        "time": int(time.time()),
        "sourcetype": sourcetype,
        "index": index,
        "event": event_dict
    }
    print(json.dumps(event))  # Ensure this prints to stdout

def main():
    try:
        config = read_inputs_conf()
        if not config.get('endpoint') or not config.get('query'):
            logging.error("Missing endpoint or query in inputs.conf")
            emit_to_stdout({"_error": "Missing configuration"}, "graphql_api_error", "main")
            return

        data = fetch_graphql_data(config['endpoint'], config['query'], config['headers'], config.get('variables', {}))
        emit_to_stdout(data, config['sourcetype'], config['index'])

    except Exception as e:
        logging.exception(f"Unhandled exception in main: {e}")
        emit_to_stdout({"_error": str(e)}, "graphql_api_error", "main")

if __name__ == '__main__':
    main()

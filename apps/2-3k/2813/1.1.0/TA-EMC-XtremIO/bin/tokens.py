import import_declare_test
import logging
import requests


def get_ids(raw_string, req_args):
    endpoint = raw_string.rsplit('/', 1)[0]
    name = endpoint.rsplit('/', 1)[1]
    endpoints = set()

    try:
        r = requests.get(endpoint, **req_args)
        r.raise_for_status()
        json_types = r.json()
        if name in ["ig-folders", "volume-folders"]:
            name = "folders"
        children = json_types[name]
        for child in children:
            endpoints.add(child['href'])
    except requests.exceptions.Timeout as e:
        logging.error("HTTP Request Timeout error: {}".format(str(e)))
    except requests.exceptions.HTTPError as e:
        logging.error("HTTP Request error: {}".format(str(e)))
    except Exception as e:
        logging.error("Exception performing request: {}".format(str(e)))

    return endpoints

""" api.py

Python module for use with SpyCloud's Enterprise API

"""
import time
import requests


def breach_catalog(api_key, since):
    """ Generator function which yields SpyCloud breaches """
    headers = {'x-api-key': api_key}
    cursor = ''
    wait_duration = 1.1
    while cursor is not None:
        url = 'https://api.spycloud.io/enterprise-v1/breach/catalog?cursor=%s&since=%s' \
              % (cursor, since)
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            # Slow down requests
            time.sleep(10)
            wait_duration = wait_duration*2
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        else:
            response.raise_for_status()
        cursor = response.json()['cursor']
        if cursor == '':
            cursor = None
        for result in response.json()['results']:
            yield result
        time.sleep(wait_duration)

def watchlist(api_key, since):
    """ Generator function which iterates over identifiers and yields
        watchlist data for each """
    headers = {'x-api-key': api_key}
    url = "https://api.spycloud.io/enterprise-v1/watchlist/identifiers"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    identifiers = response.json()["results"]
    for identifier in identifiers:
        for result in watchlist_data(api_key, since, identifier["identifier_type"],
                                     identifier["identifier_name"]):
            yield result

def watchlist_data(api_key, since, identifier_type, identifier):
    """ Generator function which yields SpyCloud watchlist data """

    # Map identifier type to endpoint
    if identifier_type == "email":
        endpoint = "emails"
    else:
        endpoint = "domains"
    headers = {'x-api-key': api_key}
    cursor = ''
    wait_duration = 1.1
    while cursor is not None:
        if cursor == '':
            url = 'https://api.spycloud.io/enterprise-v1/breach/data/%s/%s?since=%s' \
                  % (endpoint, identifier, since)
        else:
            url = 'https://api.spycloud.io/enterprise-v1/breach/data/%s/%s?cursor=%s&since=%s' \
                  % (endpoint, identifier, cursor, since)
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            # Slow down requests
            time.sleep(10)
            wait_duration = wait_duration*2
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        else:
            response.raise_for_status()

        cursor = response.json()['cursor']
        if cursor == '':
            cursor = None
        for result in response.json()['results']:
            result['identifier_type'] = identifier_type
            result['identifier'] = identifier
            yield result
        time.sleep(wait_duration)

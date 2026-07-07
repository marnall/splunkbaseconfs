#!/usr/bin/env python
"""
shodan-query.py
Generates the | shodan command
"""
import datetime
import json
import sys
import time
import re
import shodan
import splunk.Intersplunk
import common


def argument_loop(argument):
    """
    Loops through arguments
    :param argument:
    :return:
    """
    args = list()
    queries = list()
    max_pages = 1

    for arg in argument:
        try:
            (key, value) = arg.split("=", 1)
        except ValueError:
            args.append(arg)
            continue

        key = key.lower()
        if key == "max_pages":
            try:
                max_pages = int(value)
                continue
            except ValueError:
                raise Exception("max_pages must be an integer")
        queries.append("{}:{}".format(key, value))

    if not queries:
        queries.append(" ".join(args))

    return queries, max_pages


def query_loop(queries, max_pages, events):
    """
    Loops through queries
    :param queries:
    :param max_pages:
    :param events:
    :return:
    """
    session_key = re.search(r'sessionKey:(.*)', sys.stdin.read()).groups(1)[0]
    api_key_value = common.getCredentials(session_key)[1]
    api = shodan.Shodan(api_key_value)

    for query in queries:
        current_page = 1
        while current_page <= max_pages:
            try:
                results = api.search(query, page=current_page)["matches"]
            except shodan.APIError:
                results = list()
            get_events(results, query, events)
            if len(results) < 100:
                break
            current_page += 1


def get_events(results, query, events):
    """
    Loops through results
    :param results:
    :param query:
    :return:
    """
    for event in results:
        event["_raw"] = json.dumps(event)
        event["source"] = "shodan"
        event["sourcetype"] = "shodan"
        event["query"] = query

        if "timestamp" in event:
            try:
                dt = datetime.datetime.strptime(event["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                dt = datetime.datetime.strptime(event["timestamp"], "%Y-%m-%dT%H:%M:%S")
            event["_time"] = time.mktime(dt.timetuple())
        else:
            event["_time"] = time.time()

        if "ip_str" in event:
            event["host"] = event["ip_str"]
        else:
            event["host"] = "shodan"

        if "location" in event:
            location = event.pop("location")
            for k in location:
                new_k = "location_{}".format(k)
                event[new_k] = location[k]
        events.append(event)


def main():
    """
    Main method to execute Shodan command
    :return:
    """
    try:
        queries, max_pages = argument_loop(sys.argv[1:])

        events = list()
        query_loop(queries, max_pages, events)

    except Exception as e:  # pylint: disable=broad-except
        events = splunk.Intersplunk.generateErrorResults(str(e))

    splunk.Intersplunk.outputResults(events)


if __name__ == "__main__":
    main()

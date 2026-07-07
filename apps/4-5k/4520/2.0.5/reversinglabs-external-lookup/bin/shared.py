#!/usr/bin/env python

import csv
import os
from ReversingLabs.SDK.ticloud import FileReputation, FileAnalysis

'''
Module shared in File Reputation and File Analysis external lookups for Splunk 

LICENSE
<<---
Copyright (c) ReversingLabs International GmbH. 2016-2020
This unpublished material is proprietary to ReversingLabs International GmbH.. All rights reserved.
Reproduction or distribution, in whole or in part, is forbidden except by express written permission of ReversingLabs International GmbH.
<<---
'''

user_agent = "ReversingLabs Splunk External Lookup"
version = "v2.0.5"


def parse_configuration(cfg_file_pth):
    """
    Parses the CSV configuration file and returns a configuration dict.
    :param cfg_file_pth: path to the config file
    :type cfg_file_pth: str
    :return: config dict
    :rtype: dict
    """
    config = {}
    with open(cfg_file_pth, "r") as open_file:
        csv_reader = csv.reader(open_file, delimiter=",")
        line_count = 0
        for line in csv_reader:
            if line_count == 0:
                pass
            else:
                config["TitaniumCloudAddress"] = line[0]
                config["Username"] = line[1]
                config["Password"] = line[2]
                config["HttpProxyAddress"] = line[3]
                config["HttpProxyPort"] = line[4]
                config["HttpProxyUsername"] = line[5]
                config["HttpProxyPassword"] = line[6]
                config["HttpsProxyAddress"] = line[7]
                config["HttpsProxyPort"] = line[8]
                config["HttpsProxyUsername"] = line[9]
                config["HttpsProxyPassword"] = line[10]
            line_count += 1
    return config


def proxy_url_helper(addr, name, pwd, port):
    proxy = ""
    credentials = ""

    if addr != "None":
        if name != "None" and pwd != "None":
            credentials = name + ":" + pwd + "@"
        host = addr
        if host.startswith("http://"):
            protocol = "http://"
            host = host[len("http://"):]
        elif host.startswith("https://"):
            protocol = "https://"
            host = host[len("https://"):]
        proxy = protocol + credentials + host + ":" + port
    return proxy


def lookup(hash_value, lookup_type, lookup_element):
    """
    Performs an RL API query and returns the response JSON.
    :param hash_value: hash value argument in the query
    :param lookup_type: "FileAnalysis" or "FileReputation"
    :param lookup_element: json element that holds the relevant info, static type member?
    :return: first usable response JSON level
    :rtype: dict
    """
    try:
        config = parse_configuration(os.path.join(os.path.dirname(os.getcwd()), "lookups", "ticloud_configuration.csv"))
    except FileNotFoundError:
        lookup_result = {"RL_ERROR_message": "The configuration file was not found."}
        return lookup_result

    address = config.get("TitaniumCloudAddress")
    if not address:
        lookup_result = {"RL_ERROR_message": "Missing TitaniumCloud address in the configuration file."}
        return lookup_result

    username = config.get("Username")
    password = config.get("Password")
    if not username or not password:
        lookup_result = {"RL_ERROR_message": "Missing username or password in the configuration file."}
        return lookup_result

    proxies = {}
    proxy = proxy_url_helper(config["HttpsProxyAddress"], config["HttpsProxyUsername"],
                             config["HttpsProxyPassword"], config["HttpsProxyPort"])
    if proxy != "":
        proxies["https"] = proxy

    proxy = proxy_url_helper(config["HttpProxyAddress"], config["HttpProxyUsername"],
                             config["HttpProxyPassword"], config["HttpProxyPort"])
    if proxy != "":
        proxies["http"] = proxy

    try:
        lookup_obj = lookup_type(
            host=address,
            username=username,
            password=password,
            proxies=proxies,
            user_agent=f"{user_agent} {version}"
        )
        if isinstance(lookup_obj, FileAnalysis):
            response = lookup_obj.get_analysis_results(hash_input=hash_value)
        elif isinstance(lookup_obj, FileReputation):
            response = lookup_obj.get_file_reputation(hash_input=hash_value)
    except Exception as e:
        lookup_result = {"RL_ERROR_message": str(e)}
        return lookup_result
    response_json = response.json()

    if "rl" in response_json and lookup_element in response_json.get("rl"):
        lookup_result = response_json["rl"][lookup_element]
    else:
        lookup_result = {"RL_ERROR_message": "Required response body not found."}
        return lookup_result
    return lookup_result

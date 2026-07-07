# encoding = utf-8

import os
from datetime import datetime
from pathlib import Path
import requests
import re


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # checkbox = definition.parameters.get('checkbox', None)
    pass


def collect_events(helper, ew):
    now = datetime.now()
    dt_string = now.strftime("%m/%d/%Y %H:%M:%S %Z")
    
    # collect events from proofpoint blocklists and write to lookup csv
    url = 'https://rules.emergingthreats.net/blockrules/compromised-ips.txt'
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/compromised-ips.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/compromised-ips.txt", "r") as input:
        inputbase = [x.encode() for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/compromised-ips.csv", "wb") as output:
            output.write(str.encode("Date Added"))
            output.write(str.encode(","))
            output.write(str.encode("ip_address"))
            output.write(str.encode("\n"))
            for line in inputbase:
                output.write(str.encode(dt_string))
                output.write(str.encode(","))
                output.write(line)
                
    # collect events from abuse CnC IP blocklists and write to lookup csv
    # collect only IPs and discard anything that is not IP
    url = 'https://feodotracker.abuse.ch/downloads/ipblocklist.txt'
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/ipblocklist.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    # declaring the regex to capture IP addresses and discard anything else
    ip_extract = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')

    # empty list
    iplist = []
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/ipblocklist.txt", "r") as input:
        inputbase = input.readlines()
        for line2 in inputbase:
            line2 = line2.rstrip()
            result = ip_extract.search(line2)
            if result:
                iplist.append(line2)
                
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/ipblocklist.csv", "w") as output:
            output.write("Date Added")
            output.write(",")
            output.write("ip_address")
            output.write("\n")
            for line in iplist:
                output.write(dt_string)
                output.write(",")
                output.write(line)
                output.write("\n")
                
    # collect a list of urls from urlhaus and write to CSV
    url = "https://urlhaus.abuse.ch/downloads/text_recent"
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/urlhaus.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/urlhaus.txt", "r") as input:
        inputbase = [x.encode() for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/urlhaus.csv", "wb") as output:
            output.write(str.encode("Date Added"))
            output.write(str.encode(","))
            output.write(str.encode("url"))
            output.write(str.encode("\n"))
            for line in inputbase:
                output.write(str.encode(dt_string))
                output.write(str.encode(","))
                output.write(line)
                
    # collect a list of email urls from openphish and write to csv	
    url = 'https://openphish.com/feed.txt'
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/openphish.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/openphish.txt", "r") as input:
        inputbase = [x.encode() for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/openphish.csv", "wb") as output:
            output.write(str.encode("Date Added"))
            output.write(str.encode(","))
            output.write(str.encode("url"))
            output.write(str.encode("\n"))
            for line in inputbase:
                output.write(str.encode(dt_string))
                output.write(str.encode(","))
                output.write(line)
                
                
    # collects a list of domains from osint threat intel
    url = 'https://osint.digitalside.it/Threat-Intel/lists/latestdomains.txt'
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/latestdomains.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/latestdomains.txt", "r") as input:
        inputbase = [x for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/latestdomains.csv", "w") as output:
            output.write(str("Date Added"))
            output.write(str(","))
            output.write(str("url"))
            output.write(str("\n"))
            for line in inputbase:
                if not line.startswith("#"):
                    output.write(dt_string)
                    output.write(",")
                    output.write(line)
    
    # collects phishing domains from mitchell krogza github               
    url = "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-domains-ACTIVE.txt"
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/phishing-domains-ACTIVE.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/phishing-domains-ACTIVE.txt", "r") as input:
        inputbase = [x.encode() for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/phishing-domains-active.csv", "wb") as output:
            output.write(str.encode("Date Added"))
            output.write(str.encode(","))
            output.write(str.encode("domain"))
            output.write(str.encode("\n"))
            for line in inputbase:
                output.write(str.encode(dt_string))
                output.write(str.encode(","))
                output.write(line)
    
    # collects a list of Phishing domains from  romainmarcoux Github page
    url = "https://raw.githubusercontent.com/romainmarcoux/malicious-domains/refs/heads/main/full-domains-aa.txt"
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/full-domains-aa.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/full-domains-aa.txt", "r") as input:
        inputbase = [x.encode() for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/full-domains-aa.csv", "wb") as output:
            output.write(str.encode("Date Added"))
            output.write(str.encode(","))
            output.write(str.encode("domain"))
            output.write(str.encode("\n"))
            for line in inputbase:
                output.write(str.encode(dt_string))
                output.write(str.encode(","))
                output.write(line)
    
    url = "https://raw.githubusercontent.com/romainmarcoux/malicious-domains/refs/heads/main/full-domains-ab.txt"
    filename = Path('/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/full-domains-ab.txt')
    response = requests.get(url)
    filename.write_bytes(response.content)
    
    with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/holdout/full-domains-ab.txt", "r") as input:
        inputbase = [x.encode() for x in input.readlines()]
        with open("/opt/splunk/etc/apps/TA-ipurl-ioc-ingestion/lookups/full-domains-ab.csv", "wb") as output:
            output.write(str.encode("Date Added"))
            output.write(str.encode(","))
            output.write(str.encode("domain"))
            output.write(str.encode("\n"))
            for line in inputbase:
                output.write(str.encode(dt_string))
                output.write(str.encode(","))
                output.write(line)

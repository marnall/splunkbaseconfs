import datetime as dt
import os
import sys
import requests as rq
import json
from cba_helpers import CybelAngel





def stream_to_splunk(data):
    print(json.dumps(data))


def main():
    SESSION_KEY = sys.stdin.readline().strip()
    client = CybelAngel(sessionKey=SESSION_KEY)
    if len(SESSION_KEY) == 0:
        exit(2)
    
    cba_domains = client.request_cba_domains()
    for dom in cba_domains["results"]:
        stream_to_splunk(dom)


if __name__ == "__main__":
    main()
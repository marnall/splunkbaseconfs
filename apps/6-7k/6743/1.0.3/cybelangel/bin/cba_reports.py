import datetime as dt
import os
import sys
import requests as rq
import json
import csv
from cba_helpers import CybelAngel






def checkpoint(checkpoint_file, report):
    """ Add report ID to checkpoint to avoid duplicates """
    report_id =  str(report["id"])
    with open(checkpoint_file,'r') as f:
        csvreader = csv.reader(f)
        for row in csvreader:
            for item in row:
                if report_id in item:
                    return True
        return False
     

def write_to_checkpoint_file(checkpoint_file, report):
    """ Write Report ID to checkpoint file """
    report_id = str(report['id'])
    with open(checkpoint_file,'a') as f:
        f.write(report_id + "\n")

def stream_to_splunk(checkpoint_file,data):
    """ Log data to checkpoint file, and create event in Splunk"""
    if checkpoint(checkpoint_file,data):
        pass
    else:
        write_to_checkpoint_file(checkpoint_file,data)
        print(json.dumps(data))


def main():
    """ Get reports from CBA and push to Splunk """
    SESSION_KEY = sys.stdin.readline().strip()
    client = CybelAngel(sessionKey=SESSION_KEY)
    checkpoint_file = os.path.join(os.environ["SPLUNK_HOME"],'etc','apps','cybelangel','lookups','cba_reportid_lookup.csv')
    if len(SESSION_KEY) == 0:
        exit(2)
    
    cba_reports = client.request_cba_reports()
    for report in cba_reports["reports"]:
        stream_to_splunk(checkpoint_file,report)

            
if __name__ == "__main__":
    main()
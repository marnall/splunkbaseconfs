#!/usr/bin/python

import sys,csv,string,re,os,platform
import json

def main():
    try:
        with open("../local/eschecker.json", "r") as escheckerFile:
            savedValue = json.load(escheckerFile)

        output = csv.writer(sys.stdout)
        output.writerow([
            "hasEnterpriseSecurity"
        ])

        output.writerow([
            savedValue["hasEnterpriseSecurity"]
        ])

    except Exception as e:
        return

main()
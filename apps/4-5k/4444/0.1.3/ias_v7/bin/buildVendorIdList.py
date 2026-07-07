#!/usr/bin/python
############################################################
# Build a lookup table of RADIUS vendor IDs from the
# master list at IANA
############################################################
import urllib2
import sys
import csv
import os
import re
defaultOutputFile = os.path.dirname(os.path.abspath(__file__))
defaultOutputFile = os.path.split(defaultOutputFile)[0]
defaultOutputFile = os.path.join(defaultOutputFile, 'lookups', 'ias_enterprise_numbers.csv')



####################### Configuration ######################

INCLUDE_VENDOR_CONTACT_INFO = False

OUTPUT_FILE = defaultOutputFile
IANA_URL = 'https://www.iana.org/assignments/enterprise-numbers'


############################################################




def parseFile(f):
    """ Parse the IANA list of enterprise numbers into a python dict """
    lines = f.read()
    lines = lines.split('\n')

    id, org, contact, email = None, '', '', ''
    d = {}
    for line in lines:
        line = line.rstrip()
    
        m = re.search('\S', line)
        if m != None:
            indentLevel = m.start()
        else:
            indentLevel = 0

        if len(line) == 0:
            continue
        elif line[0] == '#':
            continue
        elif line[0].isdigit():
            if id is not None:
                if INCLUDE_VENDOR_CONTACT_INFO:
                    d[id] = (id, org, contact, email)
                else:
                    d[id] = (id, org, '', '')
            id = int(line)
        elif indentLevel == 2:
            org = line.lstrip()
        elif indentLevel == 4:
            contact = line.lstrip()
        elif indentLevel == 6:
            email = line.lstrip().replace('&','@')
    return d



def writeCSV(filename, d):
    f = open(filename, 'wb')
    csvWriter = csv.writer(f)
    csvWriter.writerow( ('vendor_id', 'vendor', 'vendor_contact', 'vendor_email') )

    ids = d.keys()
    ids.sort()
    for id in ids:
        csvWriter.writerow(d[id])
    f.close()




response = urllib2.urlopen(IANA_URL)
d = parseFile(response)
writeCSV(OUTPUT_FILE, d)




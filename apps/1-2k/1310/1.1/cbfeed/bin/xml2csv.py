#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# XML Feed to CSV converter
#
#
# Copyright (c) 2010-2012 Ryan Portman, Brian Guilfoyle - All rights reserved.
#
# http://www.winningbusinesssystem.com
# info@winningbusinesssystem.com
#
# In a normal operating mode, this script should be run from cron 
# (not a scripted input - see below) once per day as that is how often
# the Marketplace feed file is released.
# 
#
# The marketplace feed does not contain a date field, so the ###append date
# to parse file section is used to add a date to the csv output.
# The hour and minute are arbitrary and can be set to any value.
#
# The daily cron command should look something like this:
# /opt/splunk/etc/apps/cbfeed/bin/xml2csv_url.sh

# If you need to load older feed files to populate the index, comment out
# all entries under the ###append date to parsed file section and uncomment
# the entries under the ###only when backfilling files to index section.
# Update the date in this section to match the file that you are importing.
#
# The command to manually add files should look like this:
# /opt/splunk/etc/apps/cbfeed/bin/xml2csv_file.sh

# Remember to recomment the entries and uncomment the ones under ###append date
# to parsed file" when finished using the xml2csv_file.sh command.

#
# This script contains a routine that cleans the data after the xml is 
# initially parsed. This is because the marketplace feed xml is malformed
# which causes duplicate product IDs to be listed under a single category.
#
# Since the resulting file undergoes post processing, this script should not
# be used as a scripted input in it's present form. 
#
# When the script finishes processing, the last step copies the file to
# /opt/splunk/etc/apps/cbfeed/data where there's a directory monitor defined.
# All data is written to the cbfeed index.
#
# If you need older feed files to populate the index, see this link:
# http://www.winningbusinesssystem.com/clickbank-trending
#

import os
import sys
import pprint
import urllib2
import datetime

###append date to parsed file
now = datetime.datetime.now()
dst = now.strftime("%m/%d/%Y")
hour = "05"
minute = "00"
cbdate = (dst+" "+hour+":"+minute+" ")

###only when backfilling files to index
#year = "2012"
#month = "12"
#day = "11"
#hour = "02"
#minute = "00"
#cbdate = (month+"/"+day+"/"+year+" "+hour+":"+minute+" ")



from xml.etree import ElementTree as et


class Site:
    def __init__(self, category, siteid, line):
        self.category = category
        self.siteid = siteid
        self.line = line

    def getCategory(self):
        return self.category

    def getSiteId(self):
        return self.siteid

    def getLine(self):
        return self.line


class Parser:
    buffer = ""

    def __init__(self, data):
        print "Parsing..."
        self.tree = et.fromstring(data)
        self.compose()

    def compose(self):
        print "Converting..."
        catalogs = self.tree.find("Catalog")

        for cat in self.tree.iter("Category"):
            name = cat.find("Name")
            cat_name = "CategoryName=" + '"' + name.text + '",'
            st = ""

            # Iterate over sites
            for site in cat.iter("Site"):
                st += cat_name
                for t in site.iter():

                    if t.tag != "Site":
                        text = ""
                        if t.text != None:
                            text = t.text

                        st += t.tag + "=" + '"' + self.encodeText(text) + '",'
                    else:
                        st += t.tag + "=" + '"' + site.find("Id").text + '",'

                # Remove trailing comma
                st = st[:-1]
                st += "\n"

            st += "\n"
            self.writeToFile(st)

        # Clean results
        clean()

    def encodeText(self, text):
        return repr(text)[1:-1]

    def writeToFile(self, data):
        f = open("parsed_data.csv", "a")
        f.write(data)
        f.close()

def getFileSource():
    if sys.argv[2]:
        print "Loading file..."
        data_input = sys.argv[2]
        f = open(data_input, "r")
        data = f.read()
        f.close()
    else:
        return None
    
    return data

def getDownloadFileSource(file):
    print "Loading file..."
    f = open(file, "r")
    data = f.read()
    f.close()
    return data

def getUrlSource():
    if sys.argv[2]:
        print "Downloading feed..."
        data_input = sys.argv[2]
        down_cmd = "wget -nd " + data_input
        os.system(down_cmd)

        print "Decompressing file..."
        parts = data_input.split("/")
        f = parts[len(parts)-1]
        decomp_cmd = "unzip -o " + f
        os.system(decomp_cmd)

        unzip_file = f.split(".")
        return getDownloadFileSource(unzip_file[0] + ".xml")
    else:
        return None

def clean():
    # Read the csv file
    print "Parsing results file..."
    data = readFile()
    sites = list()
    clean_sites = list()

    # Parse lines
    for l in data:
        cat = ""
        site = ""
        fields = l.split(',')
        for f in fields:
            values = f.split('=')
            if values[0] == "CategoryName":
                cat = values[1]
            if values[0] == "Site":
                site = values[1]
        sites.append(Site(cat, site, l))

    # Filter duplicate lines for a category
    print "Finding duplicates..."
    #prev_site = ""
    nSites = len(sites)
    for n in range(nSites):
        # Print progress
        i = (float(n)/nSites) * 100
        sys.stdout.write("\r%.2f%%" % i)
        sys.stdout.flush()

        # Check site
        cat = sites[n].getCategory()
        id = sites[n].getSiteId()
        addSite = True
        for sx in clean_sites:
            if sx.getCategory() == cat and sx.getSiteId() == id:
                #print "Dup found! Site ID: " + sites[n].getSiteId()
                addSite = False
        if addSite:
            clean_sites.append(sites[n])

    sys.stdout.write("\r%.2f%%" % 100)
    sys.stdout.flush()

    # Write the new dataset to the file
    print "\nSaving clean file..."
#    os.remove("parsed_data.csv")
    if os.path.exists("parsed_data.csv"):
        os.remove("parsed_data.csv")
#    with open("parsed_data.csv", "w") as f:
    with open("parsed_data.csv", "w") as f:
        for s in clean_sites:
            line = s.getLine()
            if line != "\n":
                f.write(cbdate+s.getLine())
    f.close()
    os.system("cp parsed_data.csv /opt/splunk/etc/apps/cbfeed/data/parsed_data.csv") 

def readFile():
    with open("parsed_data.csv") as f:
        data = f.readlines()
    return data

def main():
    # If no parameters were sent print usage
    if len(sys.argv) == 1:
        print "Usage: xml2csv [file|url] [file path|web url]"
        sys.exit(0)

    # If a file is provided use that as source
    if sys.argv[1] == "file":
        data = getFileSource()

    # Download the web sevice
    elif sys.argv[1] == "url":
        data = getUrlSource()

    # Clean output
    elif sys.argv[1] == "clean":
        clean()
        sys.exit(0)

    if os.path.exists("parsed_data.csv"):
         os.remove("parsed_data.csv")
    

    parser = Parser(data)


if __name__ == "__main__":
    main()

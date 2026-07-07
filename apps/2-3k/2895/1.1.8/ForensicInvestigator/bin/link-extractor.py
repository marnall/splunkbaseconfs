#!/usr/bin/python
# Link extractor
# For questions ask anlee2 -at- vt.edu or Kyle Champlin
# Takes a URL or IP
# Returns all the links in the page

import sys,csv,splunk.Intersplunk,string,urllib2,re

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  urlip = sys.argv[1]

  try:
    website = urllib2.urlopen(urlip)
  except:
    print "Could not retrieve page"

  #read html code
  html = website.read()

  #use re.findall to get all the links
  links = re.findall('"((http|ftp)s?://.*?)"', html)

  print "Links"

  for link in links:
    print link[0]

main()

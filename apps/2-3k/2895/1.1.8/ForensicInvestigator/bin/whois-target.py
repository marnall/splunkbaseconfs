#!/usr/bin/python
# WHOIS tool - hackertarget.com
# For questions ask anlee2 -at- vt.edu or Kyle Champlin
# Takes a URL or IP
# Returns WHOIS information
# http://api.hackertarget.com/whois/?q=fireeye.com

import sys,csv,splunk.Intersplunk,string,urllib2,re,StringIO

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  try:
    response = urllib2.urlopen('http://api.hackertarget.com/whois/?q=' + sys.argv[1])
    textresponse = response.read()
  except:
    textresponse = "error will robinson"
  
  s = StringIO.StringIO(textresponse)
  #print type(textresponse)
  print "Category, Value"
  for line in s:
    if ":" in line:
      print re.sub('\:', ',', line, 1),


#  output = csv.writer(sys.stdout)
#  data = [['Answer'],[textresponse]]
#  output.writerows(data)

main()

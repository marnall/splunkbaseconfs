#!/usr/bin/python
# anlee2 -at- vt.edu
# ePO Query script
# Takes parameters from user and interacts with ePO API
# Returns information from ePO server

import sys,csv,splunk.Intersplunk,string,urllib2,re,StringIO

theurl = 'https://<IP>:8443/remote/'
username = '<username>'
password = '<password>'

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)
  if sys.argv[1] == "":
    splunk.Intersplunk.parseError("Search field cannot be blank")
    sys.exit(0)

  passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
  passman.add_password(None, theurl, username, password)
  authhandler = urllib2.HTTPBasicAuthHandler(passman)
  opener = urllib2.build_opener(authhandler)
  urllib2.install_opener(opener)

  print "Key, Value"
  textresponse="Never assigned"
  if sys.argv[2] == "query":
    try:
      response = urllib2.urlopen(theurl + '/system.find?searchText=' + sys.argv[1])
      textresponse = response.read()
      numresults = textresponse.count("System Location")
      print "** Number of Results: " + str(numresults) + " **"
    except:
      textresponse = "error will robinson"
  elif sys.argv[2] == "settag":
    try:
      response = urllib2.urlopen(theurl + '/system.applyTag?names=' + sys.argv[1] + '&tagName=' + sys.argv[3])
      textresponse = response.read()
      if textresponse == "OK:\r\n0\r\n":
        textresponse="An error occurred. Please check your parameters and try again."
      if textresponse == "OK:\r\n1\r\n":
        textresponse="Success."
    except:
      textresponse = "error will robinson"
  elif sys.argv[2] == "cleartag":
    try:
      response = urllib2.urlopen(theurl + '/system.clearTag?names=' + sys.argv[1] + '&tagName=' + sys.argv[3])
      textresponse = response.read()
      if textresponse == "OK:\r\n0\r\n":
        textresponse="An error occurred. Please check your parameters and try again."
      if textresponse == "OK:\r\n1\r\n":
        textresponse="Success."
    except:
      textresponse = "error will robinson"
  elif sys.argv[2] == "wakeup":
    try:
      response = urllib2.urlopen(theurl + '/system.wakeupAgent?names=' + sys.argv[1])
      textresponse = response.read()
      if textresponse == "OK:\r\n0\r\n":
        textresponse="An error occurred. Please check your parameters and try again."
      if textresponse == "OK:\r\n1\r\n":
        textresponse="Success."
    except:
      textresponse = "error will robinson"

  comma_textresponse = textresponse.replace(',',' |')
  converted_textresponse = comma_textresponse.replace(': ',',')
  separated_textresponse = converted_textresponse.replace('\r\n\r\n','######################################################################,######################################################################\r\n')
  print converted_textresponse

main()

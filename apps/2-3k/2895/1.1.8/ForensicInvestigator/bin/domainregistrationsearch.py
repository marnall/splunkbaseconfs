#!/usr/bin/python 
# Domain Registration Checker
# For questions ask anlee2 -at- vt.edu or patrick olsen
# Takes an email address
# Returns domains registered to that email address

import sys,csv,splunk.Intersplunk,string,base64,urllib,urllib2

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  response = urllib2.Request('https://whoisology.com/email/archive_6/')
  for line in response:
    print line
  #print response

  # result - python grep for:  | grep "whoisology.com/" |grep -e "<td>" -e "<tr>" |cut -d / -f 5 |cut -d \" -f 1


  #output = csv.writer(sys.stdout)
  #data = [['answer'],[result]]
  #output.writerows(data)

main()

#!/usr/bin/python 
# URL decoder
# For questions ask anlee2 -at- vt.edu 
# Takes a string to decode
# Returns a decoded string

import sys,csv,splunk.Intersplunk,string,base64,urllib

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  result=urllib.unquote(sys.argv[1]).decode('utf8')

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()

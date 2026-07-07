#!/usr/bin/python3
# URL decoder
# For questions ask Tony.Lee -at- FireEye.com
# Takes a string to decode
# Returns a decoded string

import sys,csv,splunk.Intersplunk,string,base64,urllib.request,urllib.parse,urllib.error

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  # result=urllib.parse.unquote(sys.argv[1]).decode('utf8')
  result=urllib.parse.unquote(sys.argv[1])
  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()

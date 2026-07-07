#!/usr/bin/python3
# Base64 Converter
# For questions ask Tony.Lee -at- FireEye.com
# Takes two arguments - the string to encode or decode and the word encode or decode
# Returns a variable named answer to Splunk

import sys,csv,splunk.Intersplunk,string,base64

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  sys.argv[1] = sys.argv[1].encode("ascii")
  if sys.argv[2] == "decode" :
    result=base64.b64decode(sys.argv[1])
  else:
    result=base64.b64encode(sys.argv[1])


  output = csv.writer(sys.stdout)
  data = [['answer'],[result.decode("ascii")]]
  output.writerows(data)

main()

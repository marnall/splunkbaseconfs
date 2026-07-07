#!/usr/bin/python 
# HEX converter
# For questions ask anlee2 -at- vt.edu 
# Takes two arguments - the string to encode or decode and the word encode or decode
# Returns a variable named answer to Splunk

import sys,csv,splunk.Intersplunk,string

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  if sys.argv[2] == "decode" :
    result=sys.argv[1].strip().decode("hex")
  else:
    result=sys.argv[1].strip().encode("hex")

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()

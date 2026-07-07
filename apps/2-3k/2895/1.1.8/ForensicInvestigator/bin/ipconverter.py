#!/usr/bin/python 
# IP converter
# For questions ask anlee2 -at- vt.edu 
# Takes two arguments - the string to encode or decode and the word encode or decode
# Returns a variable named answer to Splunk

import sys,csv,splunk.Intersplunk,string

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  input=sys.argv[1].strip()

  if sys.argv[2] == "decode" :
    temp = input.split('.')
    result = '{:02X}{:02X}{:02X}{:02X}'.format(*map(int, temp))
  else:
    bytes = ["".join(x) for x in zip(*[iter(input)]*2)]
    bytes = [int(x, 16) for x in bytes]
    result = ".".join(str(x) for x in bytes)

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()

#!/usr/bin/python 
# Luhn checker -- PCI environments
# For questions ask anlee2 -at- vt.edu or Dave Pany
# Takes a CC number and checks to see if it passes the Luhn test
# Returns True or False

import sys,csv,splunk.Intersplunk,string

def luhn(n):
    r = [int(ch) for ch in str(n)][::-1]
    return (sum(r[0::2]) + sum(sum(divmod(d*2,10)) for d in r[1::2])) % 10 == 0

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  result=luhn(sys.argv[1])

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()

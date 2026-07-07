#!/usr/bin/python 
# ROT decoder
# For questions ask anlee2 -at- vt.edu 
# Takes a string to decode
# Returns a decoded string
# Code from:  http://rosettacode.org/wiki/Rot-13

import sys,csv,splunk.Intersplunk,string

def rotn(s, number):
   """Implement the rot-13 encoding function: "rotate" each letter by the
      letter that's 13 steps from it (wrapping from z to a)
   """
   return s.translate(
       string.maketrans(
           string.ascii_uppercase + string.ascii_lowercase,
           string.ascii_uppercase[number:] + string.ascii_uppercase[:number] +
           string.ascii_lowercase[number:] + string.ascii_lowercase[:number]
           )
       )

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)


  encodedMsg = sys.argv[1]
  n = int(sys.argv[2])

  decodedMsg=rotn(encodedMsg, n)

  output = csv.writer(sys.stdout)
  data = [['answer'],[decodedMsg]]
  output.writerows(data)

main()

#!/usr/bin/python 
# Decode_vbe_wrapper
# For questions ask anlee2 -at- vt.edu 
# Takes in a VBE script

import subprocess,os,sys,csv,splunk.Intersplunk,string
tempfile='csvtemp.txt'

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  target = sys.argv[1].strip()
  oscmd = "./decode-vbe.py " + target

  print oscmd

  result = subprocess.check_output(oscmd, shell=True)

  output = csv.writer(sys.stdout)
  data = [['answer'],[result]]
  output.writerows(data)

main()

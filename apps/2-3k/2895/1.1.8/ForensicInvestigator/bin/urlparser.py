#!/usr/bin/python 
# URL Parser 
# For questions ask anlee2 -at- vt.edu
# Takes a URL and parses out the components
# Returns components of a URL

import sys,csv,splunk.Intersplunk,string,urlparse

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  from urlparse import urlparse
  result=urlparse(sys.argv[1].strip())

  output = csv.writer(sys.stdout)
  output.writerow(['Scheme', 'Netloc', 'Path', 'Params', 'Query', 'Fragment'])
  output.writerow([result.scheme, result.netloc, result.path, result.params, result.query, result.fragment])

main()

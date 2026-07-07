#!/usr/bin/python
# WHOIS tool
# For questions ask anlee2 -at- vt.edu or Kyle Champlin
# Takes a URL or IP
# Returns WHOIS information

import sys,csv,splunk.Intersplunk,string,urllib2,json

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  try:
    response = urllib2.urlopen('http://api.bulkwhoisapi.com/whoisAPI.php?', \
      'domain=' + sys.argv[1] + '&token=usemeforfree')
    jsonresponse = json.loads(response.read())
  except:
    jsonresponse = "error will robinson"

  csvheaders = jsonresponse['formatted_data']
  rawdump = jsonresponse['raw_data']

  headList = []
  dataList = []
  for i in csvheaders:
    headList.append(str(i))
    dataList.append(str(csvheaders[i]))

  headList.append("raw_data")
  dataList.append(rawdump)
  output = csv.writer(sys.stdout, delimiter=',')
  output.writerow(headList)
  output.writerow(dataList)

main()
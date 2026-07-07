# URL Unshortener
# Submit a URL to unshorten

import re,collections,json,csv,sys,urllib,urllib2,splunk.Intersplunk,string,httplib,urlparse

def urllookup(iurl):
  try:
    url = 'https://unshorten.me/raw/' + iurl
    #print "url = " + url
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
         'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
         'Accept-Encoding': 'none',
         'Accept-Language': 'en-US,en;q=0.8',
         'Connection': 'keep-alive'}

    req = urllib2.Request(url, headers=hdr)
    response = urllib2.urlopen(req)
    text = response.read()
    #print text
    return text
  except:
    text =  'An error occurred.  Check your proxy settings.'
    return text

def main():
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    sys.exit(0)

  userinput=sys.argv[1].strip()
  #print "userinput = " + userinput

  result_json = urllookup(userinput)
  print "Answer"
  print result_json

#  output = csv.writer(sys.stdout)
#  data = [['answer'],[result_json]]
#  output.writerows(data)

main()

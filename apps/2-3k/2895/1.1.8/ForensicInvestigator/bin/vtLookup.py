#!/usr/bin/python 
# Parts of this have been copied from Splunks DNSLookup and other examples.
# You can sumbit up to 25 "resources" to VT, however this script does not do that.

import re,collections,json,csv,sys,urllib,urllib2,splunk.Intersplunk,string,ConfigParser,os

apikey = "fb5cf0b1e498dc4c26f24a38b460d1dc138cc3d48e3c4bf1f3e11c97f7d24604"
g_bEnableProxy = False
g_sHTTP_Proxy = None
g_sHTTPS_Proxy = None
g_hProxy = None
g_opener = None

def GetConfig():
  global g_bEnableProxy
  global g_sHTTP_Proxy
  global g_sHTTPS_Proxy
  global g_hProxy
  global g_opener
  global apikey

  l_sPath = os.path.join(os.environ['SPLUNK_HOME'], 'etc/apps/ForensicInvestigator/local/forensicinvestigator.conf')
  #print l_sPath

  if l_sPath:
    l_hConfig = ConfigParser.ConfigParser()
    l_hConfig.read(l_sPath)

    if l_hConfig.has_section('setupentity'):
      if l_hConfig.has_option('setupentity', 'vt_api_key'):
        apikey = l_hConfig.get('setupentity', 'vt_api_key')
        #print apikey
      if l_hConfig.has_option('setupentity', 'proxy_enabled'):
        g_bEnableProxy = l_hConfig.getboolean('setupentity', 'proxy_enabled')
        #print g_bEnableProxy

        if g_bEnableProxy == True:
          if l_hConfig.has_option('setupentity', 'http_proxy'):
            g_sHTTP_Proxy = l_hConfig.get('setupentity', 'http_proxy')
            #print g_sHTTP_Proxy
          if l_hConfig.has_option('setupentity', 'https_proxy'):
            g_sHTTPS_Proxy = l_hConfig.get('setupentity', 'https_proxy')
            #print g_sHTTPS_Proxy
          g_hProxy = urllib2.ProxyHandler({'http': g_sHTTP_Proxy, 'https': g_sHTTPS_Proxy})
          g_opener = urllib2.build_opener(g_hProxy)

          #if g_sHTTP_Proxy == None and g_sHTTPS_Proxy == None:
          #  g_bEnableProxy = False
          #  print "Proxy contains blank values"

def makehash():
	return collections.defaultdict(makehash)

def hashlookup(md5):
  try:
    if g_bEnableProxy == True:
      #print "Proxy is true"
      response = opener.urlopen('https://www.virustotal.com/vtapi/v2/file/report', \
        'apikey=' + apikey + '&resource=' + md5)
      json = response.read()
      return json
    else:
      #print "Proxy is not set"
      response = urllib2.urlopen('https://www.virustotal.com/vtapi/v2/file/report', \
        'apikey=' + apikey + '&resource=' + md5)
      json = response.read()
      return json
  except:
    print 'MD5 Lookup failed.  Check proxy settings'
    return ''

def urllookup(url):
  try:
    if g_bEnableProxy == True:
      #print "Proxy is true"
      response = opener.urlopen('https://www.virustotal.com/vtapi/v2/url/report', \
        'apikey=' + apikey + '&resource=' + url + '&scan=1')
      json = response.read()
      return json
    else:
      #print "Proxy is not set"
      response = urllib2.urlopen('https://www.virustotal.com/vtapi/v2/url/report', \
        'apikey=' + apikey + '&resource=' + url + '&scan=1')
      json = response.read()
      return json
  except:
    print 'URL lookup failed.  Check proxy settings'
    return ''


def main():
  GetConfig()
  (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
  if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")
    #print "python vt.py MD5 VT"
    sys.exit(0)

  userinput=sys.argv[1].strip()
  #print userinput

  if (re.findall(r"(^[a-fA-F\d]{32})", userinput)):
    md5f = userinput
    result_json = hashlookup(md5f)
  else:
    urlf = userinput
    result_json = urllookup(urlf)


  output = csv.writer(sys.stdout)
  data = [['vt'],[result_json]]
  output.writerows(data)

main()

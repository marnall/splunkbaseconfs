import urllib2
import csv
import traceback
from splunk import Intersplunk
from splunk.clilib import cli_common as cli

class connectionError(Exception):
    pass

class CSVDL(object):
    def __init__(self):
        cfg = cli.getConfStanza('atf', 'config')
        uri = cfg.get("feed_uri")
        proxy = cfg.get("proxy")

        if proxy:
            proxy_handler = urllib2.ProxyHandler({'http': proxy, 'https': proxy})
            opener = urllib2.build_opener(proxy_handler)
        else:
            opener = urllib2.build_opener()

        self.uri = uri
        self.opener = opener
        self.proxy = proxy

    def get_csv(self, uri, kwargs):
        """
        Fetch URI
        """
        if not uri:
            uri = self.uri

        try:
            csvfile = self.opener.open(uri)
        except urllib2.URLError as e:
            raise connectionError("Unable to fetch file. Make sure and proxy ({}) is correct and uri exists. Error: {}".format(self.proxy, e))

        return [row for row in csv.DictReader( csvfile, fieldnames=('domain_hash','severity') , **kwargs)]

def main():
    csvdl = CSVDL()

    # Parse arguments from splunk search
    opts, kwargs = Intersplunk.getKeywordsAndOptions()

    results = []

    if opts:
        uri = opts[0]
    else:
        uri = None

    try:
        results = csvdl.get_csv(uri, kwargs)
    except connectionError as e:
        Intersplunk.parseError(str(e))
        return

    Intersplunk.outputResults(results)


try:
    main()
except Exception as e:
    Intersplunk.parseError(traceback.format_exc())

#/usr/bin/python

import cookielib
import os
import sys
import time
import urllib
import urllib2
import shutil
from urlparse import urlsplit
from os.path import basename
from urllib2 import urlopen, URLError, HTTPError

class FAAFetcher:
    
    def daterange(self, earliestyear, latestyear):
        early = int(earliestyear)
        late = int(latestyear)
        FAA_base_url = 'http://www.transtats.bts.gov/Download/On_Time_On_Time_Performance_'

        for year in range(early, late):
            burl = FAA_base_url + str(year)
            
            for month in range(1,13):
                url = burl + "_" + str(month) + ".zip"
                self.download(url)

    def download(self, url):
        # Open the url
        try:
            f = urlopen(url)
            print "downloading " + url

            # Open our local file for writing
            local_file = open(os.path.basename(url), "wb")
            try: 
                local_file.write(f.read())
            finally: 
                local_file.close()
                

        #handle errors
        except HTTPError, e:
            print "HTTP Error:", e.code, url
        except URLError, e:
            print "URL Error:", e.reason, url         

def main(argv):
    #let's figure out how much data you want
    if (len(argv) != 2):
        print "usage: python faascript.py <earliestyear> <latestyear>"
        return -1

    earliestyear = argv[0]
    latestyear = argv[1]

    fetcher = FAAFetcher()
    fetcher.daterange(earliestyear, latestyear)

if __name__ == "__main__":
    main(sys.argv[1:])

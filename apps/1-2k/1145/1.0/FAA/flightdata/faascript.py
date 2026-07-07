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
from StringIO import StringIO
from zipfile import ZipFile

class FAAFetcher:

    def getmonth(self, month, year):
		FAA_base_url = 'http://www.transtats.bts.gov/Download/On_Time_On_Time_Performance_'
	
		#download
		url = FAA_base_url + str(year) + "_" + str(month) + ".zip"
		#print url
		self.download(url)

    def getmonthrange(self, earliestmonth, earliestyear, latestmonth, latestyear):

		if (earliestyear == latestyear):
			for month in range(int(earliestmonth),int(latestmonth)+1):
				self.getmonth(month,int(earliestyear))
		else:
			for year in range(int(earliestyear), int(latestyear)+1):
				if (year == int(earliestyear)):
					for month in range(int(earliestmonth),13):
						self.getmonth(month,year)
				elif (year == int(latestyear)):
					for month in range(1,int(latestmonth)+1):
						self.getmonth(month,year)
				else:
					for month in range(1,13):
						self.getmonth(month,year)

    def download(self, url):
		# Open the url
		try:
			f = urlopen(url)
			print "downloading " + url
			zipfile = ZipFile(StringIO(f.read()))
			zipfile.extractall()
			zipfile.close()
		except:
			print url + " could not be downloaded"
			
def main(argv):
    #let's figure out how much data you want
    if (len(argv) != 1) and (len(argv) != 2):
	print "***usage: python faascript.py <month/year>" 
	print "***or you can download a range:"
        print "***usage: python faascript.py <earliest month/year> <latest month/year>"
	print "***example: python faascript.py 1/2011 12/2012"
	print "***which would be all months from January 2011 to December 2012 inclusive"
        return -1
	
    fetcher = FAAFetcher()

    if (len(argv) == 1):
	date = argv[0].split('/')
	fetcher.getmonth(date[0],date[1])

    if (len(argv) == 2):	
    	earliestdate = argv[0].split('/')
    	latestdate = argv[1].split('/')
	fetcher.getmonthrange(earliestdate[0],earliestdate[1],latestdate[0],latestdate[1])

if __name__ == "__main__":
    main(sys.argv[1:])


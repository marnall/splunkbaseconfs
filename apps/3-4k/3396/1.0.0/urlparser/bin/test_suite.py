#!/usr/bin/env python

"""
# /opt/splunk/etc/apps/urlparser/bin/
# /opt/splunk/bin/splunk cmd python test_suite.py

"""

import unittest
from liburlparser import URLParser

class TestURLParser(unittest.TestCase):

    DATA = [
	{'url': "hTTp://je@n:pass:w@rd@images.www.gOOGle.Co.uk:443/iDNex.php?var=CALue32&ouech=gros#pouet", 'tld':'co.uk'},
	{'url': "ftp://anonymous:jack@enolybabo.tzo.com/594410ZP193CEJ329.cap", 'tld':'com'},
	{'url': "192.168.1.234:8000", 'tld':None},
	{'url': "COUAC", 'tld':None},
	{'url': "yo.COM", 'tld':'com'},
	{'url': "com", 'tld':'com'},
	{'url': "pouet.ck", 'tld':'pouet.ck'},
	{'url': "www.ck", 'tld':'ck'},
	{'url': "google.com", 'tld':'com'},
	{'url': "www.google.com", 'tld':'com'},
	{'url': "www.google.co.uk", 'tld':'co.uk'},
	{'url': "www.google.bl.uk", 'tld':'uk'},
	{'url': "www.bl.ck", 'tld':'bl.ck'},
	{'url': "bl.www.ck", 'tld':'ck'},
	{'url': "yoyo.pouet.fujikawaguchiko.yamanashi.jp", 'tld':'fujikawaguchiko.yamanashi.jp'},
	{'url': "city.pouet.kawasaki.jp", 'tld':'pouet.kawasaki.jp'},
	{'url': "pouet.city.kawasaki.jp", 'tld':'kawasaki.jp'},
	{'url': "http://[2001:4860:0:2001::68]/index.php", 'tld': None},
	# This URL is NOT parsable by python urlparse() due to the ']'
	{'url': "http://this:break]urlparse@pouet.com/index.php", 'tld': None}, 
    ]
    
    def test_tld(self):
	urlparser = URLParser()
	urlparser.loadTLDList("mozilla")
	urlparser.setParsingMode("extended")

	for data in self.DATA:
		u = data['url']
		t = data['tld']
		r = urlparser.parse( u ).to_json()

		if r['url_tld'] is None :
			self.assertIsNone(t)
		else:
			self.assertEqual(r['url_tld'].lower(), t)

if __name__ == '__main__':
	suite = unittest.TestLoader().loadTestsFromTestCase(TestURLParser)
	unittest.TextTestRunner(verbosity=2).run(suite)


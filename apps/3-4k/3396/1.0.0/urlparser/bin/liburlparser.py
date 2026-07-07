#!/usr/bin/env python
# coding: utf-8

import os
import re
import sys
import csv
import json
import codecs
import logging, logging.handlers

from urlparse import urlparse 
from splunk.clilib.bundle_paths import make_splunkhome_path


class URL(object):
	
    SCHEME_TO_PORT = {
	"ftp"   : 21,
	"gopher": 70,
	"http"  : 80,
	"https" : 443,
	"imap"  : 143,
	"imaps" : 993,
	"nntp"  : 119,
	"prospero": 191,
	"rsync" : 873,
	"rtsp"  : 554,
	"sftp"  : 115,
	"sip"   : 5060,
	"sips"  : 5061,
	"svn"   : 3690,
	"tcp"   : 443,   # alias for HTTPS in proxy logs
	"telnet": 23,
	"wais"  : 210
    }

    def __init__(self):
	self.domain = None
	#self.port   = 80 
	self.tld    = None
	self.domain_without_tld = None
	self.subdomain = None
	#self.subdomain_depth = 0

	# from python's urlparse()
	self.scheme   = None
	self.netloc   = None
	self.path     = None
	self.params   = None
	self.query    = None
	self.fragment = None

    def set(self, fieldname, value):
	setattr(self, fieldname, value)

    def to_json(self):
	res = {}
	for (k,v) in self.__dict__.iteritems():
		# fields starting with underscore are private fields
		if k.startswith('_') :
			continue
		res[ 'url_%s' % k ] = v
	return res

    def from_json(self, data):
	for (k,v) in data.iteritems():
		k = k[4:] # remove the 'url_'
		setattr(self, k, v)

    def set_default_port(self):
	"""
	urlparse() extract the following schemes: 
	    file, ftp, gopher, hdl, http, https, imap, mailto, mms, news, nntp, 
	    prospero, rsync, rtsp, rtspu, sftp, shttp, sip, sips, snews, svn, 
            svn+ssh, telnet, wais
	"""
	try:
		self.port = self.SCHEME_TO_PORT[ self.scheme ]
	except:
		pass



class URLParser(object):

    reg_t_rfc1808 = re.compile("://")
    reg_t_ipv4    = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

    def _set_logger(self):
	logger = logging.getLogger()
	logger.propagate = False
	logger.setLevel(logging.INFO)

	#handler = logging.StreamHandler(stream=sys.stderr)
	filepath = make_splunkhome_path(["var", "log", "splunk", "urlparser.log"])
	handler = logging.handlers.RotatingFileHandler(filepath)

	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

	handler.setFormatter(formatter)
	logger.addHandler(handler)

	return logger

    def __init__(self, logger=None):
	self.logger = logger

	if logger == None :
		self.logger = self._set_logger()
		

    def setParsingMode(self, mode):
	"""
	define the parse() function, default to _parse_extended()
	"""
	mode = mode.lower().strip()

	self.parse = getattr(self, "_parse_extended")
	if mode == "simple":
		self.parse = getattr(self, "_parse_simple")


    def _parse_simple(self, url):
	"""
	_parse_simple() only parse URLs with Python's urlparse()

	Following the syntax specifications in RFC 1808, urlparse recognizes 
	a netlog only if it is properly introduced by '//'.
	"""
	if not self.reg_t_rfc1808.search(url) :
		url = "//%s" % url

	u = URL()
	u.set("_url", url.strip())

	try:
		o = urlparse( u._url )
	except Exception, e:
		self.logger.error("Python urlparse() failed to parse URL %s with error %s" % (u._url, e))
		u.set("netloc", "urlparse_error")
		return u

	for (k,v) in o._asdict().iteritems():
		u.set(k,v)

	u.set_default_port()
	return u


    def findTLD(self, hostname):
	"""
	return None in case of TLD not found (like a host or an ip address)

	COUAC    => None
	yo.COM   => com
	com      => com
	pouet.ck => pouet.ck
	www.ck   => ck
	google.com     => com
	www.google.com => com
	www.google.co.uk => co.uk
	www.google.bl.uk => uk
	www.bl.ck => bl.ck
	bl.www.ck => ck
	yoyo.pouet.fujikawaguchiko.yamanashi.jp => fujikawaguchiko.yamanashi.jp
	city.pouet.kawasaki.jp => pouet.kawasaki.jp
	pouet.city.kawasaki.jp => kawasaki.jp
	"""

	h    = hostname.lower()
	dots = h.count(".")
	offset   = -1
	wildcard = False
	exceptions = []

	while dots>=0 :
		t = h.split(".", dots)[-1]

		if t in self.TLDStruct :
			offset = dots
			wildcard   = self.TLDStruct[ t ]['wildcard']
			exceptions = self.TLDStruct[ t ]['exceptions']
		elif wildcard:
			wildcard = False
			sub = t.split(".",1).pop(0)
			if not sub in exceptions :
				offset = dots
		dots -= 1

	# TLD not found
	if offset < 0 :
		return None

	t = h.split(".", offset)[-1]
	return t	


    def _parse_extended(self, url):

	u = self._parse_simple(url)

	# work the hostname from the netloc which can contains user:pass and/or port
	hostname  = u.netloc

	# extract the port from the netloc if it exists
	tmp = u.netloc.split(':')

	if len(tmp) > 1 : 
		p = tmp.pop()
		if p.isdigit() :
			u.set('port', p)
			hostname = hostname[:-(len(p)+1)]

	# extract user:pass from netloc
	tmp = u.netloc.rsplit('@',1)
	if len(tmp) > 1 :
		hostname = hostname[len(tmp[0])+1:]
		
		t = tmp[0].split(':', 1)
		user = t.pop(0)
		password = None
		if len(t) :
			password = t.pop(0)

		u.set('username', user)
		u.set('password', password)

	u.set('hostname', hostname)

	# ipv4 ?
	if self.reg_t_ipv4.search(u.hostname) :
		return u 

	tld = self.findTLD(u.hostname)
	if tld == None :
		self.logger.warning("no TLD found for %s (hostname: %s)" % (url, hostname))
		return u 

	tlen = len(tld)
	u.set('tld', u.hostname[-tlen:]) # because 'tld' is lowered

	# domain without tld
	tn_dots = tld.count(".") # 0+
	hn_dots = u.hostname.count(".") # 1+

	if (hn_dots - tn_dots) > 0 :
		parts = u.hostname.split(".", hn_dots - (tn_dots+1))

		u.set('domain', parts.pop())
		u.set('subdomain', ".".join(parts))
		u.set('subdomain_depth', len(parts))
		u.set('domain_without_tld', u.domain[:-(tlen+1)])

		# subdomains
		sp = {}
		i  = u.subdomain_depth
		for p in parts:
			sp[ i ] = p
			i -= 1
		u.set('subdomain_parts', json.dumps({'url_subdomain':sp}))
	return u 




    def loadTLDList(self, listname):
	"""
	Load the appropriate TLD List:

	Examples:
	- mozilla|iana: load the mozilla and iana lists
	- iana|pouet  : load the iana and pouet lists
	- *           : all available lists
	- <listname>  : the specified list

	By default, urlparser is shipped with the iana and mozilla lists.
	"""
	self.TLDStruct = {}
	listname = listname.lower().strip()

	# simply list all existing lists to load them
	if listname == "*" :
		suffix_dir_path = make_splunkhome_path(["etc", "apps", "urlparser", "suffix_lists"])
		files = os.listdir( suffix_dir_path )

		tmp = []
		for f in files:
			f = f.lower()
			if re.search('\.dat$', f) :
				l = f.split("_")[-1][:-4]
				tmp.append( l )
		listname = "|".join( tmp )

	# load the specified lists
	lists = listname.split("|")
	self.logger.debug("loading TLD lists: %s" % lists)

	for listname in lists:
		filename = "suffix_list_%s.dat" % listname.strip()
		filepath = make_splunkhome_path(["etc", "apps", "urlparser", "suffix_lists", filename])

		if not os.path.exists( filepath ) :
			self.logger.error("the list %s does not exists, skipping." % filepath)
			continue
	
		try:
			fd = codecs.open(filepath, "r", "utf-8")
			data = fd.readlines()
			fd.close()
		except Exception,e :
			raise e

		# remove empty lines and  lines starting with '#' or '//'
		data = filter(lambda x: not x.startswith(("#", "//")) and x!="", map(unicode.strip, data))
		data = map(unicode.lower, data)

		# convert tld to their ascii form: 
		# u'\u043c\u043e\u0441\u043a\u0432\u0430' == xn--80adxhks	
		for tld in data:
			t = codecs.encode(tld, "idna").lower()

			if t.startswith('*') and len(t)>2 :
				t = t[2:] # *.ck => ck

				if not t in self.TLDStruct :
					self.TLDStruct[ t ] = {'wildcard':True, 'exceptions':[]}
				self.TLDStruct[ t ]['wildcard'] = True

			elif t.startswith('!') :
				t = t[1:] # !www.ck -> www.ck
				e = t.split('.', 1).pop(0) # www
				elen = len(e)   # 3
				tlen = len(t)
				t = t[-(tlen-elen-1):] # ck

				if not t in self.TLDStruct : 
					 self.TLDStruct[ t ] = {'wildcard':True, 'exceptions':[e]}
				if not e in self.TLDStruct[ t ]['exceptions'] :
					self.TLDStruct[ t ]['exceptions'].append( e )

			else: 
				if not t in self.TLDStruct :
					self.TLDStruct[ t ] = {'wildcard':False, 'exceptions':[]}



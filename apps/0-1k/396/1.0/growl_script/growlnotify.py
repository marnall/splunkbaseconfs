#!/usr/bin/env python

# Growl Notification Script for Splunk
# by Siegfried Puchbauer - SPP
# splunk@spp.at

GROWL_HOST="127.0.0.1"
GROWL_REGISTRATION_PASSWORD="s3cret4splunk"

GROWL_NOTIFICATION_STICKY=False

"""Growl 0.6 Network Protocol Client for Python"""
__version__ = "0.6.3"
__author__ = "Rui Carmo (http://the.taoofmac.com)"
__copyright__ = "(C) 2004 Rui Carmo. Code under BSD License."
__contributors__ = "Ingmar J Stein (Growl Team), John Morrissey (hashlib patch)"

try:
  import hashlib
  md5_constructor = hashlib.md5
except ImportError:
  import md5
  md5_constructor = md5.new

import struct
from socket import AF_INET, SOCK_DGRAM, socket

GROWL_UDP_PORT=9887
GROWL_PROTOCOL_VERSION=1
GROWL_TYPE_REGISTRATION=0
GROWL_TYPE_NOTIFICATION=1

class GrowlRegistrationPacket:
  """Builds a Growl Network Registration packet.
	 Defaults to emulating the command-line growlnotify utility."""

  def __init__(self, application="growlnotify", password = None ):
	self.notifications = []
	self.defaults = [] # array of indexes into notifications
	self.application = application.encode("utf-8")
	self.password = password
  # end def


  def addNotification(self, notification="Command-Line Growl Notification", enabled=True):
	"""Adds a notification type and sets whether it is enabled on the GUI"""
	self.notifications.append(notification)
	if enabled:
	  self.defaults.append(len(self.notifications)-1)
  # end def


  def payload(self):
	"""Returns the packet payload."""
	self.data = struct.pack( "!BBH",
							 GROWL_PROTOCOL_VERSION,
							 GROWL_TYPE_REGISTRATION,
							 len(self.application) )
	self.data += struct.pack( "BB",
							  len(self.notifications),
							  len(self.defaults) )
	self.data += self.application
	for notification in self.notifications:
	  encoded = notification.encode("utf-8")
	  self.data += struct.pack("!H", len(encoded))
	  self.data += encoded
	for default in self.defaults:
	  self.data += struct.pack("B", default)
	self.checksum = md5_constructor()
	self.checksum.update(self.data)
	if self.password:
	   self.checksum.update(self.password)
	self.data += self.checksum.digest()
	return self.data
  # end def
# end class


class GrowlNotificationPacket:
  """Builds a Growl Network Notification packet.
	 Defaults to emulating the command-line growlnotify utility."""

  def __init__(self, application="growlnotify",
			   notification="Command-Line Growl Notification", title="Title",
			   description="Description", priority = 0, sticky = False, password = None ):
	self.application  = application.encode("utf-8")
	self.notification = notification.encode("utf-8")
	self.title		  = title.encode("utf-8")
	self.description  = description.encode("utf-8")
	flags = (priority & 0x07) * 2
	if priority < 0:
	  flags |= 0x08
	if sticky:
	  flags = flags | 0x0100
	self.data = struct.pack( "!BBHHHHH",
							 GROWL_PROTOCOL_VERSION,
							 GROWL_TYPE_NOTIFICATION,
							 flags,
							 len(self.notification),
							 len(self.title),
							 len(self.description),
							 len(self.application) )
	self.data += self.notification
	self.data += self.title
	self.data += self.description
	self.data += self.application
	self.checksum = md5_constructor()
	self.checksum.update(self.data)
	if password:
	   self.checksum.update(password)
	self.data += self.checksum.digest()
  # end def

  def payload(self):
	"""Returns the packet payload."""
	return self.data
  # end def
# end class

import sys

def registerGrowl():
	addr = (GROWL_HOST, GROWL_UDP_PORT)
	s = socket(AF_INET,SOCK_DGRAM)
	p = GrowlRegistrationPacket(application="Splunk", password=GROWL_REGISTRATION_PASSWORD)
	p.addNotification("Splunk Alert", enabled=True)
	s.sendto(p.payload(), addr)
	p = GrowlNotificationPacket(application="Splunk",
		notification="Splunk Alert", title="Splunk Notification",
		description="Splunk Alert Notifications registered", priority=1,
		sticky=GROWL_NOTIFICATION_STICKY, password=GROWL_REGISTRATION_PASSWORD)
	s.sendto(p.payload(),addr)
	s.close()
	print "Sent registration message!"

def growlNotify(title = "Splunk Alert", message = ""):
	
	addr = (GROWL_HOST, GROWL_UDP_PORT)
	s = socket(AF_INET,SOCK_DGRAM)
	
	p = GrowlNotificationPacket(application="Splunk",
		notification="Splunk Alert", title=title,
		description=message, priority=1,
		sticky=GROWL_NOTIFICATION_STICKY, password=GROWL_REGISTRATION_PASSWORD)
	s.sendto(p.payload(),addr)
	s.close()

if __name__ == '__main__':
	if len(sys.argv) > 1:
		if sys.argv[1] == "--register":
			registerGrowl()
		else:
			count,search,fq_search,title,reason,url,not_used,result_file = sys.argv[1:9]
			if title.find("--inline") >= 0:
				import gzip,csv
				f = gzip.open(result_file)
				csv = csv.DictReader(f)
				for row in csv:
					if 'growl_msg' in row:
						growlNotify(title=title.replace("--inline",""), message=row['growl_msg'])
			else:
				growlNotify(title=title, message="%s %s" % (count, "result" if count == "1" else "results"))
	else:
		print "Usage python growlnotfy.py --register"
	

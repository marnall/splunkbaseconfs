import httplib, socket
import os
import sys
import splunk.clilib.cli_common
from datetime import datetime, date, time

def splkbool( dkey="" ):
	if dkey == "true":
		return 1
	if dkey == "True":
		return 1
	if dkey == "1":
		return 1

	return 0

settingpath = os.path.join(sys.path[0], "..", "local", "pinger")

splunk.clilib.cli_common.cacheConfFile(settingpath)
splunk.clilib.cli_common.confSettings[settingpath]

uastr = 'SplunkPinger/1.0 +http://www.splunk.com/'
headers = { "User-Agent" : uastr }
default_location = "Default"
default_prod = "1"
default_ext = "1"
default_timeout = 2

defset = splunk.clilib.cli_common.getConfStanza(settingpath, "default")

if defset.has_key("location"):
	default_location = defset["location"]
if defset.has_key("prod"):
	default_prod = str(splkbool(defset["prod"]))
if defset.has_key("external"):
	default_ext = str(splkbool(defset["external"]))
if defset.has_key("timeout"):
	default_timeout = int(defset["timeout"])

for key, value in splunk.clilib.cli_common.confSettings[settingpath].items():
	settings = splunk.clilib.cli_common.getConfStanza(settingpath, key)

	if settings.has_key("location"):
		location = settings["location"]
	else:
		location = default_location

	if settings.has_key("prod"):
		prod = str(splkbool(settings["prod"]))
	else:
		prod = default_prod

	if settings.has_key("external"):
		ext = str(splkbool(settings["external"]))
	else:
		ext = default_ext

	if settings.has_key("timeout"):
		to = int(settings["timeout"])
	else:
		to = default_timeout

	if settings.has_key("host"):
		if settings.has_key("port"):
			port = settings["port"]
		elif settings.has_key("ssl") and splkbool(settings["ssl"]) == 1:
			port = 443
		else:
			port = 80

		dnt1 = datetime.now()

		if settings.has_key("lookupdns") and splkbool(settings["lookupdns"]) == 1:
			socket.gethostbyname(settings["host"])
			dnt2 = datetime.now()
			dnstime = dnt2 - dnt1
		else:
			dnstime = dnt1 - dnt1

		stime = datetime.now()

		if settings.has_key("ssl") and splkbool(settings["ssl"]) == 1:
			conn = httplib.HTTPSConnection(settings["host"], port, timeout=to)
		else:
			conn = httplib.HTTPConnection(settings["host"], port, timeout=to)

		if settings.has_key("resource"):
			useresource = settings["resource"]
		else:
			useresource = "/"

		ctime = datetime.now()
		cdelta = ctime - stime

		if settings.has_key("username") and settings.has_key("password"):
			import base64
			httpauth = base64.encodestring('%s:%s' % ( settings["username"], settings["password"] ) ) [:-1]
			authheaders = { 'Authorization' : "Basic %s" % httpauth }
			headers.update( authheaders )

		allgood = True

		if settings.has_key("label"):
			uselabel = settings["label"]
		else:
			uselabel = settings["host"]

		try:
			conn.request("GET", useresource, "", headers)
			r1 = conn.getresponse()
		except Exception as e:
			allgood = False
			msg = str(e)

			if isinstance(e, socket.gaierror):
				code = "016"
			elif isinstance(e, socket.herror):
				code = "015"
			elif isinstance( e, socket.timeout):
				code = "014"
			elif isinstance( e, socket.error):
				code = "013"
			elif isinstance(e, httplib.BadStatusLine):
				code = "012"
			elif isinstance(e, httplib.ResponseNotReady):
				code = "011"
			elif isinstance(e, httplib.CannotSendHeader):
				code = "010"
			elif isinstance(e, httplib.CannotSendRequest):
				code = "009"
			elif isinstance(e, httplib.ImproperConnectionState):
				code = "008"
			elif isinstance(e, httplib.IncompleteRead):
				code = "007"
			elif isinstance(e, httplib.UnimplementedFileMode):
				code = "006"
			elif isinstance(e, httplib.UnknownTransferEncoding):
				code = "005"
			elif isinstance(e, httplib.UnknownProtocol):
				code = "004"
			elif isinstance(e, httplib.InvalidURL):
				code = "003"
			elif isinstance(e, httplib.NotConnected):
				code = "002"
			elif isinstance(e, httplib.HTTPException):
				code = "001"
			else:
				code = "000"

		dt = datetime.now()

		if allgood == False:
			print dt.strftime("%Y-%m-%d %H:%M:%S") + " site=" + uselabel + " domain=" + settings["host"] + " resource=" + useresource + " location=" + location + " status=" + code + " connect_time=" + str(cdelta.seconds) + "." + str(cdelta.microseconds) + " request_time=0.0 bytes=0 dns=0.0 prod=" + prod + " ext=" + ext + " message=\"" + msg + "\""
			continue

		r1stat = str(r1.status)
		etime = datetime.now()
		delta = etime - ctime
		data = r1.read()
		bytes = len(data)

		print dt.strftime("%Y-%m-%d %H:%M:%S") + " site=" + uselabel + " domain=" + settings["host"] + " resource=" + useresource + " location=" + location + " status=" + r1stat + " connect_time=" + str(cdelta.seconds) + "." + str(cdelta.microseconds) + " request_time=" + str(delta.seconds) + "." + str(delta.microseconds) + " bytes=" + str(bytes) + " dns=" + str(dnstime.seconds) + "." + str(dnstime.microseconds) + " prod=" + prod + " ext=" + ext + " message=\"Normal\""

		conn.close()

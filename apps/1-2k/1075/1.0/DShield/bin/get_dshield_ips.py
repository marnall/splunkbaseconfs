import urllib2
import re
import os

# ISC All Source IPs URL
iscurl = 'http://isc.sans.edu/feeds/daily_sources'

# Temporary file name
tempfile = 'file.tmp'

# File we write processed DShield logs into
outfile = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'DShield', 'logs', "dshield.log")

u = urllib2.urlopen(iscurl)
localFile = open(tempfile, 'w')
localFile.write(u.read())
localFile.close

# Now process file

f = open(tempfile, 'r')
fo = open(outfile, 'w')

for line in f:
	if line[0] == '#':
		continue
	else:
		matcher = re.match(r"^([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)", line)
		if matcher.group(0):
			# Fix IP addresses since they have leading zero
			ipmatch = re.match(r"0{0,2}(\d+)\.0{0,2}(\d+)\.0{0,2}(\d+)\.0{0,2}(\d+)",matcher.group(1))
			ipaddress = ipmatch.group(1) + '.' + ipmatch.group(2) + '.' + ipmatch.group(3) + '.' + ipmatch.group(4)
			log = ipaddress + "\t" + matcher.group(2) + "\t" + matcher.group(3) + "\t" + matcher.group(4) + "\t" + matcher.group(5) + "\t" + matcher.group(6) + "\t" + matcher.group(7) + "\n"
			fo.write(log)

f.close
fo.close

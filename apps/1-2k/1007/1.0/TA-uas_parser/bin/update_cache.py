# This will update the UASParser cache
from uasparser import UASparser
uas_parser = UASparser('ua_cache')
results = uas_parser.updateData()
if results:
	print "Cache data updated."
else:
	print "Error updating cache data."

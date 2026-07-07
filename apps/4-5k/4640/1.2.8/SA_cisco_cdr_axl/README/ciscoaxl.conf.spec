[<host>:<port>:<username>]

# This is no longer used, but may be present in legacy config.  Current versions of the app
# use Splunk's passwords endpoint to store passwords encrypted on disk.
# Note that this means you cannot technically seed a working list of stanzas simply by creating
# ciscoaxl.conf on disk.   Or if you do, you must then go to Update Credentials and explicitly
# add their password entries to create the entries in splunk's password storage.
password = <string>

# This key specifies a single regex that is used inside the ciscoaxlquery
# command. Be careful editing it, as mistakes can easily allow queries to
# make unwanted changes to your database.
# Note if the key is ever left entirely blank, the command will refuse to run
# because we consider it too high a risk that the blank config is a mistake.
# See default/ciscoaxl.conf for the default regex used to define the
# blacklist
queryblacklist = <string>

# This key specifies a single regex trhat is used inside the ciscoaxl
# command. The net result is to ONLY allow command strings that match this
# regex.  See default/ciscoaxl.conf for the default regex used to define the
# whitelist.
# Note if the key is ever left entirely blank, the command will refuse to run
# because we consider it too high a risk that the blank config is a mistake.
methodwhitelist = <string>

# this OPTIONAL key specifies the relative path (must be contained within the SA app itself),
# where the wsdl file is located that Splunk should use to make the SOAP request to
# the given UCM node.   Our docs will explain this more but in general the WSDL file
# must match the UCM version exactly.
# defaults to bin (see default/ciscoaxl.conf in the app )
# In practice it is best to leave a main wsdl file sitting in the bin directory, and
# to override this key for the subset of stanzas that have different version(s)
wsdl_subdirectory = <string>

#this sets the read timeout on the SOAP calls the app makes to AXL.
timeout = <integer>

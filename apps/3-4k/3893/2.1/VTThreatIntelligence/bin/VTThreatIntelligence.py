import os
import sys
#import requests
import json
import time
import urllib2

from splunklib.modularinput import *


class MyScript(Script):
    # Define some global variables
	#MASK = "<nothing to see here>"
	APP = __file__.split(os.sep)[-3]
	#API = None
	def get_scheme(self):

		scheme = Scheme("Virustotal Intelligence API key")
		scheme.description = ("Virustotal Intelligence API key Hunter")
		scheme.use_external_validation = True
#		scheme.streaming_mode_xml = True
		scheme.use_single_instance = False

		api_arg = Argument(
			name="api",
			title="API Code",
			data_type=Argument.data_type_string,
			required_on_create=True,
			required_on_edit=True
		)
		scheme.add_argument(api_arg)


		return scheme

	def validate_input(self, definition):
		api = definition.parameters["api"]

	try:
		# Do checks here.  For example, try to connect to whatever you need the credentials for using the credentials provided.
		# If everything passes, create a credential with the provided input.
		pass
	except Exception as e:
		raise Exception, "Something did not go right: %s" % str(e)


	def stream_events(self, inputs, ew):
		ew.log("INFO","Adding data")
		for input_name, input_item in inputs.inputs.iteritems():
#			self.input_name, self.input_items = inputs.inputs.popitem()
			api = input_item["api"]
#			self.API = api
			list=[]
			count=0
			try:
				r = urllib2.Request("https://www.virustotal.com/intelligence/hunting/notifications-feed/?key={0:s}&output=json".format(api))
				t = json.loads(urllib2.urlopen(r).read())

				#r = requests.get("https://www.virustotal.com/intelligence/hunting/notifications-feed/?key={0:s}&output=json".format(api))
				#t = json.loads(r.content)
			except Exception as e:
				ew.log("ERROR", "Error: %s" % str(e))

			try:
				for elements in t['notifications']:
					#ew.log("INFO","Adding dataelemnts")
					logevent = Event()
					logevent.stanza = input_name
					#logevent.index = main
					logevent.data = json.dumps(elements, sort_keys=True, separators=(',',':'))
					#logevent.data = json.dumps(elements, sort_keys=False)
					ew.write_event(logevent)
					list.append(t['notifications'][count]['id'])
        				count=count+1
				ew.log("INFO","Added %s reqister" % str(count))
			except Exception as e:
				ew.log("ERROR", "Error: %s" % str(e))
		#p = requests.post("https://www.virustotal.com/intelligence/hunting/delete-notifications/programmatic/?key={0:s}".format(api), data=json.dumps(list), headers = {'Content-type': 'application/json'})
		p = urllib2.urlopen(urllib2.Request("https://www.virustotal.com/intelligence/hunting/delete-notifications/programmatic/?key={0:s}".format(api),headers={'Content-type': 'application/json'},data=json.dumps(list)))
		ew.log("INFO","Deletting data %s" % str(p.read()))

if __name__ == "__main__":
	exitcode = MyScript().run(sys.argv)
	sys.exit(exitcode)

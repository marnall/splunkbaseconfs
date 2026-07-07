import json
import logging
from pprint import pprint

from splunk import auth, search
import splunk.rest 
from splunk import util
import splunk.entity as en

# set up logging suitable for splunkd consumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

class main(splunk.rest.BaseRestHandler):
	'''
	Main endpoint
	'''	
	def handle_GET(self):
		# set output params
		
		logging.info("Getting TEMS Creds")
		creds = en.getEntity(['storage', 'passwords'], entityName=self.args['entity'], namespace='ITM6',owner='nobody', sessionKey=self.request['systemAuth'])
		self.response.setStatus(200)
		self.response.setHeader('content-type', 'application/json')
		#self.response.write(json.dumps({'password': creds['clear_password']}))

		content = json.dumps({
			'password': creds['clear_password']
		})
		
		
		self.response.write(content)
		#self.response.write('Main: this is the sessionkey %s</br>' % creds['clear_password'])
		#self.response.write('Self: ' + str(vars(self)))

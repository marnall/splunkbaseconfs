import requests
import time
import sys
import threading
import joblib
#from importlib.machinery import SourceFileLoader
#joblib = SourceFileLoader("joblib", "/home/ubuntu/.local/lib/python3.6/site-packages/joblib/__init__.py").load_module()
# disable possible warnings for clear output
requests.packages.urllib3.disable_warnings()

class SMBGrabber:
	def __init__(self, pvx_ip=None, pvx_api_key=None, time_offset=150):
		self.set_params(pvx_ip, pvx_api_key, time_offset)

	def set_params(self, pvx_ip, pvx_api_key, time_offset):
		self.pvx_ip = pvx_ip
		self.pvx_api_key = pvx_api_key 
		self.time_offset = time_offset

		self.request_headers = {'PVX-Authorization': self.pvx_api_key}
		self.request_url = ('https://{}/api/query?expr=query.payload%2C%20response.payload%20FROM%20smb%20by%20time%28%29%2C%20server.ip' + \
							'%2C%20client.ip%2C%20server.port%2C%20client.port%2C%20file%2C%20file.id%2C%20user%2C%20domain%2C%20tree%2C' + \
							'%20tree.id%2C%20smb.command%2C%20smb.status%2C%20smb.version%2C%20application%2C%20layer%20SINCE%20%40now-{}') \
							.format(self.pvx_ip, self.time_offset)

	def parse_pvx_response(self, response_json):
		packets = []
		for packet in response_json['result']['data']:
			smb_command = packet['key'][11].get('value')
			bytes_in = int(packet['values'][1].get('value'))
			bytes_out = int(packet['values'][0].get('value'))

			res = {
				'action': 'allowed',
				'time': int(float(packet['key'][0]['value'])),
				'dest_ip': packet['key'][1].get('value'),
				'src_ip': packet['key'][2].get('value'),
				'dest_port': packet['key'][3].get('value'),
				'src_port': packet['key'][4].get('value'),
				'file_name': packet['key'][5].get('value'),
				'user': packet['key'][7].get('value'),
				'dest_nt_domain': packet['key'][8].get('value'),
				'tree': packet['key'][9].get('value'),
				'smb_command_1': smb_command[0],
				'smb_command_2': smb_command[1],  
				'smb_status': packet['key'][12].get('value'),
				'smb_version': packet['key'][13].get('value'),
				'layer': packet['key'][15].get('value'),
				'app': 'smb',
				'bytes': bytes_in + bytes_out,
				'bytes_out': bytes_out,
				'bytes_in': bytes_in,
			}
			
			for k, v in res.items():
				if v == None:
					res[k] = 0
					
			packets.append(res)

		return packets

	def grab_traffic(self, on_response_callback):
		try:
			response = requests.get(self.request_url, headers=self.request_headers, verify=False, timeout=15)
		except Exception as e:
			return str(e)

		response_json = response.json()
		if 'result' in response_json and 'data' in response_json['result']:
			packets = self.parse_pvx_response(response_json)
			on_response_callback(packets)

		elif 'type' in response_json and response_json['type'] == 'error':
			#print('Bad response from PVX: ' + str(response_json), file=sys.stdout)
			pass
			
		#time.sleep(self.time_offset)


class SMBPredictor:
	def __init__(self, smb_grabber=None, model_filename=None):
		self.set_params(smb_grabber, model_filename)

	def set_params(self, smb_grabber, model_filename):
		self.smb_grabber = smb_grabber
		self.model_filename = model_filename
		self.model = joblib.load(self.model_filename)

	def real_time_predict(self, on_response_callback):
		def make_prediction(packets):
			traffic = [[packet['dest_port'], packet['src_port'], packet['smb_command_1'], packet['smb_command_2'],
		    	packet['smb_status'], packet['smb_version'], packet['bytes'], packet['bytes_out'], packet['bytes_in']] for packet in packets]
		    	
			prediction = self.model.predict(traffic)

			return on_response_callback(packets, prediction)

		self.smb_grabber.grab_traffic(make_prediction)

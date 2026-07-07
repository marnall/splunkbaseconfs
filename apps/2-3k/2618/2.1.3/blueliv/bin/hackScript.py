# -*- coding: utf8 -*-
import json
from navigator import Navigator

class afapiHack():

	def __init__(self):
		self.download = Navigator()
		self.baseUrl = 'https://api.blueliv.com/v1/statistics/hacktivism/operationsByTimeLine'
	
	def __print_output(self, response):
		response = json.loads(response)
		print ("symbol,date,price")
		strOut = ''
		for operation in response["operations"]:
			h = 0
			m = 1
			hour = "00"
			min = "00"
			for day in operation["days"]:
				h = 0
				m = 1
				hour = "00"
				min = "00"
				for value in day["values"]:
					strOut = operation["hashtag"] +',' +day["day"]+' '+hour+':'+min+','+str(value)
					m = m + 1
					if(m % 2 == 0):
						min = "30"
					else:
						h = h + 1
						if h < 10:
							hour = "0"+str(h)
						else:
							hour = str(h)
						min = "00"
					print (strOut.encode('utf-8'))
					strOut = ''

	def parser(self):
		
		url = self.baseUrl
		response = self.download.go(url).encode('utf-8')
		if len(response) > 0:
			self.__print_output(response)
		else:
			with open("hack_test_data.json","r") as f:
				response = f.read()
			self.__print_output(response)
							
if __name__ == '__main__':
	site = afapiHack()
	site.parser()

	

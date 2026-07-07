# -*- coding: utf8 -*-
from navigator import Navigator
import json

class afapiHackMap():

	def __init__(self):
		self.download = Navigator()
		self.baseUrl = 'https://api.blueliv.com/v1/statistics/hacktivism/byCountry'
	
	def __print_output(self,response):
		response = json.loads(response)
		print "iso,total"
		strOut = ''
		for country in response["countries"]:
			strOut = country["iso"]+','+str(country["total"])
			print strOut.encode('utf-8')
			strOut = ''

	def parser(self):
		url = self.baseUrl
		response = self.download.go(url)
		if len(response) > 0:
			self.__print_output(response)
		else:
			with open("map_test_data.json","r") as f:
				response = f.read()
			self.__print_output(response)
							
if __name__ == '__main__':
	site = afapiHackMap()
	site.parser()

	

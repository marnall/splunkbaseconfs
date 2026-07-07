# -*- coding: utf-8 -*
class StringUtils():

	def clean_str(self,value):
		dict = {
			'_' : ' ',
			'AND' : '&'
		}

		for key, val in dict.iteritems():
			value = value.replace(key, val) if key in value else value

		return ' '.join(dict[value.lower()] if value.lower() in dict else value.title() for value in value.split(' '))
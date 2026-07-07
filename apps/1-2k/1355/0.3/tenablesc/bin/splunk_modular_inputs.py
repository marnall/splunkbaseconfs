#!/usr/bin/python

# copyright Satisnet Ltd.   2013
# Licensed LGPL v3

import sys
import xml.dom.minidom, xml.sax.saxutils
import logging
import json
import time
import md5
import os

class modular_inputs:    
	def __init__(self):
		try:
			# read stdin to get xml
			self.xmlstr = sys.stdin.read()
			self.config = {}

			# initialize defaults
			self.record_id = 0
			self.lastrun = 0 

		        # parse the config XML
        		self.doc = xml.dom.minidom.parseString(self.xmlstr)
        		self.root = self.doc.documentElement
        		self.conf_node = self.root.getElementsByTagName("configuration")[0]
        
			if self.conf_node:
            			logging.debug("XML: found configuration")
            			self.stanza = self.conf_node.getElementsByTagName("stanza")[0]
            		
			if self.stanza:
                		self.stanza_name = self.stanza.getAttribute("name")
                	if self.stanza_name:
                    		logging.debug("XML: found stanza " + self.stanza_name)
                    		self.config["name"] = self.stanza_name

                    	params = self.stanza.getElementsByTagName("param")
                    	for param in params:
                        	param_name = param.getAttribute("name")
                        	logging.debug("XML: found param '%s'" % param_name)
                        	if param_name and param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            		data = param.firstChild.data
                            		self.config[param_name] = data
                            		logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        		checkpnt_node = self.root.getElementsByTagName("checkpoint_dir")[0]
        		if checkpnt_node and checkpnt_node.firstChild and checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            			self.config["checkpoint_dir"] = checkpnt_node.firstChild.data
				self.set_checkpoint_file()

        		if not self.config:
            			raise Exception, "Invalid configuration received from Splunk."

    		except Exception, e:
			raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

	def get_config(self,item):
		try:
			if not self.config[item]:
				raise Exception, "Error getting Splunk configuration item : %s" % str(item)
			return self.config[item]
		except Exception, e:
			raise Exception, "Error processing Splunk configuration: %s" % str(e)

	def set_checkpoint_file(self):
		self.config["checkpoint_file"] = ""
		# strip out invalid path/file characters
		for i in range(len(self.config["name"])):
			if self.config["name"][i].isalnum():
				self.config["checkpoint_file"] += self.config["name"][i]
			else:
				self.config["checkpoint_file"] += "_"

		# now create an md5 for extra uniqness
		self.config["checkpoint_md5"] = md5.new()
		self.config["checkpoint_md5"].update(self.config["name"])

		# the checkpoint file should be a combination of both the 
		# sanitized name and the md5 of the un-sanitized name
		self.config["checkpoint_file"] += "_" + self.config["checkpoint_md5"].hexdigest()
		self.config["checkpoint_filepath"] = os.path.join(self.config["checkpoint_dir"], self.config["checkpoint_file"])

	def save_checkpoint(self):
		try:
			logging.info("Checkpointing name=%s file=%s", self.config["name"], self.config["checkpoint_filepath"])
			f = open(self.config["checkpoint_filepath"],"w")
			f.write(json.dumps([time.time(), self.record_id]))
			f.close()
		except Exception, e:
			raise Exception, "Error saving checkpoint: %s" %str(e)

	def load_checkpoint(self):
		try:
			logging.info("Checkpointing loading name=%s", self.config["name"])
			f = open(self.config["checkpoint_filepath"],"r")
			tmpjson = f.read()
			tmp = json.loads(tmpjson)
			if len(tmp) == 2:
				self.lastrun = tmp[0]
				self.record_id = tmp[1]

		except:
			# there may be no checkpoint file
			return False
		return True
	
	def get_lastrun(self):
		return self.lastrun
	
	def get_record_id(self):
		return self.record_id

	def set_record_id(self,record_id):
		self.record_id = record_id

				

	@staticmethod
	def print_error(s):
    		print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)

	@staticmethod
	def do_scheme(scheme):
    		print scheme

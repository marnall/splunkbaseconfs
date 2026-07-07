#!/usr/bin/env python
import datetime, time
import json
import csv
import codecs, sys
from cexc import BaseChunkHandler


def RaiseError(errormsg, metadata={ "finished": "finished"}):
  test=[{"ERROR": errormsg}]
  return (
          {'finished': metadata['finished']}, test
          
      )

class PointerSet(BaseChunkHandler):

    def _parse_arguments(self, args):
        
    	setattr(self, "field", False)
	setattr(self, "pointer", False)
	setattr(self, "default", False)
	setattr(self, "ptrFieldFilter", False)

	self.numTokens = 0
	self.default = ""

	for token in args:
        	if not '=' in token:
        		self.field = token
	        	self.numTokens += 1
        		continue
    
	        (k,v) = token.split('=', 1)

		if v == False:
			v = ""

        	# ignore everything expect the following arguments:
	        if k in ["pointer", "default", "ptrFieldFilter"]:
    			setattr(self, k, v)


	if self.field == False:
		raise Exception("Missing target field -- Usage: pointerset <target-field> pointer=<field> ptrFieldFilter<fieldName_pattern*>") 
	if self.pointer == False:
        	raise Exception("Missing pointer field -- Usage: pointerset <target-field> pointer=<field> ptrFieldFilter<fieldName_pattern*>") 
	if self.numTokens > 1:
		raise Exception("More than one target field found -- Usage: pointerset <target-field> pointer=<field> ptrFieldFilter<fieldName_pattern*>") 

    # metadata is a dict with the parsed JSON metadata payload.
    # data is a list of dicts, where each dict represents a search result.
    def handler(self, metadata, data):

        # The first chunk is a "getinfo" chunk.
        if metadata['action'] == 'getinfo':
          try:
            args = metadata['searchinfo']['args']
          except:
            args = []

	  # Parse all the arguments
          self._parse_arguments(args)

	  myRequiredFields = [self.pointer]
	  
	  if self.ptrFieldFilter != False:
		tmpFieldFilters = []
		tmpFieldFilters = self.ptrFieldFilter.split('|')
	
		for field in tmpFieldFilters:
			if str(field) != "":
				myRequiredFields.append(str(field))
			else:

				myRequiredFields.append("*")
	  else:
		myRequiredFields = ["*"]

	  # Listing of all fields that Splunk will return as part of the "data", using * to return everything as we don't know what field 'pointer' will be pointing at for each row.
	  return {'type': 'streaming', 'required_fields': myRequiredFields }


	if self.field == False:
		raise Exception("Missing target field -- Usage: pointerset <target-field> pointer=<field> ptrFieldFilter<fieldName_pattern*>") 
        if self.pointer == False:
                raise Exception("Missing pointer field -- Usage: pointerset <target-field> pointer=<field> ptrFieldFilter<fieldName_pattern*>") 
	if self.numTokens > 1:
		raise Exception("More than one target field found -- Usage: pointerset <target-field> pointer=<field> ptrFieldFilter<fieldName_pattern*>") 



# Now let's actually analyze our data
	for record in data:
		try:
			record.update({self.field: str(record.get(str(record.get(self.pointer,"")),self.default)) })
		except ValueError:
			record.update({self.field: self.default})

	return (
							{'finished': metadata['finished']},
							data
					)


if __name__ == "__main__":
    PointerSet().run()

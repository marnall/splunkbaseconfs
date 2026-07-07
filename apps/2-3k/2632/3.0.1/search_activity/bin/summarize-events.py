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
class DoubleData(BaseChunkHandler):

    def _parse_arguments(self, args):
        self.field = "bighappyfamily"
    # metadata is a dict with the parsed JSON metadata payload.
    # data is a list of dicts, where each dict represents a search result.
    def handler(self, metadata, data):

        # The first chunk is a "getinfo" chunk.
        if metadata['action'] == 'getinfo':
          try:
            args = metadata['searchinfo']['args']
          except:
            args = []

          self._parse_arguments(args)
          
          return {'type': 'streaming', 'required_fields':[ self.field, "Message", "type", "_time" , "*"]}

	def describeEvents(obj):
		if obj['type'] == "search":
			counter = 0
			total_results = 0
			trt = 0
			
			for search in obj['supplement']:
				counter += 1
				trt += float(search['total_run_time'])
				total_results += int(search['result_count'])
			obj['Message'] = "User ran " + str(counter) + " searches, running for a total of " + str( round(trt / 60,2) ) + " minutes and returning " + str(total_results) + " results."
			return obj
		else:
			return obj


# Now let's actually analyze our data
	newReturn = list()
	lastVal = dict()
	for record in data:
		try:
			# record.update({"doubled": ", ".join(record.keys())})
			# newReturn.append(record)
			supplement = dict()
			
			for key in record.keys():
				if key=="_time" or ((not "_" in key or key.index("_") != 0 ) and key!="type" and key!="Message" and key!="by" and record[key]!=""):
					supplement[key] = record[key]
					
			now = datetime.datetime.fromtimestamp( float(record["_time"]) )
			round_mins = 5
			mins = now.minute - (now.minute % round_mins) #Rounding down to nearest 5 minutes
			newTime = datetime.datetime(now.year, now.month, now.day, now.hour, mins) + datetime.timedelta(minutes=round_mins)
			record["_time"] = (newTime - datetime.datetime(1970,1,1)).total_seconds()
			if len(lastVal) == 0:
				lastVal = record
				lastVal['myType'] = record['type']
				lastVal['count'] = 1
				lastVal['supplement'] = list()
				lastVal['supplement'].append(supplement)
			else:
				if record['type'] == lastVal['type'] and record["_time"] == lastVal["_time"]:
					lastVal['count'] += 1
					lastVal['supplement'].append(supplement)
				else:
					newReturn.append(describeEvents(lastVal))
					lastVal = record
					lastVal['myType'] = record['type']
					lastVal['count'] = 1
					lastVal['supplement'] = list()
					lastVal['supplement'].append(supplement)
			
		except ValueError:
			record.update({"doubled": ""})
			record["dvtest"] = json.dumps(record)
			newReturn.append(record)
		except KeyError:
			record.update({"doubled": ", ".join(record.keys())})
			record["dvtest"] = json.dumps(record)
			newReturn.append(record)
					

	return (
							{'finished': metadata['finished']},
							newReturn
					)


if __name__ == "__main__":
    DoubleData().run()
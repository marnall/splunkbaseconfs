#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import traceback
import urllib3
from splunklib.searchcommands import GeneratingCommand, Option, Configuration, dispatch

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@Configuration()
class ThreatmonSetStatusCommand(GeneratingCommand):
	alarm_id = Option(require=True)
	status = Option(require=True)
	api_url = Option(require=True)
	api_key = Option(require=True)

	def generate(self):
		allowed_statuses = ["Open", "In Progress", "False Positive", "Ignore", "Resolved"]
		if self.status not in allowed_statuses:
			yield {
				"alarmId": self.alarm_id,
				"status": self.status,
				"result": f"Invalid status value. Allowed values: {', '.join(allowed_statuses)}"
			}
			return
		http = urllib3.PoolManager()
		url = f"{self.api_url}/incident/status"
		headers = {"X-COMPANY-API-KEY": self.api_key, "accept": "application/json"}
		body = json.dumps({"status": self.status, "alarmIds": [self.alarm_id]})
		try:
			resp = http.request("PATCH", url, body=body, headers=headers)
			if resp.status == 200:
				yield {"alarmId": self.alarm_id, "status": self.status, "result": "status updated successfully"}
			else:
				yield {"alarmId": self.alarm_id, "status": self.status, "result": f"error {resp.status}: {resp.data.decode('utf-8', 'ignore')}"}
		except Exception as e:
			yield {"alarmId": self.alarm_id, "status": self.status, "result": f"exception {str(e)}"}

if __name__ == "__main__":
	dispatch(ThreatmonSetStatusCommand, sys.argv, sys.stdin, sys.stdout, __name__)

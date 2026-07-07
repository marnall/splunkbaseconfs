import sys
import json
import httplib, urllib


if sys.argv[1] == "--execute":
	payload = json.loads(sys.stdin.read())
	print >> sys.stderr, "INFO Payload: %s" % json.dumps(payload)

	params = payload.get('configuration')

	if "api.app_token" not in params or params["api.app_token"] == "" or "api.user_token" not in params or params["api.user_token"] == "" or "message" not in params or params["message"] == "":
		print >> sys.stderr, "FATAL Missing required params, exit."
		sys.exit(1)
		
	else:
		pushover_payload = {
			"token": params['api.app_token'],
			"user": params['api.user_token'],
			"message": params['message'],
		}

		if 'device' in params and params['device'] != "":
			pushover_payload.update({ "device": params['device']})

		if 'title' in params and params['title'] != "":
			pushover_payload.update({ "title": params['title']})

		if 'url' in params and params['url'] != "":
			pushover_payload.update({ "url": params['url']})

		if 'url_title' in params and params['url_title'] != "":
			pushover_payload.update({ "url_title": params['url_title']})

		if 'priority' in params and params['priority'] != "":
			if int(params['priority']) == 2:
				if 'expire' in params and params['expire'] != "":
					pushover_payload.update({ "retry": "30"})
					pushover_payload.update({ "priority": str(params['priority'])})
					pushover_payload.update({ "expire": str(params['expire'])})
				else:
					print >> sys.stderr, "FATAL Missing expire param, cannot send notification with emergency priority."
					sys.exit(2)
			else:
				pushover_payload.update({ "priority": str(params['priority'])})

		if 'timestamp' in params and params['timestamp'] != "":
			pushover_payload.update({ "timestamp": params['timestamp']})

		if 'sound' in params and params['sound'] != "":
			pushover_payload.update({ "sound": params['sound']})

		conn = httplib.HTTPSConnection(params['api.host'])
		conn.request("POST", params['api.ws'], urllib.urlencode(pushover_payload), { "Content-type": "application/x-www-form-urlencoded" })
		response = conn.getresponse()
		data = response.read()

		print >> sys.stderr, "INFO Status: %s" % response.status
		print >> sys.stderr, "INFO Reason: %s" % response.reason
		print >> sys.stderr, "INFO Data: %s" % data




import json
import traceback

import splunk.admin
import splunk.clilib.cli_common as scc
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

from ITOA.setup_logging import setup_logging

import resolve_consts
import utils

import httplib2

LOGGER = setup_logging("resolve_incident_resolution.log", "ResolveIncidentHandler")

class ResolveIncidentHandler(splunk.admin.MConfigHandler):
	def setup(self):
		self.supportedArgs.addReqArg('notable_event_id')

	def _get_resolve_account(self):
		app = resolve_consts.app_name
		resolve_conf = scc.getMergedConf("resolve")
		resolve_account = {}
		for stanza in ("resolve_default", "resolve_account", "resolve_proxy"):
			resolve_account.update(resolve_conf[stanza])

		sessionId = self.getSessionKey()
		mgmtURI = scc.getMgmtUri()
		accs = (("url", "username", "password"),
				("proxy_url", "proxy_username", "proxy_password"))
		for (url_k, user_k, pass_k) in accs:
			url = resolve_account[url_k]
			username = resolve_account[user_k]
			password = resolve_account[pass_k]
			resolve_account[user_k] = username
			resolve_account[pass_k] = password
		if resolve_account["proxy_port"]:
			resolve_account["proxy_port"] = int(resolve_account["proxy_port"])

		if utils.is_false(resolve_account["proxy_enabled"]):
			resolve_account["proxy_url"] = ""
			resolve_account["proxy_port"] = ""

		resolve_url = resolve_account["url"]
		if not resolve_url:
			raise Exception("Resolve Systems account has not been setup.")

		if not resolve_url.startswith("https://"):
			resolve_url = "https://%s" % resolve_url

		if not resolve_url.endswith("/"):
			resolve_url = "%s/" % resolve_url

		resolve_account["url"] = resolve_url
		resolve_account["release"] = resolve_account.get("release", "5.5").lower()
		# LOGGER.info("RESOLVE ACCOUNT : %s" % resolve_account)
		return resolve_account

	def _get_resolution_link(self, resolve_account, notable_event_id):
		LOGGER.info("********** {}".format(resolve_account));
		link = "{}resolve/jsp/rsclient.jsp?rid=true&autoCreate=true&rule_id={}&status=1&security_domain=threat".format(resolve_account["url"], notable_event_id)
		return link

	def _get_worksheet_link(self, resolve_account, worksheet_id):
		link = "{}resolve/jsp/rsclient.jsp#RS.worksheet.Worksheet/id={}&activeTab=1".format(resolve_account["url"], worksheet_id)
		return link

	def _build_error_response(self, response, code, error_msg):
		response.append("code", code)
		response.append("message", error_msg)

	def handleList(self, conf_info):
		# LOGGER.info("********** %s" % self.callerArgs.data)
		notable_event_id = self.callerArgs.data['notable_event_id'][0]
		resolve_account = self._get_resolve_account()
		LOGGER.info("Received request with Notable Event ID '%s'" % notable_event_id)
		# LOGGER.info("Received conf_info : %s" % conf_info)
		resp = conf_info["IncidentResult"]
		# url =#  "http://localhost.cloud.resolvesys.com:7777/SplunkNotableEventRR?rule_id={}&status=1&security_domain# =threat".format(notable_event_id)
		# gw_resp, gw_content = httplib2.Http().request(url)
		# # LOGGER.info("Response content: %s" % content)
		# message = json.loads(gw_content)
		# worksheet_id = message["Message"]["worksheetId"]
		# worksheet_url = self._get_worksheet_link(resolve_account, worksheet_id)
		# LOGGER.info("worksheet_id: %s, worksheet_url: %s" % (gw_content, worksheet_url))
		# LOGGER.info("Resolve account retrieved: %s" % resolve_account);
		# resp.append("worksheet_id", worksheet_id)
		# resp.append("worksheet_url", worksheet_url)
		resp.append("worksheet_id", "NEW")
		resp.append("worksheet_url", "{}resolve/jsp/rsclient.jsp?rid=true&autoCreate=true&rule_id={}&splunk_itsi=true".format(resolve_account["url"], notable_event_id))


def main():
	splunk.admin.init(ResolveIncidentHandler, splunk.admin.CONTEXT_NONE)

if __name__ == '__main__':
	main()

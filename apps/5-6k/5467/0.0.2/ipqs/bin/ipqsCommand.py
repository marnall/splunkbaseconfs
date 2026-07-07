import sys
import requests as req

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class ipqsCommand(StreamingCommand):

	ipfield = Option(doc=''' **Syntax:** **ipfield=***<fieldname>* **Description:** Name of the field containing the ip that will be looked up''', require=True, validate=validators.Fieldname())

	def stream(self, events):
		storage_passwords=self.service.storage_passwords
		for credential in storage_passwords:
			api_key = credential.content.get('clear_password')

		for event in events:
			ip = event[self.ipfield]
			request_url = "https://ipqualityscore.com/api/json/ip/{0}/{1}?strictness=0&allow_public_access_points=true&fast=true&lighter_penalties=true&mobile=true".format(api_key,ip)
			response=req.get(url=request_url)
			data=response.json()

			if data["success"] == 0:
				event['ipqs_result']=data["message"]
			else:
				event['ipqs_result']=data["message"]
				event['ipqs_fraud_score']=data["fraud_score"]
				event['ipqs_country_code']=data["country_code"]
				event['ipqs_region']=data["region"]
				event['ipqs_city']=data["city"]
				event['ipqs_ISP']=data["ISP"]
				event['ipqs_organization']=data["organization"]
				event['ipqs_latitude']=data["latitude"]
				event['ipqs_longitude']=data["longitude"]
				event['ipqs_is_crawler']=data["is_crawler"]
				event['ipqs_mobile']=data["mobile"]
				event['ipqs_host']=data["host"]
				event['ipqs_proxy']=data["proxy"]
				event['ipqs_vpn']=data["vpn"]
				event['ipqs_tor']=data["tor"]
				event['ipqs_active_vpn']=data["active_vpn"]
				event['ipqs_active_tor']=data["active_tor"]
				event['ipqs_recent_abuse']=data["recent_abuse"]
				event['ipqs_bot_status']=data["bot_status"]

			yield event

if __name__ == "__main__":
	dispatch(ipqsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
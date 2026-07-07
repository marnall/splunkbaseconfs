# ----------------------------------------------------------------------
# OpenDNS Investigate App for Splunk                       Set Solutions
#                                                   dev@setsolutions.com
#
# Todo:
# - Force order of additional columns to appear in order to the right.
# - Use SESSIONKEY for KV store interactions; issues with utils/parser.
# - Validate that IP matches both IPv6 and IPv4.
# - Need to deal with errors better, everywhere.
# - Fundamental: When searching, only the cache from the last poll is
#   used, regardless of age; but the method has to be able to provide
#   the data. Means potential duplicate polls.
# - Reduce redundant code.
# - Expand multi-value fields so it's more readable in Splunk?
# - New AMP API
# - Define all fields in collections.conf, that I forgot about.
# ----------------------------------------------------------------------

# :: Include libraries that should be in the Splunk Python
import os
import sys
import json
import time
import re

# :: Include any eggs that are in the eggs directory
eggs = os.path.dirname(__file__)
eggs = eggs+"/eggs/" if len(eggs) > 0 else "./eggs/"
for filename in os.listdir(eggs):
	if filename.endswith(".egg"):
		sys.path.append(eggs+filename)
import requests
import configparser
from splunklib.searchcommands import dispatch,StreamingCommand,Configuration,Option,validators
from splunklib.client import connect

# :: Load the configuration initialization file
cwd = os.path.dirname(__file__)
cwd = cwd+"/" if len(cwd) > 0 else "."
ini = configparser.ConfigParser()
ini.read(cwd+"../local/config.ini")

# ----------------------------------------------------------------------
# Initialization Function
# ----------------------------------------------------------------------
def odlInitialization():

	# :: Validate that the required values are present
	error = []
	if len(ini["opendns"]["address"]) == 0: error.append("Configuration value missing: opendns/address")
	if len(ini["opendns"]["apikey"]) == 0: error.append("Configuration value missing: opendns/apiKey")
	if int(ini["opendns"]["labels"]) not in [0,1]: error.append("Configuration value invalid or missing: opendns/labels")
	if int(ini["opendns"]["verify"]) not in [0,1]: error.append("Configuration value invalid or missing: opendns/verify")
	if len(ini["splunk"]["address"]) == 0: error.append("Configuration value missing: splunk/address")
	if len(ini["splunk"]["username"]) == 0: error.append("Configuration value missing: splunk/username")
	if len(ini["splunk"]["password"]) == 0: error.append("Configuration value missing: splunk/password")
	if int(ini["splunk"]["verify"]) not in [0,1]: error.append("Configuration value invalid or missing: opendns/verify")
	if len(ini["regex"]["domain"]) == 0: error.append("Configuration value missing: regex/domain")
	if len(ini["regex"]["ipv4n6"]) == 0: error.append("Configuration value missing: regex/ipv4n6")
	if len(error) > 0:
		sys.stderr.write("\n".join(error))
		exit(2)

	# :: Apply proxy settings if present
	if len(ini["proxy"]["address"]) > 0: os.environ["https_proxy"] = ini["proxy"]["address"]
	if len(ini["proxy"]["bypass"]) > 0: os.environ["no_proxy"] = ini["proxy"]["bypass"]

# ----------------------------------------------------------------------



# ----------------------------------------------------------------------
# Lookup Function
# ----------------------------------------------------------------------
def odlLookup(key,record,method,service):
	collect_time = time.time()
	newdata = False
	usecache = False

	# :: Lookup the Investigate API results for given record
	labels = "?showLabels" if ini["opendns"]["labels"] == "1" else ""
	if re.match(re.compile(ini["regex"]["domain"]),record[key]) and method in ["quick","smart","extended","whois"]:
		method_domain = record[key]
		method_ip = None

		# Poll the OpenDNS cache KV store; last record is latest (1/2)
		kvdata = json.dumps({"domain":record[key]})
		verify = False if ini["splunk"]["verify"] == "0" else True
		kvapir = requests.get(ini["splunk"]["address"]+"storage/collections/data/opendns_cache?query="+kvdata,auth=(ini["splunk"]["username"],ini["splunk"]["password"]),verify=verify,headers={"Content-Type":"application/json"})
		if kvapir.status_code == 200 and kvapir.text != "[ ]":
			cached = json.loads(kvapir.text)
			cached = cached[(len(cached)-1)]
		else: cached = []

		# Domain Status and Categorization
		if method in ["quick","smart","extended"]:
			if len(cached)>0 and cached["collect_type"] in ["quick","smart","extended"]:
				usecache = True
				record["opendns_api_collect_time"]        = cached["collect_time"]
				record["opendns_api_collect_type"]        = cached["collect_type"]
				record["opendns_status"]              = cached["status"]
				record["opendns_content_categories"]  = cached["content_categories"]
				record["opendns_security_categories"] = cached["security_categories"]
			else:
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_dsc_rquest = requests.get(ini["opendns"]["address"]+"/domains/categorization/"+record[key]+labels,headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_dsc_rquest.status_code == 200:
					newdata = True
					opendns_dsc_result = json.loads(opendns_dsc_rquest.text)
					record["opendns_api_collect_time"]        = collect_time
					record["opendns_api_collect_type"]        = method
					record["opendns_status"]              = opendns_dsc_result[record[key]]["status"]
					record["opendns_content_categories"]  = ",".join(opendns_dsc_result[record[key]]["content_categories"])
					record["opendns_security_categories"] = ",".join(opendns_dsc_result[record[key]]["security_categories"])

		# Security Information for a Domain
		if method == "extended" or (method == "smart" and record["opendns_status"] < 0):
			if len(cached)>0 and cached["collect_type"] in ["smart","extended"]:
				usecache = True
				record["opendns_api_collect_time"]        = cached["collect_time"]
				record["opendns_api_collect_type"]        = cached["collect_type"]
				record["opendns_dga_score"]               = cached["dga_score"]
				record["opendns_perplexity"]              = cached["perplexity"]
				record["opendns_entropy"]                 = cached["entropy"]
				record["opendns_securerank2"]             = cached["securerank2"]
				record["opendns_pagerank"]                = cached["pagerank"]
				record["opendns_asn_score"]               = cached["asn_score"]
				record["opendns_prefix_score"]            = cached["prefix_score"]
				record["opendns_rip_score"]               = cached["rip_score"]
				record["opendns_fastflux"]                = cached["fastflux"]
				record["opendns_popularity"]              = cached["popularity"]
				record["opendns_geodiversity"]            = cached["geodiversity"]
				record["opendns_geodiversity_normalized"] = cached["geodiversity_normalized"]
				record["opendns_tld_geodiversity"]        = cached["tld_geodiversity"]
				record["opendns_geoscore"]                = cached["geoscore"]
				record["opendns_ks_test"]                 = cached["ks_test"]
				record["opendns_attack"]                  = cached["attack"]
				record["opendns_threat_type"]             = cached["threat_type"]
				record["opendns_threat_found"]            = cached["threat_found"]
			else:
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_rquest = requests.get(ini["opendns"]["address"]+"/security/name/"+record[key]+".json",headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_rquest.status_code == 200:
					newdata = True
					opendns_result = json.loads(opendns_rquest.text)
					record["opendns_api_collect_time"]            = collect_time
					record["opendns_api_collect_type"]            = method
					record["opendns_dga_score"]               = opendns_result["dga_score"]
					record["opendns_perplexity"]              = opendns_result["perplexity"]
					record["opendns_entropy"]                 = opendns_result["entropy"]
					record["opendns_securerank2"]             = opendns_result["securerank2"]
					record["opendns_pagerank"]                = opendns_result["pagerank"]
					record["opendns_asn_score"]               = opendns_result["asn_score"]
					record["opendns_prefix_score"]            = opendns_result["prefix_score"]
					record["opendns_rip_score"]               = opendns_result["rip_score"]
					record["opendns_fastflux"]                = opendns_result["fastflux"]
					record["opendns_popularity"]              = opendns_result["popularity"]
					record["opendns_geodiversity"]            = opendns_result["geodiversity"]
					record["opendns_geodiversity_normalized"] = opendns_result["geodiversity_normalized"]
					record["opendns_tld_geodiversity"]        = opendns_result["tld_geodiversity"]
					record["opendns_geoscore"]                = opendns_result["geoscore"]
					record["opendns_ks_test"]                 = opendns_result["ks_test"]
					record["opendns_attack"]                  = opendns_result["attack"]
					record["opendns_threat_type"]             = opendns_result["threat_type"]
					record["opendns_threat_found"]            = opendns_result["found"]

		# Co-occurrences for a Domain
		if method in ["extended"]:
			if len(cached)>0 and cached["collect_type"] in ["extended"]:
				usecache = True
				record["opendns_api_collect_time"] = cached["collect_time"]
				record["opendns_api_collect_type"] = cached["collect_type"]
				record["opendns_pfs2"]             = cached["pfs2"] if "pfs2" in cached else None
				record["opendns_pfs2_found"]       = cached["pfs2_found"] if "pfs2_found" in cached else None
			else:
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_rquest = requests.get(ini["opendns"]["address"]+"/recommendations/name/"+record[key]+".json",headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_rquest.status_code == 200:
					newdata = True
					opendns_result = json.loads(opendns_rquest.text)
					record["opendns_api_collect_time"] = collect_time
					record["opendns_api_collect_type"] = method
					record["opendns_pfs2"]             = opendns_result["pfs2"] if "pfs2" in opendns_result else None
					record["opendns_pfs2_found"]       = opendns_result["found"] if "found" in opendns_result else None

		# Related Domains for a Domain
		if method in ["extended"]:
			if len(cached)>0 and cached["collect_type"] in ["extended"]:
				usecache = True
				record["opendns_api_collect_time"] = cached["collect_time"]
				record["opendns_api_collect_type"] = cached["collect_type"]
				record["opendns_tb1"]              = cached["tb1"] if "tb1" in cached else None
				record["opendns_tb1_found"]        = cached["tb1_found"] if "tb1_found" in cached else None
			else:
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_rquest = requests.get(ini["opendns"]["address"]+"/links/name/"+record[key]+".json",headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_rquest.status_code == 200:
					newdata = True
					opendns_result = json.loads(opendns_rquest.text)
					record["opendns_api_collect_time"] = collect_time
					record["opendns_api_collect_type"] = method
					record["opendns_tb1"]              = opendns_result["tb1"] if "tb1" in opendns_result else None
					record["opendns_tb1_found"]        = opendns_result["found"] if "found" in opendns_result else None

		# Domain Tagging Dates for a Domain
		if method in ["extended"]:
			if len(cached)>0 and cached["collect_type"] in ["extended"]:
				usecache = True
				record["opendns_api_collect_time"] = cached["collect_time"]
				record["opendns_api_collect_type"] = cached["collect_type"]
				record["opendns_period"]           = cached["period"] if "period" in cached else None
				record["opendns_category"]         = cached["category"] if "category" in cached else None
				record["opendns_url"]              = cached["url"] if "url" in cached else None
			else:
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_rquest = requests.get(ini["opendns"]["address"]+"/domains/"+record[key]+"/latest_tags",headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_rquest.status_code == 200:
					newdata = True
					opendns_result = json.loads(opendns_rquest.text)
					record["opendns_api_collect_time"] = collect_time
					record["opendns_api_collect_type"] = method
					record["opendns_period"]           = opendns_result["period"] if "period" in opendns_result else None
					record["opendns_category"]         = opendns_result["category"] if "category" in opendns_result else None
					record["opendns_url"]              = opendns_result["url"] if "url" in opendns_result else None

		# WHOIS Information for a Domain
		if method in ["extended","whois"]:
			if len(cached)>0 and cached["collect_type"] in ["extended","whois"]:
				usecache = True
				record["opendns_api_collect_time"]   = cached["collect_time"]
				record["opendns_api_collect_type"]   = cached["collect_type"]
				record["opendns_whois_addresses"]    = cached["whois_addresses"] if "whois_addresses" in cached else None
				record["opendns_whois_created"]      = cached["whois_created"] if "whois_created" in cached else None
				record["opendns_whois_emails"]       = cached["whois_emails"] if "whois_emails" in cached else None
				record["opendns_whois_expires"]      = cached["whois_expires"] if "whois_expires" in cached else None
				record["opendns_whois_nameServers"]  = cached["whois_nameServers"] if "whois_nameServers" in cached else None
				record["opendns_whois_status"]       = cached["whois_status"] if "whois_status" in cached else None
				record["opendns_whois_timestamp"]    = cached["whois_timestamp"] if "whois_timestamp" in cached else None
				record["opendns_whois_updated"]      = cached["whois_updated"] if "whois_updated" in cached else None
				record["opendns_whois_whoisServers"] = cached["whois_whoisServers"] if "whois_whoisServers" in cached else None
			elif method == "whois":
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_rquest = requests.get(ini["opendns"]["address"]+"/whois/"+record[key],headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_rquest.status_code == 200:
					newdata = True
					opendns_result = json.loads(opendns_rquest.text)
					record["opendns_api_collect_time"]   = collect_time
					record["opendns_api_collect_type"]   = method
					record["opendns_whois_addresses"]    = opendns_result["addresses"] if "addresses" in opendns_result else None
					record["opendns_whois_created"]      = opendns_result["created"] if "created" in opendns_result else None
					record["opendns_whois_emails"]       = opendns_result["emails"] if "emails" in opendns_result else None
					record["opendns_whois_expires"]      = opendns_result["expires"] if "expires" in opendns_result else None
					record["opendns_whois_nameServers"]  = opendns_result["nameServers"] if "nameServers" in opendns_result else None
					record["opendns_whois_status"]       = opendns_result["status"] if "status" in opendns_result else None
					record["opendns_whois_timestamp"]    = opendns_result["timestamp"] if "timestamp" in opendns_result else None
					record["opendns_whois_updated"]      = opendns_result["updated"] if "updated" in opendns_result else None
					record["opendns_whois_whoisServers"] = opendns_result["whoisServers"] if "whoisServers" in opendns_result else None

	elif re.match(re.compile(ini["regex"]["ipv4n6"]),record[key]) and method in ["maldomains"]:
		method_domain = None
		method_ip = record[key]

		# Poll the OpenDNS cache KV store; last record is latest (2/2)
		kvdata = json.dumps({"ip":record[key]})
		verify = False if ini["splunk"]["verify"] == "0" else True
		kvapir = requests.get(ini["splunk"]["address"]+"storage/collections/data/opendns_cache?query="+kvdata,auth=(ini["splunk"]["username"],ini["splunk"]["password"]),verify=verify,headers={"Content-Type":"application/json"})
		if kvapir.status_code == 200 and kvapir.text != "[ ]":
			cached = json.loads(kvapir.text)
			cached = cached[(len(cached)-1)]
		else: cached = []

		# Latest Malicious Domains for an IP
		if method in ["maldomains"]:
			if len(cached)>0 and cached["collect_type"] in ["maldomains"]:
				usecache = True
				record["opendns_api_collect_time"] = cached["collect_time"]
				record["opendns_api_collect_type"] = cached["collect_type"]
				record["opendns_maldomains"]       = cached["maldomains"] if "maldomains" in cached else None
			elif method == "maldomains":
				verify = False if ini["opendns"]["verify"] == "0" else True
				opendns_rquest = requests.get(ini["opendns"]["address"]+"/ips/"+record[key]+"/latest_domains",headers={"Authorization":"Bearer "+ini["opendns"]["apiKey"]},verify=verify)
				if opendns_rquest.status_code == 200:
					newdata = True
					opendns_result = json.loads(opendns_rquest.text)
					record["opendns_api_collect_time"] = collect_time
					record["opendns_api_collect_type"] = method
					mvnew = []
					for mvfields in opendns_result: mvnew.append(mvfields["name"])
					record["opendns_maldomains"]       = mvnew

	# :: Store the OpenDNS API response in the cache KV Store
	if newdata == True:
		kvdata = json.dumps({
			"collect_time": time.time(),
			"collect_type": method,
			"domain": method_domain,
			"ip": method_ip,
			"status": record["opendns_status"] if "opendns_status" in record else None,
			"content_categories": record["opendns_content_categories"] if "opendns_content_categories" in record else None,
			"security_categories": record["opendns_security_categories"] if "opendns_security_categories" in record else None,
			"dga_score": record["opendns_dga_score"] if "opendns_dga_score" in record else None,
			"perplexity": record["opendns_perplexity"] if "opendns_perplexity" in record else None,
			"entropy": record["opendns_entropy"] if "opendns_entropy" in record else None,
			"securerank2": record["opendns_securerank2"] if "opendns_securerank2" in record else None,
			"pagerank": record["opendns_pagerank"] if "opendns_pagerank" in record else None,
			"asn_score": record["opendns_asn_score"] if "opendns_asn_score" in record else None,
			"prefix_score": record["opendns_prefix_score"] if "opendns_prefix_score" in record else None,
			"rip_score": record["opendns_rip_score"] if "opendns_rip_score" in record else None,
			"fastflux": record["opendns_fastflux"] if "opendns_fastflux" in record else None,
			"popularity": record["opendns_popularity"] if "opendns_popularity" in record else None,
			"geodiversity": record["opendns_geodiversity"] if "opendns_geodiversity" in record else None,
			"geodiversity_normalized": record["opendns_geodiversity_normalized"] if "opendns_geodiversity_normalized" in record else None,
			"tld_geodiversity": record["opendns_tld_geodiversity"] if "opendns_tld_geodiversity" in record else None,
			"geoscore": record["opendns_geoscore"] if "opendns_geoscore" in record else None,
			"ks_test": record["opendns_ks_test"] if "opendns_ks_test" in record else None,
			"attack": record["opendns_attack"] if "opendns_attack" in record else None,
			"threat_type": record["opendns_threat_type"] if "opendns_threat_type" in record else None,
			"threat_found": record["opendns_threat_found"] if "opendns_threat_found" in record else None,
			"pfs2": record["opendns_pfs2"] if "opendns_pfs2" in record else None,
			"pfs2_found": record["opendns_pfs2_found"] if "opendns_pfs2_found" in record else None,
			"tb1": record["opendns_tb1"] if "opendns_tb1" in record else None,
			"tb1_found": record["opendns_tb1_found"] if "opendns_tb1_found" in record else None,
			"period": record["opendns_period"] if "period" in record else None,
			"category": record["opendns_category"] if "category" in record else None,
			"url": record["opendns_url"] if "url" in record else None,
			"whois_addresses": record["opendns_whois_addresses"] if "opendns_whois_addresses" in record else None,
			"whois_created": record["opendns_whois_created"] if "opendns_whois_created" in record else None,
			"whois_emails": record["opendns_whois_emails"] if "opendns_whois_emails" in record else None,
			"whois_expires": record["opendns_whois_expires"] if "opendns_whois_expires" in record else None,
			"whois_nameServers": record["opendns_whois_nameServers"] if "opendns_whois_nameServers" in record else None,
			"whois_status": record["opendns_whois_status"] if "opendns_whois_status" in record else None,
			"whois_timestamp": record["opendns_whois_timestamp"] if "opendns_whois_timestamp" in record else None,
			"whois_updated": record["opendns_whois_updated"] if "opendns_whois_updated" in record else None,
			"whois_whoisServers": record["opendns_whois_whoisServers"] if "opendns_whois_whoisServers" in record else None,
			"maldomains": record["opendns_maldomains"] if "opendns_maldomains" in record else None
		})
		verify = False if ini["splunk"]["verify"] == "0" else True
		kvapir = requests.post(ini["splunk"]["address"]+"storage/collections/data/opendns_cache",data=kvdata,auth=(ini["splunk"]["username"],ini["splunk"]["password"]),verify=verify,headers={"Content-Type":"application/json"})
		record["opendns_api_collect_cached"] = "False"
	elif newdata == False and usecache == True: record["opendns_api_collect_cached"] = "True"

	return record
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
@Configuration()
class odlCommand(StreamingCommand):

	# :: Enumerate the values submitted by Splunk
	method = Option(require=True,validate=validators.Fieldname())
	field = Option(require=True,validate=validators.Fieldname())
	def stream(self,records):
		for record in records:
			for key,value in record.items():
				if key == self.field: record = odlLookup(key,record,self.method.lower(),self.service)
			yield record

if __name__ == "__main__":
	odlInitialization()
	dispatch(odlCommand,sys.argv,sys.stdin,sys.stdout,__name__)
# ----------------------------------------------------------------------

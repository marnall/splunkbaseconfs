#
# Splunk integration, api call script: nick 2017
#
import logging
import json
from lib.xmltodict import xmltodict
import hashlib
import hmac
from lib import requests
from parser import parser

requests.packages.urllib3.disable_warnings()


class api_request:
    """Make api request."""

    def __init__(self):
        """initialize a bunch of stuff."""
        self.log = logging.getLogger("securitylookup")
        self.parser = parser()

    def remove_empty_keys(self, parsed_result):
        """
        Remove null items from results.

        :param json_data
        :returns json_data without empty k,v pairs
        """
        for k in parsed_result.keys():
            if not parsed_result[k]:
                del parsed_result[k]

        return parsed_result

    def search_threatcrowd(self, searchtype, searchvalue):
        """Make api call to threatcrowd."""
        # craft URL parameters
        if searchtype == 'file_hash':
            param = 'resource'
            api = 'file'
        elif searchtype == 'domain':
            param = 'domain'
            api = 'domain'
        elif searchtype == 'ip':
            param = 'ip'
            api = 'ip'

        # make request
        params = {param: searchvalue}
        response = requests.get('https://www.threatcrowd.org/searchApi/v2/'+api+'/report/', params=params, verify=False)
        # check website response
        if response.status_code == 200:
            json_data = response.json()
            # call threatcrowd parser
            parsed_result = self.parser.threatcrowd_parser(searchtype, searchvalue, json_data)
            # remove any empty keys value pairs
            parsed_result = self.remove_empty_keys(parsed_result)
            # return result
            return parsed_result
        # if bad response code from website
        else:
            self.log.error("ThreatCrowd Response: {}".format(response.content))
            err_dict = {}
            err_dict["SearchType"] = searchtype
            err_dict["SearchValue"] = searchvalue
            err_dict["Response"] = "Bad Response from threatcrowd api, check log"
            return err_dict

    def search_virustotal(self, searchtype, searchvalue, vt_key):
        """Make api call to virustotal."""
        # Craft URL Parameters
        if searchtype == 'file_hash':
            param = 'resource'
            api = 'file'
        elif searchtype == 'domain':
            param = 'domain'
            api = 'domain'
        elif searchtype == 'ip':
            param = 'ip'
            api = 'ip-address'

        # make request
        params = {'apikey': vt_key, param: searchvalue}
        response = requests.get('https://www.virustotal.com/vtapi/v2/'+api+'/report', params=params, verify=False)
        # check website response
        if response.status_code == 200:
            json_data = response.json()
            # call virustotal parser
            parsed_result = self.parser.virustotal_parser(searchtype, searchvalue, json_data)
            # remove any empty keys value pairs
            parsed_result = self.remove_empty_keys(parsed_result)
            # return result
            return parsed_result
        # if bad response code from website
        else:
            self.log.error("VirusTotal Response: {}".format(response.content))
            err_dict = {}
            err_dict["SearchType"] = searchtype
            err_dict["SearchValue"] = searchvalue
            err_dict["Response"] = "Bad Response from Virustotal api, check log"
            return err_dict

    # Totalhash function
    def get_signature(self, th_key, queryvalue):
        """build totalhash signature."""
        sign = hmac.new(th_key, msg=queryvalue, digestmod=hashlib.sha256).hexdigest()
        return sign

    # Totalhash function
    def build_totalhash_url(self, querytype, queryvalue, th_user, sign):
        """build totalhash url."""
        url = "https://api.totalhash.com/{}/{}&id={}&sign={}".format(querytype, queryvalue, th_user, sign)
        return url

    def search_totalhash(self, searchtype, searchvalue, th_key, th_user):
        """Make api call to totalhash."""
        # Craft URL Parameters
        if searchtype == 'file_hash':
            # Check to make sure its sha1, otherwise stop
            if len(searchvalue) != 40:
                self.log.info("The hash submitted was not sha1, only submit sha1 for TotalHash analysis")
                err_dict = {}
                err_dict["SearchType"] = searchtype
                err_dict["SearchValue"] = searchvalue
                err_dict['Response'] = "The hash submitted was not sha1, only submit sha1 for TotalHash analysis"
                return err_dict
            else:
                # do analysis for file_hash
                querytype = 'analysis'
                queryvalue = searchvalue
        elif searchtype == 'domain':
            # do search for domain
            querytype = 'search'
            queryvalue = 'dnsrr:{}'.format(searchvalue)
        elif searchtype == 'ip':
            # do search for ip
            querytype = 'search'
            queryvalue = 'ip:{}'.format(searchvalue)

        # make api request
        sign = self.get_signature(th_key, queryvalue)
        url = self.build_totalhash_url(querytype, queryvalue, th_user, sign)
        response = requests.get(url, verify=False)

        # check response from website
        if response.status_code == 404:
            self.log.info("The query was not found in TotalHash...")
            null_result = {}
            null_result["SearchType"] = searchtype
            null_result["SearchValue"] = searchvalue
            null_result['Response'] = "The query was not found in TotalHash."
            return null_result
        elif response.status_code == 200:
            self.log.debug("Found in TotalHash...")
            json_data = json.loads(json.dumps(xmltodict.parse(response.content)))

            # call totalhash parser
            parsed_result = self.parser.totalhash_parser(searchtype, searchvalue, json_data)
            # remove any empty keys value pairs
            parsed_result = self.remove_empty_keys(parsed_result)
            # return result
            return parsed_result
        else:
            self.log.error("TotalHash Response: {}".format(response.content))
            null_result = {}
            null_result["SearchType"] = searchtype
            null_result["SearchValue"] = searchvalue
            null_result['Response'] = "Error from totalhash api, check log"
            return null_result

    def search_passivetotal(self, searchtype, searchvalue, pt_key, pt_user):
        """Make api call to passivetotal."""
        # craft parameters
        auth = (pt_user, pt_key)
        data = {'query': searchvalue}

        # make api request
        response = requests.get("https://api.passivetotal.org/v2/dns/passive", auth=auth, json=data, verify=False)

        # check api response
        if response.status_code == 200:
            json_data = response.json()
            # call passivetotal parser
            parsed_result = self.parser.passivetotal_parser(searchtype, searchvalue, json_data)
            # remove any empty keys value pairs
            parsed_result = self.remove_empty_keys(parsed_result)
            # return result
            return parsed_result
        # if bad response code from website
        else:
            self.log.error("PassiveTotal Response: {}".format(response.content))
            err_dict = {}
            err_dict["SearchType"] = searchtype
            err_dict["SearchValue"] = searchvalue
            err_dict["Response"] = "Bad Response from passivetotal api, check log"
            return err_dict

    def search_censys(self, searchtype, searchvalue, cs_uuid, cs_secret):
        """Make api call to censys.io."""
        # craft parameters
        if searchtype == 'domain':
            index = 'websites'
        elif searchtype == 'ip':
            index = 'ipv4'
        auth = (cs_uuid, cs_secret)

        # make api request
        response = requests.get("https://www.censys.io/api/v1/view/{}/{}".format(index, searchvalue), auth=auth, verify=False)

        # check api response
        if response.status_code == 200:
            self.log.debug("Found in Censys.io Database...")
            json_data = response.json()
            # call censys parser
            parsed_result = self.parser.censys_parser(searchtype, searchvalue, json_data)
            # remove any empty keys value pairs
            parsed_result = self.remove_empty_keys(parsed_result)
            # return result
            return parsed_result
        # censys responds w/ json if they dont have it or a problem
        else:
            json_data = response.json()
            null_result = {}
            null_result["SearchType"] = searchtype
            null_result["SearchValue"] = searchvalue
            null_result["Response"] = json_data["error"]
            return null_result


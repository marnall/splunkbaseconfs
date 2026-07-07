#
# Splunk integration, initial script: nick 2017
#
# Sending Data to Splunk needs to be in this format
# [{key1: value, key2: [value, value, etc]}]
#
import os
import logging
import splunk.Intersplunk
import ConfigParser
from core import Processor
from external_request import api_request


class runner:
    """Build requests to various APIs."""

    def __init__(self):
        """initialize a bunch of stuff."""
        self.procs = Processor()
        self.api_call = api_request()
        self.log = logging.getLogger("securitylookup")

    def get_apikey(self, stanza, key):
        """Get api key from local/api_keys.conf."""
        configLocalFileName = "{}/api_keys.conf".format(self.procs.local_dir)
        # check if local/api_keys.conf exists
        if not os.path.exists(configLocalFileName):
            self.log.error("No local/api_keys.conf file found.")
            splunk.Intersplunk.generateErrorResults("No local/api_keys.conf file found")
            exit(0)
        # try to get api key or object
        else:
            try:
                key_parser = ConfigParser.SafeConfigParser()
                key_parser.read(configLocalFileName)
                key_object = key_parser.get(stanza, key)
            # the stanza for the api key is missing, needs added
            except ConfigParser.NoSectionError:
                self.log.error("No {} stanza in api_keys.conf, add stanza and {}".format(stanza, key))
                splunk.Intersplunk.generateErrorResults("No {} stanza in api_keys.conf, add stanza and {}".format(stanza, key))
                exit(0)
            # the stanza is present, but the key in stanza is missing
            except ConfigParser.NoOptionError:
                self.log.error("No {} in {} stanza in api_keys.conf, add key to stanza".format(key, stanza))
                splunk.Intersplunk.generateErrorResults("No {} in {} stanza in api_keys.conf, add key to stanza".format(key, stanza))
                exit(0)
            if key_object:
                return key_object
            # the stanza and key are present, but key value missing
            else:
                self.log.error("No {} value found, add key value for {}".format(key, stanza))
                splunk.Intersplunk.generateErrorResults("No {} value found, add value to {}".format(key, stanza))
                exit(0)

    def main(self):
        """
        The main securitylookup class.

        :returns returns result in a list to splunk
        """
        # get args passed from splunk
        try:
            keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
            self.log.debug("keywords: {}".format(keywords))
            self.log.debug("argvals: {}".format(argvals))
            file_hash = argvals.get("file_hash", None)
            domain = argvals.get("domain", None)
            ip = argvals.get("ip", None)
            engine = argvals.get("engine", None)

            # Check correct arguments were passed
            if file_hash:
                searchtype = "file_hash"
                searchvalue = file_hash
            elif domain:
                searchtype = "domain"
                searchvalue = domain
            elif ip:
                searchtype = "ip"
                searchvalue = ip
            else:
                self.log.error("Did not pass correct searchtype. Try [file_hash=|domain=|ip=]")
                splunk.Intersplunk.generateErrorResults("Did not pass correct searchtype. Try [file_hash=|domain=|ip=]")
                exit(0)

            # make api call to specified provider
            results_list = []
            if engine == "threatcrowd":
                results_list.append(self.api_call.search_threatcrowd(searchtype, searchvalue))
            elif engine == "virustotal":
                vt_key = self.get_apikey("virustotal", "vt_key")
                results_list.append(self.api_call.search_virustotal(searchtype, searchvalue, vt_key))
            elif engine == "totalhash":
                th_key = self.get_apikey("totalhash", "th_key")
                th_user = self.get_apikey("totalhash", "th_user")
                results_list.append(self.api_call.search_totalhash(searchtype, searchvalue, th_key, th_user))
            elif engine == "passivetotal":
                pt_key = self.get_apikey("passivetotal", "pt_key")
                pt_user = self.get_apikey("passivetotal", "pt_user")
                results_list.append(self.api_call.search_passivetotal(searchtype, searchvalue, pt_key, pt_user))
            elif engine == "censys":
                cs_uuid = self.get_apikey("censys", "cs_uuid")
                cs_secret = self.get_apikey("censys", "cs_secret")
                results_list.append(self.api_call.search_censys(searchtype, searchvalue, cs_uuid, cs_secret))
            else:
                self.log.error("Did not pass correct SearchEngine. Try engine=[virustotal|threatcrowd|totalhash|passivetotal|censys]")
                splunk.Intersplunk.generateErrorResults("Did not pass correct SearchEngine. Try engine=[virustotal|threatcrowd|totalhash|passivetotal|censys]")
                exit(0)

        except Exception as e:
            import traceback
            stack = traceback.format_exc()
            self.log.error("{}. \nTraceback: {}".format(e, stack))
            splunk.Intersplunk.generateErrorResults(e)

        # return results to splunk
        try:
            # return results
            self.log.info("{}".format(results_list))
            splunk.Intersplunk.outputResults(results_list)
            self.log.info("{} Lookup for {} Done.".format(engine, searchvalue))
        except Exception, e:
            import traceback
            stack = traceback.format_exc()
            self.log.error("{}. \nTraceback: {}".format(e, stack))
            splunk.Intersplunk.generateErrorResults(e)

if __name__ == '__main__':
    runner().main()


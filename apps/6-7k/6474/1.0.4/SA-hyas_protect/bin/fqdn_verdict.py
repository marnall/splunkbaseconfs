# This is a generating command for making a post request to particular endpoint.
from __future__ import absolute_import, division, print_function, unicode_literals
import sys
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from validation import validating_ioc
from constants import IOC_PROTECT
from data_parsing import Data_Parsing
from constants import BASE_URL
from hyas_api_call import Hyas_api_call
from json import loads

# Generating command is used to make post request and parse the response on splunk dashboard(hyas_search).
@Configuration()
class ip(GeneratingCommand):
    ioc_names = IOC_PROTECT
    # ioc_name is the parameter chosen by user through the application's hyas_search dashboard dropdown.
    type = "fqdn"
    # ioc_value is the value entered by user through the application's hyas_search dashboard text field.
    value = Option(require=True)
    # generate function for making generating search command, the data has to be yielded as per the splunk's requirement.
    def generate(self):
        try:
            # endpoint  is the API ENDPOINT - URL
            validated_ioc_name = validating_ioc(self.type, self.value)
            if validated_ioc_name and validated_ioc_name in self.ioc_names.keys():
                ioc_name_validated = self.ioc_names[validated_ioc_name]
                endpoint = BASE_URL + ioc_name_validated + "/" + self.value
                # api_key which is stored is passwords configuration file is accessed and assgined to api_key.
                storage_passwords = self.service.storage_passwords
                api_key = Hyas_api_call.api_key_call(storage_passwords)
                # Post request is made using hyas_protect_endpoints function providing it the required parameters ( api_key, body and endpoint url).
                hyas_data = Hyas_api_call.hyas_protect_endpoints(endpoint, api_key)
                # checking the status of the response and raising error according to it if found any.
                if hyas_data == 401:
                    yield {"Error": "Unauthorized error, please "
                                    "provide valid api key."}
                elif hyas_data == 500:
                    yield {"Error": "Server Issue"}
                # Parsing and flattening of data is done here.
                elif hyas_data:
                    data_final = Data_Parsing.protect_parse_data(hyas_data)
                    yield data_final
                else:
                    yield {"Response": "No results found"}
        # Exception is raised when the try block doesnt executes due to interruptions, those interruptions will be raised by Exception class.
        except ConnectionError:
            yield {"Error": "Please check your internet connection!"}
        except KeyError:
            yield {"Error": "Please provide valid indicator type."}
        except Exception as err:
            yield {"Error": err}


dispatch(ip, sys.argv, sys.stdin, sys.stdout, __name__)

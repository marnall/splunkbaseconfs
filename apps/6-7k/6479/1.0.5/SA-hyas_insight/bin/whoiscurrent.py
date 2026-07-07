from __future__ import absolute_import, division, print_function, unicode_literals
import os,sys
from constants import WHOIS_CURRENT, WHOIS_CURRENT_NAMES, WHOIS_CURRENT_BASE_URL
from validation import Validation
from data_parsing import Data_Parsing
from hyas_api_call import Hyas_api_call
import json
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

# FOR EXPLANATION OF CODE PLEASE REFER TO COMMENTS IN PASSIVE.PY AS ALL THE FILES WITH GENERATING COMMAND HAVE SIMILAR CODE.
@Configuration()
class whoiscurrent(GeneratingCommand):
    
    ioc_names = WHOIS_CURRENT_NAMES
    type = Option(require=True)        
    #ioc_value is the value entered by user through the application's hyas_search dashboard text field.
    value = Option(require=True)
            
    def generate(self):
        try:
            endpoint = WHOIS_CURRENT_BASE_URL + WHOIS_CURRENT
            validated_ioc_name = Validation.validating_ioc(self.type, self.value)
            if validated_ioc_name is not None:
                if validated_ioc_name in self.ioc_names.keys():
                    ioc_name_validated = self.ioc_names[validated_ioc_name]
                    api_key = ""
                    storage_passwords = self.service.storage_passwords
                    for credential in storage_passwords:
                        realm = credential.content.get('realm')
                        if realm == "hyas_realm":
                            usercreds = {'password': credential.content.get('clear_password')}
                            api_key = usercreds['password']
                    payload = json.dumps({
                            "applied_filters": {
                                ioc_name_validated: self.value,
                                "current":True
                            }
                            })
                    hyas_data = Hyas_api_call.hyas_insight_endpoints(endpoint, api_key, payload)
                    filtered_data = hyas_data['items']
                    if hyas_data == 401:
                        yield {"Error": "Please provide valid API Key"}
                    elif hyas_data == 500:
                        yield {"Error": "Unable to fetch data!"}
                    elif hyas_data:
                        for item in filtered_data:
                            final_data = Data_Parsing.flatten_data(item)
                            data_final = Data_Parsing.whoiscurrent_parse_data(final_data)
                            yield data_final
                    else:
                        yield {"Response":"No results found"}
                else:
                    pass
            else:
                pass

        except IndexError:
            pass
        except KeyError :
            pass
        except Exception as err:
            yield {"Error":err}


dispatch(whoiscurrent, sys.argv, sys.stdin, sys.stdout, __name__)
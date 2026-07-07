from __future__ import absolute_import, division, print_function, unicode_literals
import sys
from constants import BASE_URL, SSL, SSL_IOC
from hyas_api_call import Hyas_api_call
from data_parsing import Data_Parsing
from validation import Validation
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

# FOR EXPLANATION OF CODE PLEASE REFER TO COMMENTS IN PASSIVE.PY AS ALL THE FILES WITH GENERATING COMMAND HAVE SIMILAR CODE.
@Configuration()
class hyas_ssl(GeneratingCommand):
    
    ioc_names = SSL_IOC
    #ioc_name is the parameter chosen by user through the application's hyas_search dashboard dropdown.
    type = Option(require=True)        
    #ioc_value is the value entered by user through the application's hyas_search dashboard text field.
    value = Option(require=True)
            
    def generate(self):
        try:
            endpoint = BASE_URL + SSL
            validated_ioc_name = Validation.validating_ioc(self.type, self.value)
            if validated_ioc_name is not None :
                if validated_ioc_name in self.ioc_names.keys():
                    ioc_name_validated = self.ioc_names[validated_ioc_name]  
                    api_key = ""
                    storage_passwords = self.service.storage_passwords
                    for credential in storage_passwords:
                        realm = credential.content.get('realm')
                        if realm == "hyas_realm":
                            usercreds = {'password': credential.content.get('clear_password')}
                            api_key = usercreds['password']
                    data = Hyas_api_call.hyas_insight_endpoints_body(ioc_name_validated, self.value)
                    hyas_data = Hyas_api_call.hyas_insight_endpoints(endpoint,api_key, data)
                    if hyas_data == 401:
                        pass
                        # yield {"Error": "Please provide valid API Key"}
                    elif hyas_data == 500:
                        yield {"Error": "Server Issue"}
                    else: 
                        filtered_data = hyas_data['ssl_certs']
                        if len(filtered_data) > 0:
                            for item in filtered_data:
                                final_data = Data_Parsing.flatten_data(item)
                                data_final = Data_Parsing.ssl_parse_data(final_data)
                                yield data_final
                        else:
                            yield {"Response": "No results found"}
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

dispatch(hyas_ssl, sys.argv, sys.stdin, sys.stdout, __name__)
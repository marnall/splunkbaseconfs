# This is a generating command for making a post request to particular endpoint
from __future__ import absolute_import, division, print_function, unicode_literals
import sys
from constants import PASSIVE, BASE_URL, PASSIVE_IOC
from data_parsing import Data_Parsing
from validation import Validation
from hyas_api_call import Hyas_api_call
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

#Generating command is used to make post request and parse the response on splunk dashboard(hyas_search).
@Configuration()
class passive(GeneratingCommand):
    
    # ioc_names relates to specific parameters that this endpoint should serve.
    ioc_names = PASSIVE_IOC
    #ioc_name is the parameter chosen by user through the application's hyas_search dashboard dropdown.
    type = Option(require=True)        
    #ioc_value is the value entered by user through the application's hyas_search dashboard text field.
    value = Option(require=True)
    
        
    # generate function for making generating search command, the data has to be yielded as per the splunk's requirement.
    def generate(self):
        try:
            # endpoint  is the API ENDPOINT - URL
            endpoint = BASE_URL + PASSIVE
            # Validation of user inputs is done usning validating_ioc function.
            validated_ioc_name = Validation.validating_ioc(self.type, self.value)
            #
            if validated_ioc_name is not None:
                if validated_ioc_name in self.ioc_names.keys():
                    ioc_name_validated = self.ioc_names[validated_ioc_name] 
                    #api_key which is stored is passwords configuration file is accessed and assgined to api_key.     
                    api_key = ""
                    storage_passwords = self.service.storage_passwords
                    for credential in storage_passwords:
                        realm = credential.content.get('realm')
                        if realm == "hyas_realm":
                            usercreds = {'password': credential.content.get('clear_password')}
                            api_key = usercreds['password']
                    # body of the post request is formed by providing parameter name and paramerter value to hyas_insight_endpoints_body.
                    data = Hyas_api_call.hyas_insight_endpoints_body(ioc_name_validated, self.value)
                    # Post request is made using hyas_insight_endpoints function providing it the required parameters ( api_key, body and endpoint url).
                    hyas_data = Hyas_api_call.hyas_insight_endpoints(endpoint, api_key, data)                    

                    # checking the status of the response and raising error according to it if found any.
                    if hyas_data == 401:
                        pass
                        # yield {"Error": "Please provide valid API Key"}
                    elif hyas_data == 500:
                        yield {"Error": "Unable to fetch data!"}
                    elif hyas_data:
                        # Parsing and flattening of data is done here.
                        for item in hyas_data:
                            final_data = Data_Parsing.flatten_data(item)
                            data_final = Data_Parsing.passive_parse_data(final_data)  
                            yield data_final
                    else:
                        yield {"Response":"No results found"}         
                else:
                    pass
            else:
                pass
        # Exception is raised when the try block doesnt executes due to interruptions, those interruptions will be raised by Exception class.
        except IndexError:
            pass
        except KeyError :
            pass
        except Exception as err:
            yield {"Error":err}

dispatch(passive, sys.argv, sys.stdin, sys.stdout, __name__)
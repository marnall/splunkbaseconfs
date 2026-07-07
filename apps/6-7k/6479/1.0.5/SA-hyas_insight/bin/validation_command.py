from __future__ import absolute_import, division, print_function, unicode_literals
import sys
from validation import Validation
from constants import DYNAMIC, BASE_URL, DYNAMIC_IOC
from hyas_api_call import Hyas_api_call
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

# FOR EXPLANATION OF CODE PLEASE REFER TO COMMENTS IN PASSIVE.PY AS ALL THE FILES WITH GENERATING COMMAND HAVE SIMILAR CODE.

@Configuration()
class validation_results(GeneratingCommand):
    
    ioc_names = DYNAMIC_IOC
    #ioc_name is the parameter chosen by user through the application's hyas_search dashboard dropdown.
    type = Option(require=True)        
    #ioc_value is the value entered by user through the application's hyas_search dashboard text field.
    value = Option(require=True)
           
    def generate(self):
        try:
            endpoint = BASE_URL + DYNAMIC
            if  self.type is not "" and self.value is not "" :
                validated_ioc_name = Validation.validating_ioc(self.type, self.value)
                if validated_ioc_name is not None:
                    api_key = ""
                    storage_passwords = self.service.storage_passwords
                    for credential in storage_passwords:
                        realm = credential.content.get('realm')
                        if realm == "hyas_realm":
                            usercreds = {'password': credential.content.get('clear_password')}
                            api_key = usercreds['password']
                    data = Hyas_api_call.hyas_insight_endpoints_body(self.type, self.value)
                    hyas_data = Hyas_api_call.hyas_insight_endpoints(endpoint, api_key, data)
                    if hyas_data == 401:
                        yield {"Error": "HYAS API key is not valid, Please "
                                        "provide valid API Key"}

                    else:
                        pass
                else:
                    yield {"Error": "Please provide valid indicator value."}
            elif self.type and self.value is "":
                yield {"Error": "Please provide valid value."}

        except Exception as err:
            yield {"Error":err}

dispatch(validation_results, sys.argv, sys.stdin, sys.stdout, __name__)
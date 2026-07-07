from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
from validation import validating_ioc
from constants import BASE_URL
from hyas_api_call import Hyas_api_call
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# FOR EXPLANATION OF CODE PLEASE REFER TO COMMENTS IN PASSIVE.PY AS ALL THE FILES WITH GENERATING COMMAND HAVE SIMILAR CODE.


@Configuration()
class validation_results(GeneratingCommand):

    # ioc_name is the parameter chosen by user through the application's hyas_search dashboard dropdown.
    type = Option(require=True)
    # ioc_value is the value entered by user through the application's hyas_search dashboard text field.
    value = Option(require=True)

    def generate(self):
        try:
            endpoint = BASE_URL + self.type + "/" + self.value
            if self.type and self.value:
                validated_ioc_name = validating_ioc(self.type, self.value)
                if validated_ioc_name:
                    api_key = ""
                    storage_passwords = self.service.storage_passwords
                    api_key = Hyas_api_call.api_key_call(storage_passwords)
                    hyas_data = Hyas_api_call.hyas_protect_endpoints(endpoint, api_key)
                    if hyas_data == 401:
                        yield {"Error": "HYAS API key is not valid, Please "
                                        "provide valid API Key"}
                    else:
                        pass
                else:
                    yield {"Error": "Please provide valid indicator value."}
            elif self.type and self.value is "":
                yield {"Error": "Please select indicator type and provide valid value."}

        except Exception as err:
            yield {"Error": err}


dispatch(validation_results, sys.argv, sys.stdin, sys.stdout, __name__)

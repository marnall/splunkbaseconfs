from __future__ import absolute_import, division, print_function, \
    unicode_literals
import sys
from constants import BASE_URL, SAMPLE_INFORMATION, SAMPLE_INFORMATION_IOC
from validation import Validation
from hyas_api_call import Hyas_api_call
from splunklib.searchcommands import dispatch, GeneratingCommand, \
    Configuration, Option


# FOR EXPLANATION OF CODE PLEASE REFER TO COMMENTS IN PASSIVE.PY AS ALL THE
# FILES WITH GENERATING COMMAND HAVE SIMILAR CODE.

@Configuration()
class sample_information(GeneratingCommand):
    ioc_names = SAMPLE_INFORMATION_IOC
    # ioc_name is the parameter chosen by user through the application's
    # hyas_search dashboard dropdown.
    type = Option(require=True)
    # ioc_value is the value entered by user through the application's
    # hyas_search dashboard text field.
    value = Option(require=True)

    def generate(self):
        try:
            endpoint = BASE_URL + SAMPLE_INFORMATION
            validated_ioc_name = Validation.validating_ioc(self.type,
                                                           self.value)
            if validated_ioc_name is not None:
                if validated_ioc_name in self.ioc_names.keys():
                    ioc_name_validated = self.ioc_names[validated_ioc_name]

                    api_key = ""
                    storage_passwords = self.service.storage_passwords
                    for credential in storage_passwords:
                        realm = credential.content.get('realm')
                        if realm == "hyas_realm":
                            usercreds = {'password': credential.content.get(
                                'clear_password')}
                            api_key = usercreds['password']
                    data = Hyas_api_call.hyas_insight_endpoints_body(
                        ioc_name_validated, self.value)
                    hyas_data = Hyas_api_call.hyas_insight_endpoints(endpoint,
                                                                     api_key,
                                                                     data)

                    if hyas_data == 401:
                        pass
                        # yield {"Error": "Please provide valid API Key"}
                    elif hyas_data == 404:
                        yield {"": "No result found"}
                    elif hyas_data == 500:
                        yield {"Error": "Unable to fetch data!"}
                    elif hyas_data:
                        hyas_data_list = hyas_data.get('scan_results', [])
                        if hyas_data_list and len(hyas_data_list) > 0:
                            for item in hyas_data_list:
                                data_final = {
                                        "AV Scan Score": hyas_data.get(
                                            "avscan_score"),
                                        "MD5": hyas_data.get("md5"),
                                        'Scan Result AV Name': item.get(
                                            "av_name"),
                                        'Scan Result Def Time': item.get(
                                            "def_time"),
                                        'Scan Result Threat Found': item.get(
                                            'threat_found'),
                                        'Scan Time': hyas_data.get("scan_time"),
                                        'SHA1': hyas_data.get('sha1'),
                                        'SHA256': hyas_data.get('sha256'),
                                        'SHA512': hyas_data.get('sha512')
                                    }
                                yield data_final
                        else:
                            yield {"Response": "No results found"}
                    else:
                        yield {"Response": "No results found"}
                else:
                    pass
            else:
                pass
        except IndexError:
            pass
        except KeyError:
            pass
        except Exception as err:
            yield {"Error": err}


dispatch(sample_information, sys.argv, sys.stdin, sys.stdout, __name__)

# encoding = utf-8
"""Specifies lists of config options for each tab in the config section. 

This module is produced by the Splunk Add-on Builder.  It is slightly 
modified by TruSTAR, and the modification is clearly marked below.  
This modification had to be made to accommodate SplunkCloud's requirement
that add-ons not allow any insecure HTTP communication.  

NOTE 1 TO TRUSTAR DEVELOPERS:  If you modify the add-on builder project 
file in the future (reporoot/add_on_builder/aob_project_file.tgz), you
will have to obtain the new copy of this module produced by the AOB,
paste it over top of this copy, and reimplement the edits in the new 
copy that have been implemented in this copy.  It would be kind to 
put this docstring in the new copy of the file also.

NOTE 2 TO TRUSTAR DEVELOPERS:  Make sure that this module overwrites 
the version of this module produced by the AOB when building the final 
bundle to be submitted to Splunkbase / SplunkCloud for certification. 

"""

import ta_trustar_es_declare

# THIS IMPORT STATEMENT IS ADDED BY TRUSTAR, AND NEEDS TO BE WRITTEN 
# INTO THIS FILE AGAIN IF THE AOB PROJECT FILE EVER CHANGES!
from trustar_splunk_es.validator.validator import StationUrlValidator
# ALSO NOTE THAT THIS IMPORT STATEMENT MUST COME AFTER 'ta_trustar_es_declare' 
# HAS BEEN IMPORTED BECASUE THAT IMPORT PUTS 'trustar_splunk_es' IN THE 
# SPLUNK PATH, MAKING IT IMPORTABLE BY ABSOLUTE IMPORT SYNTAX. 

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    
    # THIS WAS THE ORIGINAL VERSION OF THE STATION URL STANZA THAT 
    # SPLUNKCLOUD NEEDED US MODIFY.  THE ONLY MODIFICATION IS THAT THE 
    # VALIDATOR IS NOW THE "StationUrlValidator"  
    # field.RestField(
    #     'station_url',
    #     required=True,
    #     encrypted=False,
    #     default='https://api.trustar.co',
    #     validator=validator.String(
    #         max_len=8192, 
    #         min_len=0, 
    #     )
    # ),
    # THE UPDATED STANZA (below) NEEDS TO BE WRITTEN INTO THE NEXT VERSION OF 
    # THIS FILE IF THE AOB PROJECT FILE IS EVER CHANGED.  
    
    field.RestField(
        'station_url',
        required=True,
        encrypted=False,
        default='https://api.trustar.co',
        validator=StationUrlValidator(      # THIS LINE UPDATED BY TRUSTAR. 
            max_len=8192,
            min_len=0
        )
    ),
    field.RestField(
        'default_submit_enclave_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'default_enrich_enclave_ids',
        required=True,
        encrypted=False,
        default='ALL',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_trustar_es_settings',
    models=[
        model_proxy, 
        model_logging, 
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )

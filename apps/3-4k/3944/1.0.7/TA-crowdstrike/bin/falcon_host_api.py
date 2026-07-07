#! /usr/bin/env python

import os
from ta_crowdstrike_import_declare import ta_lib_name
from splunktaucclib.data_collection import ta_mod_input
from falcon_host_data_client import FalconHostDataClient
from falcon_host_data_config import FalconHostConfig
from falcon_host_checkpoint_manager import FalconHostCheckPointMgr

SCHEMA_FILE_NAME = 'falcon_host.schema.json'


def ta_run():
    segments = [os.path.dirname(os.path.abspath(__file__)), ta_lib_name, SCHEMA_FILE_NAME]
    schema_file_path = os.path.join(*segments)
    ta_mod_input.main(FalconHostDataClient, schema_file_path, "falcon_host_api", checkpoint_cls=FalconHostCheckPointMgr, configer_cls=FalconHostConfig)


if __name__ == '__main__':
    ta_run()

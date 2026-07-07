# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

import soar_config_rest_handler

class SoarConfigHandler(soar_config_rest_handler.SoarConfigRESTHandler):
    def __init__(self, command_line, command_arg):
        super(SoarConfigHandler, self).__init__(command_line, command_arg)

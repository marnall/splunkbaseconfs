# File: conftest.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
import sys


class BaseConnectorMock:
    pass


# The following module-related changes take care of
# the missing 'phantom'-related package/modules.
# Without having 'phantom' installed as python dependency,
# tests do not fail because of 'ModuleNotFoundError'.
# 'phantom' is used within 'vmray_connector'.
module = type(sys)("phantom.app")
module.APP_ERROR = "APP_ERROR"
module.APP_SUCCESS = "APP_SUCCESS"
sys.modules["phantom.app"] = module

module = type(sys)("phantom")
sys.modules["phantom"] = module

module = type(sys)("phantom.rules")
sys.modules["phantom.rules"] = module

module = type(sys)("phantom.action_result")
module.ActionResult = type(sys)("ActionResult")
sys.modules["phantom.action_result"] = module

module = type(sys)("phantom.base_connector")
module.BaseConnector = BaseConnectorMock
sys.modules["phantom.base_connector"] = module

module = type(sys)("phantom.vault")
module.Vault = type(sys)("Vault")
sys.modules["phantom.vault"] = module

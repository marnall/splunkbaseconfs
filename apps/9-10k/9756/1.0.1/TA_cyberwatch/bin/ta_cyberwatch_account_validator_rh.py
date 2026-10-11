#
# Copyright 2026 Process-IT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Custom REST handler for the Accounts tab.
"""

import import_declare_test  # noqa: F401  isort:skip -- must run first, it fixes sys.path

import logging

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from ta_cyberwatch import validation

logger = logging.getLogger(__name__)


def _check(payload):
    try:
        skipped = validation.validate_account(payload)
    except Exception as exc:  # noqa: BLE001 -- every failure becomes a form message
        message = validation.explain(exc)
        logger.warning("Account validation refused a save: %s", message)
        # 400: the submitted configuration is the problem, not the request.
        raise RestError(400, message) from exc
    if skipped:
        logger.info("Account validation skipped: %s", skipped)


class CustomAccountValidator(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        _check(self.payload)
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        _check(self.payload)
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)

"""Utilities related to account page."""

from os import path
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.endpoint import SingleModel
from splunk import rest

from riskiqsis_utils import APP_NAME, reload_batch_input, INPUT_NAME

ACCOUNT_STANZA_NAME = None

# Various Path Skeletons for Inputs
BATCH_STANZA_PATH = path.join("$SPLUNK_HOME", "var", "spool", "splunk", "{}*.gz")
BATCH_STANZA_PREFIX = "batch://{}"

DATATYPE_SOURCETYPE_MAPPING = {
    "newly_observed_domain": "riskiq:sis:domain",
    "newly_observed_host": "riskiq:sis:host",
    "malware_blacklist": "riskiq:sis:malware",
    "phishing_blacklist": "riskiq:sis:phish",
    "scam_blacklist": "riskiq:sis:scam",
    "content_blacklist": "riskiq:sis:content"
}

DATATYPE_INTERVAL_MAPPING = {
    "newly_observed_domain": 3600,
    "newly_observed_host": 86400,
    "malware_blacklist": 3600,
    "phishing_blacklist": 3600,
    "scam_blacklist": 3600,
    "content_blacklist": 3600
}


class AccountModel(SingleModel):
    """Account Model."""

    def validate(self, name, data, existing=None):
        """To get stanza name for future use as it can only be retrive from here."""
        global ACCOUNT_STANZA_NAME
        ACCOUNT_STANZA_NAME = name
        super(AccountModel, self).validate(name, data, existing)


class AccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        super(AccountHandler, self).handleCreate(confInfo)
        self.create_inputs()

    def create_inputs(self):
        """Create given types of inputs into inputs.conf file."""
        payload = self.payload
        data_types = self.payload.get('data_types')

        data_types_list = data_types.split("~")

        for data_type in data_types_list:

            data_type = data_type.strip()
            modular_input_name = INPUT_NAME
            sourcetype = DATATYPE_SOURCETYPE_MAPPING[data_type]
            file_name_format = "{}_{}".format(ACCOUNT_STANZA_NAME, data_type)
            self.create_batch_input(file_name_format, sourcetype)

            # Common key:value for all inputs
            input_stanza = {
                "name": "{}://{}".format(modular_input_name, file_name_format),
                "collect_data_for": 1,
                "data_type": data_type,
                "global_account": payload.get('name'),
                "interval": DATATYPE_INTERVAL_MAPPING[data_type],
                "disabled": 1
            }

            # Using Splunk internal API to create default input
            try:
                rest.simpleRequest(
                    "/servicesNS/nobody/{}/configs/conf-inputs".format(
                        APP_NAME),
                    self.getSessionKey(),
                    postargs=input_stanza,
                    method="POST",
                    raiseAllErrors=True,
                )

            except Exception as e:
                if "409" in str(e):
                    e = "Account is created but Inputs are not created for it because inputs are still present for same\
                         account name. Please close this dialog box and remove the previously created inputs and create\
                         new."
                raise Exception(e)

    def create_batch_input(self, file_name_format, sourcetype):
        """
        Create batch input stanza for the data type corresponding to the account configured.

        :param file_name_format: modular_input_name
        :sourcetype: sourcetype for the batch input stanza to be created.
        """
        batch_input_stanza = {
            "name": BATCH_STANZA_PREFIX.format(BATCH_STANZA_PATH.format(file_name_format)),
            "move_policy": "sinkhole",
            "crcSalt": "<SOURCE>",
            "disabled": 0,
            "sourcetype": sourcetype
        }

        # Using Splunk internal API to create default input
        res, _ = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-inputs".format(APP_NAME),
            self.getSessionKey(),
            postargs=batch_input_stanza,
            method="POST",
            rawResult=True,
            raiseAllErrors=True,
        )
        if res.status not in [201, 409]:
            raise Exception("Unable to create batch input for {}".format(file_name_format))

        reload_batch_input(self.getSessionKey())

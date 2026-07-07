from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.endpoint import SingleModel
from copy import deepcopy
from splunk import rest
from ta_egnyte_constants import APP_NAME
ACCOUNT_STANZA_NAME = None

class AccountModel(SingleModel):
    """Account Model."""

    def validate(self, name, data, existing=None):
        """To get stanza name for future use as it can only be retrive from here."""
        global ACCOUNT_STANZA_NAME, INDEX_NAME, ENDPOINT
        ACCOUNT_STANZA_NAME = name
        INDEX_NAME = data.get("index", "main")
        ENDPOINT = data.get("endpoint", "US")
        super(AccountModel, self).validate(name, data, existing)

class AccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        super(AccountHandler, self).handleCreate(confInfo)
        self.create_inputs()

    def create_inputs(self):
        """Create given types of inputs into inputs.conf file."""

        modular_input_name = "egnyte"
        input_type = "egnyte"
    
        input_stanza = {
                "name": "{}://{}_{}".format(modular_input_name, ACCOUNT_STANZA_NAME, input_type),
                "global_account": ACCOUNT_STANZA_NAME,
                "disabled": "true",
                "endpoint": ENDPOINT,
                "index": INDEX_NAME
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
                e = "Account is created but Inputs are not created for it because inputs are still present for same account\
                name. Please close this dialog box and remove the previously created inputs and create new."
            raise Exception(e)
        
        try:
            rest.simpleRequest(
                "/servicesNS/nobody/{}/data/inputs/{}/{}_{}/enable".format(
                    APP_NAME, modular_input_name, ACCOUNT_STANZA_NAME, input_type),
                self.getSessionKey(),
                method="POST",
                raiseAllErrors=True,
            )
        except Exception as e:
            raise Exception(e)
import sys
from resources.splunklib import client as client
from resources.splunklib.modularinput import *
import resources.investigatelib as investigatelib

# Script is a class in modularinput
class CredsInput(Script):
    MASK           = "Splunk's recommendation is to keep this hidden"
    API_KEY_KEY    = "cisco_investigate_api_key"
    PROXY_PASSWORD_KEY = "cisco_investigate_proxy_password"
    PROXY_USERNAME_KEY = "cisco_investigate_proxy_username"
    SCHEME_DESCRIPTION = "Save your Investigate API Key and proxy credentials here (only enter one set of credentials)."

    def get_scheme(self):
        try:
            scheme = Scheme("Cisco Investigate Credentials")
            scheme.description = (self.SCHEME_DESCRIPTION)
            scheme.use_external_validation = True
            scheme.use_single_instance = False

            apikey_arg = Argument('api_key')
            apikey_arg.data_type=Argument.data_type_string
            apikey_arg.description="Investigate API Key"
            apikey_arg.required_on_create=True
            apikey_arg.required_on_edit=True
            scheme.add_argument(apikey_arg)

            proxy_user_arg = Argument('proxy_username')
            proxy_user_arg.data_type=Argument.data_type_string
            proxy_user_arg.description="Proxy Username"
            proxy_user_arg.required_on_create=False
            proxy_user_arg.required_on_edit=False
            scheme.add_argument(proxy_user_arg)

            proxy_password_arg = Argument('proxy_password')
            proxy_password_arg.data_type=Argument.data_type_string
            proxy_password_arg.description="Proxy Password"
            proxy_password_arg.required_on_create=False
            proxy_password_arg.required_on_edit=False
            scheme.add_argument(proxy_password_arg)
            return scheme
        except Exception as e:
            raise Exception("Cisco Umbrella inputs: Problem getting scheme in opendns_investigate.py: {}".format(str(e)))

    ## Not usiing this right now ##
    def validate_input(self, definition):
        session_key = definition.metadata["session_key"]
        api_key    = definition.parameters["api_key"]
        proxy_username = definition.parameters["proxy_username"]
        proxy_password = definition.parameters["proxy_password"]
        
        try:
            # Do checks here.  For example, try to connect to whatever you need the credentials for using the credentials provided.
            # If everything passes, create a credential with the provided input.
            pass
        except Exception as e:
            raise Exception("Cisco Umbrella inputs: Something did not go right: %s" % str(e))

    def encrypt_cred(self, thing_to_encrypt, key_to_retrieve, service):        
        try:
            # If the credential already exists, delete it.
            for storage_password in service.storage_passwords:
                # Basically, we're going to save the api key as a password, 
                # with the username as - 'opendns_investigate_api_key', etc
                if storage_password.username == key_to_retrieve:
                    service.storage_passwords.delete(username=storage_password.username)
                    break
            # Create the credential.
            service.storage_passwords.create(thing_to_encrypt, key_to_retrieve)

        except Exception as e:
            raise Exception("Cisco Umbrella inputs: An error occurred updating credentials. "\
                             "Please ensure your user account has admin_all_objects and/or "\
                             "list_storage_passwords capabilities. Details: {}".format(str(e)))

    # mask_apikey makes sure the item you see in the UI is the MASK value above. 
    def mask_apikey(self, service, mask_args):
        try:
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))
            item.update(**mask_args).refresh()
            
        except Exception as e:
            raise Exception("Cisco Umbrella inputs: Error updating inputs.conf: %s" % str(e))

    ## Not using this right now ##
    def get_apikey(self, service):
        try:
            # Retrieve the api_key from the storage/passwords endpoint 
            for storage_password in service.storage_passwords:
                if storage_password.username == self.API_KEY_KEY:
                    return storage_password.content.clear_password
        except Exception as e:
            raise Exception("Cisco Umbrella inputs: Error occurred getting api key. Details: {}".format(str(e)))

    def stream_events(self, inputs, ew):
        self.input_name, self.input_items = inputs.inputs.popitem()
        session_key = self._input_definition.metadata["session_key"]
        api_key = self.input_items.get('api_key')
        proxy_username = self.input_items.get('proxy_username')
        proxy_password = self.input_items.get('proxy_password')
        # Using the investigatelib.setup.connect gets the apikey stored in our app's local directory 
        # (apps/opendns_investigate/local/passwords.conf). service = client.connect(**args) 
        # starts a service as a different user, and saves the apikey in apps/search/local/passwords.conf, which 
        # we won't access from the script in the add_on. It's best to keep everything in our app directory. 
        
        # Start a connection to Splunk and begin retrieving data
        service = None

        # get the user info and a service for the user
        try:
            service = investigatelib.setup.connect(session_key)
        except Exception as e:
            logger.exception("Error obtaining service object: {}".format(e))

        if service:
            try:
                # Save what we need to
                if api_key != self.MASK:
                    ew.log("INFO", "Cisco Umbrella inputs: Saving API Key")
                    self.encrypt_cred(api_key, self.API_KEY_KEY, service)
                if proxy_password is not None and proxy_password != self.MASK:
                    ew.log("INFO", "Cisco Umbrella inputs: Saving proxy password")
                    self.encrypt_cred(proxy_password, self.PROXY_PASSWORD_KEY, service)
                # We're saving the username in the password api because it will stay in our app
                # This will also run twice. 
                if proxy_username is not None and len(proxy_username) > 0:
                    ew.log("INFO", "Cisco Umbrella inputs: Saving proxy username")
                    self.encrypt_cred(proxy_username, self.PROXY_USERNAME_KEY, service)
                # finally mask if we need to. Calling mask_apikey will call a refresh() method, which
                # causes the entire stream_events function to run again. This check avoids an infinate loop.
                if api_key != self.MASK or proxy_password != self.MASK:
                    mask_args = {
                        'api_key': self.MASK,
                        'proxy_username': proxy_username,
                        'proxy_password': self.MASK
                    }
                    self.mask_apikey(service, mask_args)
            except Exception as e:
                ew.log("ERROR", "Cisco Umbrella inputs: Error: %s" % str(e))
            finally:
                self.mask_apikey(service, mask_args)
        
if __name__ == "__main__":
    sys.exit(CredsInput().run(sys.argv))
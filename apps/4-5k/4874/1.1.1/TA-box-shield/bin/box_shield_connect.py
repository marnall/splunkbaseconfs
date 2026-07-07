# Local library imports
from boxsdk import OAuth2
from boxsdk import Client
from boxsdk import BoxException, BoxNetworkException, BoxAPIException

from utility import create_session_from_proxy, save_tokens, set_globals


class BoxShieldConnect(object):

    def __init__(self, helper):
        """constructor for BoxShieldConnect class.
        This class contains all the boxsdk related operations.

        Attributes:
            helper (obj): Splunk object
            GLOBAL_ACCOUNT (obj): Configured Box Account
        """
        self.helper = helper
        self.GLOBAL_ACCOUNT = self.helper.get_arg("box_account")

    def get_oauth_obj(self, oauth_class=OAuth2):
        """To get the client object
        This function serves two purposes
            1. Authentication 
            2. Initialize the client

        Args:
            OAuth2 (obj): OAuth2 object

        Returns:
            oauth (obj): OAuth2 object

        """
        set_globals(self.helper, self.GLOBAL_ACCOUNT['name'])
        oauth = oauth_class(
            client_id=self.GLOBAL_ACCOUNT['client_id'],
            client_secret=self.GLOBAL_ACCOUNT['client_secret'],
            access_token=self.GLOBAL_ACCOUNT['access_token'],
            refresh_token=self.GLOBAL_ACCOUNT['refresh_token'],
            store_tokens=save_tokens,
            session=self.get_session_info(),
        )
        return oauth

    def get_session_info(self, config=None):
        """Get the session object with informations

        Args:
            config (obj) : oAuth2 object
        """
        proxy_args = self.helper.get_proxy()
        if proxy_args:
            session = create_session_from_proxy(proxy_args, self.helper, config=config, helper_log=True)
        else:
            session = None
        return session

    def get_client(self, oauth):
        """Get client object

        Args:
            oauth (obj) : oAuth2 object
        """
        try:
            proxy_args = self.helper.get_proxy()
            if proxy_args:
                self.helper.log_info("Collecting data with given proxy configurations")
            else:
                self.helper.log_info("Collecting data without proxy")
            client = Client(oauth, self.get_session_info(config=oauth))
            return client

        except BoxException as be:
            self.helper.log_error(
                "Error occurred while configuring client object : \n{}".format(be))
        except Exception as e:
            self.helper.log_error(
                "Error occurred while configuring client object : \n{}".format(e))

    def get_events(self, client, created_after, created_before, event_type, next_stream_position):
        """Make the API call through boxsdk
        At the time it will only return the 500 events

        Args:
            client (obj): Client object. In order to get call the API client object is needed
            created_after (str): To get the data after the specified time
            created_before (str): To get the data before the specified time
            event_type (str): It can be `SHIELD_ALERT` or `["METADATA_INSTACE_CREATE","METADATA_INSTACE_CREATE",
                              "METADATA_INSTACE_CREATE", "METADATA_INSTACE_CREATE"]
            next_stream_position (str): This field used to get data consistently.
                                        It will contains the position of last events call,
                                        we use this field in upcoming API call.

        Returns:
            events (obj): Box response event object

        """
        try:
            events = client.events().get_admin_events(limit='500', created_after=created_after,
                                                      created_before=created_before, event_types=event_type, stream_position=next_stream_position)
            return events
        except BoxNetworkException as ne:
            self.helper.log_error(
                "Error occurred due to the Network issue while retrieving admin events: \n{}".format(ne))
            raise Exception(str(ne))
        except BoxAPIException as ae:
            self.helper.log_error(
                "Error occurred during the API call for admin events : \n{}".format(ae))
            raise Exception(str(ae))
        except BoxException as be:
            self.helper.log_error(
                "Unknown Error occurred while retrieving admin events : \n{}".format(be))
            raise Exception(str(be))
        except Exception as e:
            self.helper.log_error(
                "Unknown Error occurred while retrieving admin events: \n{}".format(e))
            raise Exception(str(e))

"""This module contain class and method related to updating the finding state."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..')))

import import_declare_test  # noqa: E402
import json  # noqa: E402
import socket  # noqa: E402
import traceback  # noqa: E402
from datetime import datetime  # noqa: E402
from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402
import splunk.admin as admin  # noqa: E402
import splunk.clilib.cli_common  # noqa: E402
from solnlib import conf_manager # noqa : E402
import splunklib.client as client  # noqa: E402
import TA_GoogleSCC_apiclient as gsa  # noqa: E402
from TA_GoogleSCC_consts import constants  # noqa: E402
from TA_GoogleSCC_logger_manager import setup_logging  # noqa: E402


APP_NAME = import_declare_test.app_name

class SplunkSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()

class UpdateFindingState(PersistentServerConnectionApplication):
    """Update Finding State Handler."""

    def __init__(self, _command_line, _command_arg):
        """Initialize object with given parameters."""
        self.finding_name = None
        self.finding_state = None
        self.new_state_value = None
        self.payload = {}
        self.status = None
        self.session_key = None
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a synchronous from splunkd.
    def handle(self, in_string):
        """
        After user clicks on Mark to Active/Inactive button, Called for a simple synchronous request.

        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        req_data = json.loads(in_string)
        session = dict(req_data.get("session"))
        self.session_key = session.get("authtoken")
        form_data = dict(req_data.get("form"))
        self.finding_name = form_data.get("finding_name")
        self.finding_state = form_data.get("finding_state")
        self.new_state_value = "INACTIVE" if self.finding_state == "ACTIVE" else "ACTIVE"
        event_time = datetime.utcnow().strftime(constants.ISO_DATE_FORMAT)
        logger = setup_logging("ta_googlescc_update_findings_status")

        try:
            cfm = conf_manager.ConfManager(
                self.session_key,
                import_declare_test.ta_name,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                    import_declare_test.ta_name, import_declare_test.ta_accounts_conf
                ),
            ).get_conf(import_declare_test.ta_accounts_conf)  # noqa: E501
            account_conf_file = cfm.get_all(only_current_app=True)
        except Exception:
            logger.error("message=conf_file_error | Error occured while reading account configuration.\n"
                         "{}".format(traceback.format_exc()))

        finding = form_data.get("finding_name")
        finding_split = finding.split("/")
        org_id = finding_split[1]

        # Initializing error message and status code with default values.
        self.payload['error'] = "No valid account configuration found for the organization: {}".format(org_id)
        self.status = 500

        for each in account_conf_file:
            if account_conf_file[str(each)].get('organization_id') == str(org_id):
                account_info = {
                    "service_account_json": json.loads(account_conf_file[str(each)].get('service_account_json')),
                    "credential_configuration_file": account_conf_file[str(each)].get('credential_configuration_file'),
                    "organization_id": account_conf_file[str(each)].get('organization_id'),
                }
                try:
                    client = gsa.init_google_scc_client(
                        service_account_json=account_info['service_account_json'],
                        credential_configuration_file=account_info['credential_configuration_file'],
                        organization_id=account_info['organization_id'],
                        logger=logger,
                        timeout=constants.TIMEOUT_TIME,
                        session_key=self.session_key,
                    )
                    response = client.update_findings_state(
                        logger=logger,
                        name=self.finding_name,
                        body={
                            "state": self.new_state_value,
                            "startTime": event_time
                        }
                    )
                    if not response:
                        logger.error("message=finding_state_updation_failed | "
                                     "Updation of finding state failed for account={}".format(str(each)))
                        self.payload['error'] = "Error while updating finding state to {} for Finding ID - {}".format(
                            self.new_state_value, self.finding_name)
                        self.status = 500
                    else:
                        # Updating the finding state in the kvstore lookup
                        self.kvstore_insert(response, logger)
                        self.payload['success'] = "Updated finding state successfully to {} for Finding ID = {}".format(
                            self.new_state_value, self.finding_name)
                        self.payload['response'] = response
                        self.status = 200
                        return {'payload': self.payload,
                                'status': self.status
                                }

                except Exception as e:
                    logger.error("message=client_response_error |"
                                 " Error occured while getting response for SCC client.\n{}"
                                 .format(traceback.format_exc()))
                    logger.error("message=finding_state_updation_failed | "
                                 "Error occured while updating finding state of finding={} using {} account.\n"
                                 "Error: {}".format(self.finding_name, str(each), str(e)))
                    err = str(e).replace("[", "").replace("]", "")
                    self.payload["error"] = '"<br>'.join(err.split('|", '))
                    self.status = 500

        logger.error("message=finding_state_updation_error |"
                     " No valid account configuration found for the organization: {}".format(org_id))
        return {'payload': self.payload,
                'status': self.status
                }

    def resolve_host(self, hostname):
        """Resolve hostname to IPv4/IPv6 address."""
        try:
            # This returns a list of (family, type, proto, canonname, sockaddr) tuples
            infos = socket.getaddrinfo(hostname, None)

            # Filter for IPv4 and IPv6 addresses
            ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
            ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]

            # Prefer IPv4, but fallback to IPv6 if necessary
            if ipv4_addresses:
                address = ipv4_addresses[0][4][0]
            elif ipv6_addresses:
                address = ipv6_addresses[0][4][0]
            else:
                return None  # No suitable address found
            return address
        except socket.gaierror:
            return None

    def create_service(self, sessionkey=None):
        """Create Service to communicate with splunk."""
        mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
        hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
        mgmt_port = mgmt_uri.split(":")[-1]

        # Resolve hostname to IPv4 address
        ip_address = self.resolve_host(hostname)
        if not ip_address:
            raise Exception("Failed to resolve Splunk management URI to an IP address.")

        if not sessionkey:
            sessionkey = SplunkSessionKey().session_key

        service = client.connect(host=ip_address, port=mgmt_port, token=sessionkey, app="GoogleSCCAppforSplunk")
        return service

    def kvstore_insert(self, response, logger):
        """Method to update or insert data into kvstore lookup."""  # noqa: D401
        try:
            mgmt_port = splunk.clilib.cli_common.getMgmtUri().split(":")[-1]
            collection_name = constants.COLLECTION_NAME
            kvstore_data = {
                "_key": response['name'],
                "eventTime": response['eventTime'],
                "state": response['state']
            }
            service = self.create_service(self.session_key)
            if collection_name in service.kvstore:
                collection = service.kvstore[collection_name]
                try:
                    data = collection.data.query_by_id(kvstore_data['_key'])
                    data["eventTime"] = kvstore_data["eventTime"]
                    data["state"] = kvstore_data["state"]
                    collection.data.update(data['_key'], json.dumps(data))
                    logger.info("message=finding_state_updated |"
                                " Updated the finding state in kvstore lookup successfully.")
                except Exception:
                    collection.data.insert(json.dumps(kvstore_data))
                    logger.info("message=finding_state_updated |"
                                " Inserted the finding state in kvstore lookup successfully.")
            else:
                logger.error("message=kvstore_error | Collection {} does not exist."
                             " Please define one in collections.conf.".format(collection_name))
        except Exception:
            logger.error("message=kvstore_updation_error | Couldn't update the finding state in kvstore lookup"
                         " for finding {}.\n{}".format(response['name'], traceback.format_exc()))

    def handleStream(self, handle, in_string):
        """For future use."""
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """Virtual method which can be optionally overridden to receive a callback after the request completes."""
        pass

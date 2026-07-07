import sys
import os
sys.path.insert(0, os.path.join("$SPLUNK_HOME", "lib",
                                "python3", "site-packages", "splunk"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from constants import LaceworkAPIConfConstants
from helpers import getConfStanzaAccessor, updateStanza
import splunklib.client as client
import splunk.admin as admin

LW_API_STANZA = LaceworkAPIConfConstants.LW_API_STANZA
LW_API_FIELD_DOMAIN = LaceworkAPIConfConstants.LW_API_FIELD_DOMAIN
LW_API_FILENAME = LaceworkAPIConfConstants.LW_API_FILENAME


class APIDomainHandler(admin.MConfigHandler):
    """Handles endpoint at apiDomain/APIDomainHandler that manages lacework-api.conf [api] 'domain' field. 
    See documentation on restmap.conf and web.conf for more info.
    An example to use the endpoint:
    GET https://localhost:PORT/services/apiDomain/APIDomainHandler -> to return the current domain, OR;
    GET https://localhost:PORT/services/apiDomain/APIDomainHandler?domain=yourDomain -> to create/update the domain

    Args:
        admin.MConfigHandler (class): A base class for all EAI handlers to implement.

    Raises:
        admin.BadActionException: Raised when requested action is not supported.
    """
    handledActions = [admin.ACTION_LIST]

    def setup(self):
        """
        Must be implemented by the derived class.  Defines arguments and validation
        info.  Called before the handle*() functions.
        Should:
          - inspect self.requestedAction.
          - populate self.supportedArgs via addReqArg() and addOptArg().
          - set pipelineName and processorName if appropriate.
        """
        if self.requestedAction not in self.handledActions:
            raise admin.BadActionException(
                "This handler does not support this action (%d)." % self.requestedAction)
        if self.requestedAction == admin.ACTION_LIST:
            self.supportedArgs.addOptArg("domain")

    def createService(self):
        """Creates a service that connects to splunk and enable the use of their endpoints

        Returns:
            class: An initialized :class:`Service` connection.
        """
        session_key = self.getSessionKey()
        service = client.Service(
            owner="nobody", app="lacework", sharing="app", token=session_key)
        return service

    def handleCreate(self, confInfo):
        """Called when user invokes the "create" action."""
        self.actionNotImplemented()

    def handleEdit(self, confInfo):
        """Called when user invokes the "edit" action."""
        self.actionNotImplemented()

    def handleList(self, confInfo):
        """Called when user invokes the "list" action. This corresponds to a GET request on the endpoint.
        When resource is created/updated, restarts our scripted input to fetch a new api token."""
        # if there is a domain field supplied that's also not an empty value: create/update our domain
        if self.callerArgs.__contains__("domain"):
            domain = self.callerArgs["domain"]
            if domain[0]:
                full_domain = domain[0] + ".lacework.net"
                service = self.createService()
                configuration_accessor = service.confs

                # Update domain
                updateStanza(configuration_accessor, LW_API_FILENAME, LW_API_STANZA, LW_API_FIELD_DOMAIN, full_domain)

                # Toggle between disabled and enabled for the scripted input so that it can be reloaded with the app 
                # without the need for restarting the server or app
                script_stanza = "script://$SPLUNK_HOME/etc/apps/lacework/bin/setupReload.sh"
                configuration_stanza_accessor = getConfStanzaAccessor(
                    configuration_accessor, "inputs", script_stanza)
                configuration_stanza_accessor.update(
                    **{"disabled": "true"})
                service.apps.__getitem__("lacework").reload()
                configuration_stanza_accessor.update(
                    **{"disabled": "false"})
                service.apps.__getitem__("lacework").reload()

                # Send back a 201 message to let the users know that the domain was created successfully
                confInfo[LW_API_STANZA].append("status", "201")
                confInfo[LW_API_STANZA].append("domain", full_domain)
                confInfo[LW_API_STANZA].append("Message", "New domain: " + full_domain)

        # Otherwise, just simply display our current domain if there exists one
        else:
            confDict = self.readConf(LW_API_FILENAME)
            if confDict != None:
                if LW_API_STANZA in confDict:
                    stanzaDict = confDict[LW_API_STANZA]
                    if LW_API_FIELD_DOMAIN in stanzaDict:
                        full_domain = stanzaDict[LW_API_FIELD_DOMAIN]
                        confInfo[LW_API_STANZA].append("domain", full_domain)
                        confInfo[LW_API_STANZA].append("Message", "Current domain: " + full_domain)
            else:
                confInfo[LW_API_STANZA].append(
                    "Message", "Lacework-api.conf file does not exist. Please redo your setup.")
            confInfo[LW_API_STANZA].append("status", "200")

    def handleMembers(self, confInfo):
        """Called when user invokes the "members" action."""
        self.actionNotImplemented()

    def handleReload(self, confInfo):
        """Called when user invokes the "reload" action."""
        self.actionNotImplemented()

    def handleRemove(self, confInfo):
        """Called when user invokes the "remove" action."""
        self.actionNotImplemented()

    def handleCustom(self, confInfo):
        """
        Called when user invokes a custom action.  Implementer can find out which
        action is requested by checking self.customAction and self.requestedAction.
        The former is a string, the latter an action type (create/edit/delete/etc).
        """
        self.actionNotImplemented()


# initialize the handler
admin.init(APIDomainHandler, admin.CONTEXT_NONE)

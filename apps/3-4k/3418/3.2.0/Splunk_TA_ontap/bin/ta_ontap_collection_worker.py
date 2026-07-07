# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# Core Python Imports
import sys
import re
import datetime

# Add SA-Hydra packages to sys.path
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra', 'bin']))

# Import TA-Ontap collection codes
from ta_ontap import handlers
from ta_ontap.OntapClient import OntapClient, ClientSideError

from hydra.hydra_worker import HydraWorker


class TAOntapWorker(HydraWorker):
    title = "TA-Ontap Collection Worker"
    description = "Worker to perform Netapp ONTAP collection tasks."
    handlers = {
        "megaperf": handlers.MegaPerfHandler,
        "megainv": handlers.MegaInvHandler,
        "options": handlers.OptionsHandler,
        "volumeperf": handlers.VolumePerfHandler,
        "diskperf": handlers.DiskPerfHandler,
        "lunperf": handlers.LunPerfHandler,
        "aggrperf": handlers.AggrPerfHandler,
        "vfilerperf": handlers.VFilerPerfHandler,
        "qtreeperf": handlers.QTreePerfHandler,
        "quotaperf": handlers.QuotaPerfHandler,
        "systemperf": handlers.SystemPerfHandler,
        "icmpperf": handlers.ICMPPerfHandler,
        "ifnetperf": handlers.IFNETPerfHandler,
        "ipperf": handlers.IPPerfHandler,
        "udpperf": handlers.UDPPerfHandler,
        "tcpperf": handlers.TCPPerfHandler,
        "processorperf": handlers.ProcessorPerfHandler,
        "perfperf": handlers.PerfPerfHandler,
        "waflperf": handlers.WAFLPerfHandler,
        "aggr": handlers.AggrHandler,
        "disk": handlers.DiskHandler,
        "qtree": handlers.QtreeHandler,
        "quota": handlers.QuotaHandler,
        "vfiler": handlers.VfilerHandler,
        "volume": handlers.VolumeHandler,
        "ems": handlers.EMSHandler,
        "lun": handlers.LUNHandler,
        "nfsexports": handlers.NfsExportsHandler,
        "vserver": handlers.VserverHandler,
        "cifs_options": handlers.CIFSOptionsHandler,
        "cluster": handlers.ClusterHandler,
        "system": handlers.SystemHandler
    }
    app = "Splunk_TA_ontap"
    # The cached clients dictionary is used to save ontap client sessions locally
    # to the process as there is no benefit to session sharing.
    cached_clients = {}
    # stores bad client and time the client was marked bad
    bad_clients = {}
    BAD_CLIENT_LOGIN_PERIOD = 1800

    # For parsing target values at OntapClient creation
    target_parse_re = re.compile("^(https?)?(?:://)?([^:/]+)(?::(\d+))?/?$")

    def _client_key(self, target, user):
        return ':'.join([target, user])

    def getSessionForTarget(self, target, user, realm):
        """
        Overload of the base class method in order to disable hydra session
        caching. The Ontap API does not have a concept of session based authentication
        only of basic username-password authentication so there is no value in sharing
        sessions accross the processes.

        This method will create an Ontap client object for the given target and username,
        setting the versions and modes appropriately.
        ARGS:
                target - The target Ontap system to log in to
                user - The username with which to log into the target
                realm - get realm credentials if needed

        RETURNS the OntapClient object associated with the given target and user or None if
                target login fails
        """
        oc = None
        # Check if we have a cached client
        client_key = self._client_key(target, user)
        if client_key in self.bad_clients:
            last_attempt_dt = (datetime.datetime.now() - self.bad_clients[client_key]).total_seconds()
            if last_attempt_dt < self.BAD_CLIENT_LOGIN_PERIOD:
                self.logger.debug("[getSessionForTarget] target=%s labeled bad and ignored due to failed login attempts", target)
                return None

        if client_key in self.cached_clients:
            oc = self.cached_clients[client_key]
            # Check if the client is valid
            if self.isSessionValid(oc):
                # Session was valid, return it
                return oc

        # No session (ontap client) available, make one
        credential_realm = realm if realm else target
        password = self.getPassword(credential_realm, user)
        oc = self.loginToTarget(target, user, password)
        # Cache it and return it
        self.cached_clients[client_key] = oc
        return oc

    @staticmethod
    def parseTarget(target):
        """
        Parse the target field and return the protocol, server, and port
        ARGS:
                target - the singleton target string from the conf

        RETURNS a tuple of (protocol, server, port)
        """
        match = TAOntapWorker.target_parse_re.match(target)
        protocol, server, port = match.groups()
        if protocol is None:
            protocol = "HTTPS"
        else:
            protocol = protocol.upper()
        if port is None:
            port = 443
        else:
            port = int(port)
        return protocol, server, port

    def loginToTarget(self, target, user, password, realm=None):
        """
        Creates an OntapClient object for the given target, user with the given
        password.
        ARGS:
                target - the uri to the ontap asset we need to log in to
                user - the user name stored in splunkd associated with that target
                password - the password stored in splunkd associated with that target
                realm - the realm in the collection conf associated with this username

        RETURNS an OntapClient object for the given target and user
        """
        oc = None
        protocol, server, port = TAOntapWorker.parseTarget(target)
        for retry_count in range(4):
            try:
                oc = OntapClient(server, user, password, transport=protocol, port=port)
                major, minor = oc.getApiVersion(cached=False)
                is_clustered = oc.isClustered(cached=False)
                version = str(major) + "." + str(minor)
                self.logger.debug("[loginToTarget] Created OntapClient for target=%s user=%s version=%s clustered=%s", target, user, version, is_clustered)
                # if we previously marked this client as bad, unmark it
                self.bad_clients.pop(self._client_key(target, user), None)
                return oc
            except Exception as e:
                self.logger.exception("[loginToTarget] Failed to create OntapClient for target=%s user=%s: %s", target, user, str(e))
        self.logger.error("Could not login to target=%s with username=%s after num_retries=%s, setting OntapClient as None and marking this target as bad in the worker" % (target, user, retry_count))
        self.bad_clients[self._client_key(target, user)] = datetime.datetime.now()
        return None

    def isSessionValid(self, session):
        """
        Check that a given OntapClient object is valid and usable.
        For now we just check that it is not None.
        args:
                session - an OntapClient object to test

        RETURNS True if session is valid, False if it must be refreshed
        """
        return isinstance(session, OntapClient)


if __name__ == '__main__':
    worker = TAOntapWorker()
    worker.execute()
    sys.exit(0)

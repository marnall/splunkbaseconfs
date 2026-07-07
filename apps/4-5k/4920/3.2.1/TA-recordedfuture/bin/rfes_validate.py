"""Implement on-board validation of the app setup."""

import datetime
import sys
import re
import hashlib
import logging
import socket
import platform
from recordedfuture.api.rfclient import RFClient
from recordedfuture.api.splunk_api import SplunkClient
from requests.exceptions import ProxyError, HTTPError, SSLError

LGR = logging.getLogger(__name__)

RE_PROXY = (
    r"(?P<proxyprotocol>https?)://"
    r"((?P<username>[^:/]+):(?P<password>.+)@)?"
    r"(?P<proxyhost>[^:/]+)(:(?P<proxyport>\d+))?"
)
NO_PROXY_CFG = "No proxy configured."
SSLInvalid = "SSL certificate not valid: {}"


class RfesVerificationStep(object):
    """Contain config and result from a verification step."""

    fieldnames = ["Verification step", "Status", "Information", "Suggested action"]

    def __init__(self):
        """Initialize."""
        object.__init__(self)
        self.result_string = "Verification has not been initiated."
        self.name = type(self).__name__[20:]
        self.result_code = "Pending"
        self.result_suggestion = ""

    def output_dict(self):
        """Report result as a dict."""
        return {
            "Verification step": self.name,
            "Status": self.result_code,
            "Information": self.result_string,
            "Suggested action": self.result_suggestion,
        }

    def output_csv(self, fdcsv):
        """Write result as a CSV line."""
        fdcsv.writerow(self.output_dict())

    def report(self, code, message, suggestion):
        """Set result of verification log the message."""
        if self.result_code == "Pending":  # Don't overwrite
            self.result_code = code
            self.result_string = message
            self.result_suggestion = suggestion

    def report_success(self, message, suggestion=""):
        """Set result of verification to success and log the message."""
        self.report("Ok", message, suggestion)

    def report_error(self, message, suggestion=""):
        """Set result of verification to success and log the message."""
        self.report("Error", message, suggestion)

    def report_warning(self, message, suggestion=""):
        """Set result of verification to success and log the message."""
        self.report("Warning", message, suggestion)

    def report_na(
        self, message="Unable to verify due to previous error.", suggestion=""
    ):
        """Set result of verification to not available.

        Can happen due to missing pre-condition.
        """
        self.report("NA", message, suggestion)


class RfesVerificationStepAppVersion(RfesVerificationStep):
    """Collect and print app version and timestamp."""

    def run(self, app_env):
        """Perform verification."""
        msg = "Recorded Future for Splunk v{} (build {}), report created {}.".format(
            app_env.integration_version,
            app_env.build_id,
            datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.report_success(msg)


class RfesVerificationStepRFApiKey(RfesVerificationStep):
    """Verify that a token could be retreived from Splunk.

    Troubleshoot if not.
    """

    # noinspection InsecureHash
    def run(self, app_env):
        """Perform verification."""
        if app_env.api_key:
            # Report success and add 6 first characters of the Md5
            # sum of the token. This allows verification that the
            # correct token has been entered without revealing any
            # sensitive data. This fingerprint is not usable in itself.
            fingerprint = hashlib.sha256(app_env.api_key.encode("utf-8")).hexdigest()[
                :6
            ]
            msg = "API key was received from Splunk. Fingerprint: {}".format(
                fingerprint
            )
            self.report_success(msg)
            return

        # Token is not available. Figure out why.
        if app_env.session_key is None:
            self.report_na()

        else:
            self.report_error(
                "Could not retrieve api key. This indicates that the app hasn't been "
                "properly setup. "
                "Please configure the app."
            )


class RfesVerificationStepProxySetting(RfesVerificationStep):
    """If a proxy is configured, verify that it's a valid setting."""

    def run(self, app_env):
        """Perform verification."""
        if not app_env.proxy:
            self.report_na(NO_PROXY_CFG)
            return

        reproxy = re.compile(RE_PROXY)
        pmatch = reproxy.match(app_env.proxy["http"])
        if pmatch is None:  # Completely wrong
            self.report_error(
                'Invalid proxy setting: "{}"'.format(app_env.proxy["http"]),
                "Go to Configuration and enter a valid proxy setting. If a host "
                "name is entered it must be resolvable by the Splunk server.",
            )
            return

        pmd = pmatch.groupdict()
        if pmd["username"] is None or pmd["username"] in ["", "None"]:
            self.report_success(
                "Valid proxy setting: {}://{}:{}/".format(
                    pmd["proxyprotocol"], pmd["proxyhost"], pmd["proxyport"]
                )
            )
        else:
            self.report_success(
                "Valid proxy setting: {}://<redacted>:<redacted>@{}:{}/".format(
                    pmd["proxyprotocol"], pmd["proxyhost"], pmd["proxyport"]
                )
            )


class RfesVerificationStepProxyDNSResolution(RfesVerificationStep):
    """If a proxy is configured, verify that hostname resolution works."""

    def run(self, app_env):
        """Perform verification."""
        # NA if no proxy configured
        if not app_env.proxy:
            self.report_na(NO_PROXY_CFG)
            return
        # NA if proxy setting is not valid
        reproxy = re.compile(RE_PROXY)
        pmatch = reproxy.match(app_env.proxy["http"])
        if not pmatch:
            self.report_na()
        # Check name resolution
        proxyhost = pmatch.groupdict()["proxyhost"]
        try:
            proxyip = socket.gethostbyname(proxyhost)
            self.report_success(
                "Proxy host name {} resolves to {}.".format(proxyhost, proxyip)
            )
        except socket.gaierror as err:
            self.report_error(
                "Proxy host name can't be resolved: {}".format(err.strerror)
            )
        except Exception:  # pylint: disable=broad-except
            self.report_error(
                "Proxy host name can't be resolved: {}".format(sys.exc_info()[0])
            )


class RfesVerificationStepProxyConnectivity(RfesVerificationStep):
    """If a proxy is configured, verify that the proxy is reachable."""

    def run(self, app_env):
        """Perform verification."""
        # NA if no proxy configured
        if not app_env.proxy:
            self.report_na(NO_PROXY_CFG)
            return
        # NA if proxy setting is not valid
        reproxy = re.compile(RE_PROXY)
        pmatch = reproxy.match(app_env.proxy["http"])
        if not pmatch:
            self.report_na()
        # Check connectivity
        client = RFClient(app_env)
        try:
            client.config.info()
            self.report_success("Proxy is working.")
        except ProxyError:
            self.report_error("Proxy is not working: {}".format(sys.exc_info()[1]))
        except Exception:  # pylint: disable=broad-except
            self.report_error("Proxy is not working: {}".format(sys.exc_info()[0]))


class RfesVerificationStepApiUrlValue(RfesVerificationStep):
    """Verify that the api url is sane."""

    def run(self, app_env):
        """Perform verification."""
        try:
            self.report_success("API URL: {}".format(app_env.api_url))
        except Exception:  # pylint: disable=broad-except
            self.report_error("API URL is not available")


class RfesVerificationStepApiConnectivity(RfesVerificationStep):
    """Verify that the api is reachable."""

    def run(self, app_env):
        """Perform verification."""
        client = RFClient(app_env)
        try:
            req = client.config.helo()
            if "Recorded Future BFI for Splunk" in req.text:
                self.report_success("The Recorded Future API is reachable.")
            else:
                self.report_warning(
                    "A response was received from the Recorded Future API but it does "
                    "not contain the expected text. Please verify that it really is the"
                    " Recorded Future API that is reached.",
                    "Verify that it really is a valid API URL, ex try to fetch the URL "
                    "(default https://api.recordedfuture.com/gw/splunk/) manually. Ex "
                    "use the CLI tool curl on the Splunk server.",
                )
        except Exception:  # pylint: disable=broad-except
            self.report_error(
                "The Recorded Future API could not be reached: {}".format(
                    sys.exc_info()[0]
                )
            )


class RfesVerificationStepOSVersion(RfesVerificationStep):
    """Display the OS and version."""

    # pylint: disable=unused-argument
    def run(self, app_env):
        """Perform extraction of OS information."""
        os = platform.system()
        if os == "Linux":
            os_string = "Type: {}, Release: {}, Version: {}, Machine type: {}".format(
                os,
                platform.release(),
                platform.version(),
                platform.machine(),
            )
            self.report_success(os_string)
        elif os == "Windows":
            os_string = "Type: {}, Version: {}, Machine type: {}".format(
                os,
                platform.platform(),
                platform.machine(),
            )
            self.report_success(os_string)
        elif os == "Darwin":
            os_string = "Type: {}, Version: {}, Machine type: {}".format(
                os,
                platform.mac_ver()[0],
                platform.mac_ver()[2],
            )
            self.report_success(os_string)
        else:
            self.report_warning(
                "Unknown OS type. The app may not work.",
                "Please report your machine information to Recorded Future.",
            )


class RfesVerificationStepAuth(RfesVerificationStep):
    """Verify that the api is reachable."""

    def run(self, app_env):
        """Perform verification."""
        if not app_env.api_key:
            self.report_warning(
                "No API key available, verfication step can not be performed.",
                "Ensure that the RF API key can be retrieved from Splunk's "
                "password store.",
            )
            return

        # Call the whoami endpoint in the API
        client = RFClient(app_env)
        try:
            client.config.info()
            self.report_success("API calls can be performed. API key is valid.")
        except:  # noqa
            suggestion = (
                "Verify that an API key is configured on the "
                "configuration page and that it is valid."
            )
            self.report_error("Invalid or missing API Key", suggestion=suggestion)


class RfesVerificationStepSplunkVersion(RfesVerificationStep):
    """Basic info about the Splunk environment."""

    def run(self, app_env):
        """Perform verification."""
        if not app_env.session_key:
            self.report_na()
        else:
            splunk_version = app_env.splunk_version
            self.report_success("Splunk version is {}".format(splunk_version))


class RfesVerificationStepSplunkESVersion(RfesVerificationStep):
    """Basic info about the Splunk environment."""

    def run(self, app_env):
        """Perform verification."""
        if not app_env.session_key:
            self.report_na()
        else:
            splunk_es_active = " and activated" if app_env.es else " and not activated"
            splunk_es_version = app_env.splunk_es_version
            self.report_success(
                "Splunk ES version is {}{}".format(splunk_es_version, splunk_es_active)
            )


class RfesVerificationStepSplunkEsCompatibility(RfesVerificationStep):
    """Verify that Splunk ES is compatible with the current version of RF app"""

    def run(self, app_env):
        """Run verification"""
        client = RFClient(app_env)
        try:
            version = client.config.version_information()
        except HTTPError:
            msg = (
                "The current version of Splunk ES has not been tested with the installed "
                "version of Recorded Future's app"
            )
            self.report_error(msg)
            return
        splunk_es_version = ".".join(app_env.splunk_es_version.split(".")[:2])
        es_versions = [v for v in version["addons"] if v["name"] == "es"][0]
        if splunk_es_version in es_versions.get("versions", {}):
            self.report_success(
                "Current version of Splunk Enterprise Security is compatible with "
                "RF app"
            )
            return
        self.report_error(
            "Current version of Splunk Enterprise Security is not "
            "compatible with RF app"
        )


class RfesVerificationStepSplunkCompatibility(RfesVerificationStep):
    """Verify that Splunk is compatible with the current version of RF app"""

    def run(self, app_env):
        """Run verification"""
        client = RFClient(app_env)
        try:
            version = client.config.version_information()
        except HTTPError:
            msg = (
                "The current version of Splunk has not been tested with the installed "
                "version of Recorded Future's app"
            )
            self.report_error(msg)
            return
        splunk_version = ".".join(app_env.splunk_version.split(".")[:2])
        platform_version = version.get("platform_versions", [])
        if splunk_version in platform_version:
            self.report_success("Current version of Splunk is compatible with RF app")
            return
        app_env.logger.debug(
            "Splunk version {}, platform_versions {}".format(
                splunk_version, platform_version
            )
        )
        self.report_error(
            "Current version of Splunk has not been tested with the installed version of Recorded Future's app"
        )


class RfesVerificationStepRest(RfesVerificationStep):
    """Basic info about the Splunk Rest endpoint."""

    def run(self, app_env):
        """Perform verification."""
        if not app_env.server_uri:
            self.report_na()
        else:
            try:
                self.report_success(
                    "Splunk REST endpoint is {}".format(app_env.server_uri)
                )
            except Exception:  # pylint: disable=broad-except
                self.report_error(
                    "Unable to lookup Splunk REST endpoint: {}".format(
                        sys.exc_info()[0]
                    )
                )


class RfesVerificationStepSearchHeadCluster(RfesVerificationStep):
    """Check if it's a Search Head cluster."""

    def run(self, app_env):
        """Perform verification."""
        client = SplunkClient(app_env)
        is_cluster = client.config.is_shcluster()
        if is_cluster:
            self.report_success("Part of a Search Head cluster.")
            return
        self.report_success("Not part of a Search Head cluster.")


class RfesVerificationStepSearchHeadClusterCounts(RfesVerificationStep):
    """Get Search Head Cluster information."""

    def run(self, app_env):
        """Perform verification."""
        client = SplunkClient(app_env)
        try:
            shc_data = client.config.shc_context()
            indexer_data = client.config.shc_indexer_context()
            captain = ""
            num_shc = shc_data.get("paging", {}).get("total", 0)
            num_index = indexer_data.get("paging", {}).get("total", 0)
            num_index_disabled = 0
            for shc in shc_data.get("entry", []):
                if shc.get("content", {}).get("is_captain", False):
                    captain = shc.get("content", {}).get("label")
            for indexer in indexer_data.get("entry", []):
                if indexer.get("content", {}).get("disabled", False):
                    num_index += 1
        except HTTPError:
            self.report_success("Not part of a Search Head cluster.")
            return
        self.report_success(
            "Cluster consists of {} search heads ({} is the current captain) and "
            "{} indexers, of which {} are disabled.".format(
                num_shc, captain, num_index, num_index_disabled
            )
        )


class RfesVerificationStepFusionLists(RfesVerificationStep):
    """Verify that the defined fusion risk lists are accessible."""

    def run(self, app_env):
        """Perform verification."""
        app_env.logger.debug("Start RL Inputs")
        api = RFClient(app_env)
        failed = []
        app_env.logger.debug(str(app_env.correlation_feeds))
        for entry, values in app_env.correlation_feeds.items():
            app_env.logger.debug("Checking risklist: {}".format(entry))
            if values.get("disabled", False):
                continue
            else:
                if not values.get("fusion_risk_list", None):
                    cat = values.get("risk_list_category", None)
                    app_env.logger.debug("Category: {}".format(cat))
                    if cat:
                        path = "".join(["/public/default_", cat, "_risklist.csv"])
                        try:
                            res = api.feed.get(path)
                            app_env.logger.debug("Headers: {}".format(str(res)))
                        except HTTPError:
                            failed.append("Default {} risk list".format(cat))
                        except SSLError as err:
                            self.report_error(
                                SSLInvalid.format(str(err)),
                                suggestion="Disable SSL verification if this is "
                                "expected. Otherwise find out why the verification "
                                "fails.",
                            )

                else:
                    path = values["fusion_risk_list"]
                    app_env.logger.debug("Fusion path: {}".format(path))
                    try:
                        res = api.feed.get(path)
                        app_env.logger.debug("Headers: {}".format(str(res)))
                    except HTTPError:
                        failed.append(entry)
                    except SSLError as err:
                        self.report_error(
                            SSLInvalid.format(str(err)),
                            suggestion="Disable SSL verification if this is expected. "
                            "Otherwise find out why the verification fails.",
                        )
        if failed:
            self.report_error(
                "Could not access fusion file(s): {}".format(", ".join(failed)),
                suggestion="Make sure that the current API-key can access the fusion "
                "file(s) and that it/they exist.",
            )
        self.report_success("All configured risk lists can be accessed.")


###########################################################################
#
# Splunk ES Specific validation
#
###########################################################################


class RfesVerificationStepEsTracking(RfesVerificationStep):
    """Print out es-sharing."""

    def run(self, app_env):
        """Perform verification."""
        msg = "ES sharing-data configuration: {}".format(app_env.enrichment_mode)
        self.report_success(msg)


class RfesVerificationStepPythonVersion(RfesVerificationStep):
    """Verify the status of KV Storage in Splunk Enterprise."""

    def run(self, app_env):
        """Perform verification."""
        self.report_success(
            "Python version is {}".format(sys.version.replace("\n", ""))
        )


class RfesVerificationStepAlertActionsCreated(RfesVerificationStep):
    """Verify the status of KV Storage in Splunk Enterprise."""

    def run(self, app_env):
        """Perform verification."""
        aac = app_env.check_alert_actions_conf()
        if aac and app_env.es:
            self.report_success(
                "RF alert_actions.conf created and ES functionality enabled."
            )
        elif not aac and app_env.es:
            self.report_error(
                "RF alert_actions.conf not created but ES functionality is enabled."
            )
        elif aac and not app_env.es:
            self.report_success(
                "RF alert_actions.conf created but ES functionality is not enabled."
            )
        else:
            self.report_success(
                "RF alert_actions.conf not created and ES functionality is not enabled."
            )

        aac_prefix = app_env.check_alert_actions_prefix()
        if aac_prefix:
            self.report_success("RF alert_actions.conf is correctly configured")
        else:
            self.report_error(
                'RF alert_actions.conf is missing "param.prefix" parameter.'
            )


class RfesVerificationStepPlatformID(RfesVerificationStep):
    """Check platform string."""

    def run(self, app_env):
        """Perform actions."""
        self.report_success("Platform string: {}".format(app_env.platform_id))


class RfesVerificationStepGuid(RfesVerificationStep):
    """Check system GUID."""

    def run(self, app_env):
        """Perform check."""
        self.report_success("System GUID: {}".format(app_env.master_guid))


def validate(_, app_env):
    """Execute validation."""
    shared_verification_steps = [
        RfesVerificationStepAppVersion(),
        RfesVerificationStepSplunkVersion(),
        RfesVerificationStepSplunkCompatibility(),
        RfesVerificationStepGuid(),
        RfesVerificationStepOSVersion(),
        RfesVerificationStepPythonVersion(),
        RfesVerificationStepRest(),
        RfesVerificationStepRFApiKey(),
        RfesVerificationStepProxySetting(),
        RfesVerificationStepProxyDNSResolution(),
        RfesVerificationStepProxyConnectivity(),
        RfesVerificationStepApiUrlValue(),
        RfesVerificationStepApiConnectivity(),
        RfesVerificationStepAuth(),
        RfesVerificationStepSearchHeadCluster(),
        RfesVerificationStepSearchHeadClusterCounts(),
        RfesVerificationStepPlatformID(),
    ]

    if app_env.es_available:
        # Splunk ES validation steps
        verification_steps = list(shared_verification_steps)
        verification_steps.insert(3, RfesVerificationStepSplunkESVersion())
        verification_steps.insert(4, RfesVerificationStepSplunkEsCompatibility())
        verification_steps.append(RfesVerificationStepAlertActionsCreated())
        verification_steps.append(RfesVerificationStepEsTracking())
    else:
        # Splunk Enterprise validation steps
        verification_steps = shared_verification_steps
    for count, step in enumerate(verification_steps):
        try:
            step.run(app_env)
        except Exception as err:
            app_env.logger.error(
                "Validation step {} failed: {}".format(step, err), exc_info=1
            )
            step.report_error(
                "Error during verification: {} {} {}".format(
                    sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                )
            )

    validation = [
        {"step": "step_{}".format(step + 1), "result": result.output_dict()}
        for step, result in enumerate(verification_steps)
    ]
    reslist = [{"name": ent["step"], "content": ent} for ent in validation]
    return 200, {"entry": reslist}

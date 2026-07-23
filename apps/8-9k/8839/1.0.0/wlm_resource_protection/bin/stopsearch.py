import sys
import json
from splunk.rest import simpleRequest
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators
import splunk.mining.dcutils as dcu

logger = dcu.getLogger()


@Configuration()
class StopSearch(EventingCommand):
    terminate_search = Option(require=True, validate=validators.Integer(), default=0)

    default_threshold = float("inf")
    metrics = [
        "total_vcpu_sec", "total_mem_gib_sec", "shs_vcpu_sec", "shs_mem_gib_sec",
        "idxs_vcpu_sec", "idxs_mem_gib_sec", "max_shs_vcpu_sec", "max_idxs_vcpu_sec", 
        "max_shs_mem_usage", "max_idxs_mem_usage"
    ]
    threshold_postfix = "_th"
    thresholds_endpoint = (
        "/services/properties/wlm_resource_protection/thresholds?output_mode=json"
    )
    general_settings_endpoint = (
        "/services/properties/wlm_resource_protection/general?output_mode=json"
    )

    def sendMessageToAudit(self, sid):
        try:
            sh_name = self.service.info["serverName"]
            message = (
                "Search sid={0} was terminated by Splunk WLM Resource Protection App"
                "(HeavySearchesTerminator)"
            ).format(sid)

            self.service.indexes["_audit"].submit(
                event=message,
                host=sh_name,
                source="heavy_searches_terminator",
                sourcetype="wlm_resource_protection"
            )

            logger.debug(
                "Successfully sent raw message to _audit for SID: {0}".format(sid)
            )

        except Exception as e:
            logger.error(
                "Error sending message to _audit for SID {0}: {1}".format(sid, str(e))
            )

    def isTrueSetting(self, value):
        return str(value).strip().lower() == "true"

    def cancelSearch(self, sid):
        logger.info("Trying to cancel search with SID: {0}".format(sid))
        try:
            path = "/services/search/jobs/{0}/control".format(sid)
            post_data = {'action': 'cancel'}
            response, content = simpleRequest(
                path,
                sessionKey=self.service.token,
                method='POST',
                postargs=post_data
            )

            if response.status in [200, 204]:
                logger.info("Successfully cancelled search SID: {0}".format(sid))
                return True
            else:
                logger.error(
                    "Failed to cancel SID {0}. Status: {1}".format(sid, response.status)
                )
                return False

        except Exception as e:
            logger.error("Error cancelling search {0}: {1}".format(sid, str(e)))
            return False

    def normalizeUser(self, user):
        if isinstance(user, list):
            return user[0] if user else ""
        return user or ""

    def getUserEmail(self, user):
        user = self.normalizeUser(user)
        if not user:
            logger.error("Cannot get user email because username is empty")
            return None

        try:
            path = "/services/authentication/users/{0}?output_mode=json".format(user)
            response, content = simpleRequest(
                path,
                sessionKey=self.service.token,
                method='GET'
            )

            if response.status != 200:
                logger.error(
                    "Failed to get email for user {0}. Status: {1}".format(
                        user,
                        response.status
                    )
                )
                return None

            if isinstance(content, bytes):
                content = content.decode('utf-8')

            payload = json.loads(content)
            if "entry" in payload and len(payload["entry"]) > 0:
                email = payload["entry"][0].get("content", {}).get("email")
                if email:
                    return email

            logger.error("Email is not configured for user {0}".format(user))
            return None

        except Exception as e:
            logger.error("Error getting email for user {0}: {1}".format(user, str(e)))
            return None

    def getSearchQuery(self, sid):
        if not sid:
            logger.error("Cannot get search query because SID is empty")
            return None

        try:
            path = "/services/search/jobs/{0}?output_mode=json".format(sid)
            response, content = simpleRequest(
                path,
                sessionKey=self.service.token,
                method='GET'
            )

            if response.status != 200:
                logger.error(
                    "Failed to get search query for SID {0}. Status: {1}".format(
                        sid,
                        response.status
                    )
                )
                return None

            if isinstance(content, bytes):
                content = content.decode('utf-8')

            payload = json.loads(content)
            if "entry" in payload and len(payload["entry"]) > 0:
                search_query = payload["entry"][0].get("content", {}).get("search")
                if search_query:
                    return search_query

            logger.error("Search query is not available for SID {0}".format(sid))
            return None

        except Exception as e:
            logger.error("Error getting search query for SID {0}: {1}".format(sid, str(e)))
            return None

    def getSearchOwner(self, sid):
        if not sid:
            logger.error("Cannot get search owner because SID is empty")
            return None

        try:
            path = "/services/search/jobs/{0}?output_mode=json".format(sid)
            response, content = simpleRequest(
                path,
                sessionKey=self.service.token,
                method='GET'
            )

            if response.status != 200:
                logger.error(
                    "Failed to get search owner for SID {0}. Status: {1}".format(
                        sid,
                        response.status
                    )
                )
                return None

            if isinstance(content, bytes):
                content = content.decode('utf-8')

            payload = json.loads(content)
            if "entry" in payload and len(payload["entry"]) > 0:
                entry = payload["entry"][0]
                owner = entry.get("acl", {}).get("owner")
                if not owner:
                    owner = entry.get("content", {}).get("eai:acl", {}).get("owner")
                if owner:
                    return owner

            logger.error("Search owner is not available for SID {0}".format(sid))
            return None

        except Exception as e:
            logger.error("Error getting search owner for SID {0}: {1}".format(sid, str(e)))
            return None

    def escapeSplunkString(self, value):
        return json.dumps(value or "")[1:-1]

    def sendEmailToUser(self, user, sid, search_query):
        user = self.normalizeUser(user)
        user_email = self.getUserEmail(user)
        if not user_email:
            return False

        logger.info("Trying to send notification email to user {0}".format(user))
        try:
            message = (
                "Your recent search was stopped by Splunk WLM Resource Protection App because it consumed a high "
                "level of resources.\n\n"
                "SID: {0}\n"
                "Search query: {1}\n\n"
                "Please contact a Splunk administrator if you need help tuning or "
                "rerunning this search."
            ).format(
                sid,
                search_query or "Unavailable"
            )
            dispatch_search = (
                '| makeresults '
                '| eval msg="{0}" '
                '| sendemail to="{1}" subject="Splunk WLM Resource Protection App notification" '
                'message="$result.msg$" '
                'sendresults=false'
            ).format(
                self.escapeSplunkString(message),
                self.escapeSplunkString(user_email)
            )
            logger.info(
                "Dispatching notification email search for user {0}: {1}".format(
                    user,
                    dispatch_search
                )
            )

            response, content = simpleRequest(
                "/services/search/jobs",
                sessionKey=self.service.token,
                method='POST',
                postargs={
                    'search': dispatch_search,
                    'exec_mode': 'normal'
                }
            )

            if response.status in [200, 201]:
                logger.info(
                    "Successfully dispatched notification email search for user {0}".format(
                        user
                    )
                )
                return True

            logger.error(
                "Failed to dispatch notification email search for user {0}. Status: {1}".format(
                    user,
                    response.status
                )
            )
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            logger.error(
                "Notification email search dispatch response for user {0}: {1}".format(
                    user,
                    content
                )
            )
            return False

        except Exception as e:
            logger.error("Error sending email to user {0}: {1}".format(user, str(e)))
            return False

    def getWorkloadThresholds(self):
        thresholds = {}
        for metric in self.metrics:
            thresholds[metric + self.threshold_postfix] = self.default_threshold

        try:
            response, content = simpleRequest(
                self.thresholds_endpoint,
                sessionKey=self.service.token,
                method='GET'
            )

            if response.status != 200:
                logger.error(
                    "Failed to get Workloads Thresholds from {0}. Status: {1}".format(
                        self.thresholds_endpoint,
                        response.status
                    )
                )
            else:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')

                payload = json.loads(content)

                if "entry" in payload:
                    for item in payload["entry"]:
                        name = item.get("name")
                        value = item.get("content")
                        if name in thresholds:
                            try:
                                thresholds[name] = float(value)
                            except (TypeError, ValueError):
                                logger.error(
                                    "Invalid threshold value for {0}: {1}".format(
                                        name,
                                        value
                                    )
                                )

        except Exception as e:
            logger.error("Error in getWorkloadThresholds: {0}".format(str(e)))

        message = "WLM threshholds: "
        for metric in self.metrics:
            message += metric + "=" + str(thresholds[metric + self.threshold_postfix]) + ", "

        logger.debug(message)

        return thresholds

    def isSendEmailEnabled(self):
        try:
            response, content = simpleRequest(
                self.general_settings_endpoint,
                sessionKey=self.service.token,
                method='GET'
            )

            if response.status != 200:
                logger.error(
                    "Failed to get general settings from {0}. Status: {1}".format(
                        self.general_settings_endpoint,
                        response.status
                    )
                )
                return False

            if isinstance(content, bytes):
                content = content.decode('utf-8')

            payload = json.loads(content)
            if "entry" in payload:
                for item in payload["entry"]:
                    if item.get("name") == "sendemail":
                        return self.isTrueSetting(item.get("content"))

            logger.error("sendemail setting is missing in general configuration")
            return False

        except Exception as e:
            logger.error("Error in isSendEmailEnabled: {0}".format(str(e)))
            return False

    def transform(self, records):
        thresholds = self.getWorkloadThresholds()
        send_email_enabled = self.isSendEmailEnabled()
        output_result = {}

        for record in records:
            sid = record.get('sid')
            metrics_values = {}
            for metric in self.metrics:
                metric_value = record.get(metric, 0)
                if metric_value in (None, ""):
                    metric_value = 0
                metrics_values[metric] = float(metric_value)

            for metric_name, value in metrics_values.items():
                threshold_value = thresholds[metric_name + "_th"]
                if value > threshold_value:
                    output_result[sid] = (
                        "Search {0} terminated, because of {1}={2} ({3})"
                    ).format(sid, metric_name, value, threshold_value)
                    if self.terminate_search:
                        user = record.get('user')
                        if not self.normalizeUser(user):
                            user = self.getSearchOwner(sid)
                        search_query = self.getSearchQuery(sid)
                        if self.cancelSearch(sid):
                            if send_email_enabled:
                                self.sendEmailToUser(user, sid, search_query)
                            self.sendMessageToAudit(sid)
                    break
                else:
                    output_result[sid] = "Search {0} not Terminated".format(sid)

        for sid in output_result:
            yield {
                'sid': sid,
                'terminated_reason': output_result[sid]
            }


if __name__ == "__main__":
    dispatch(StopSearch, sys.argv, sys.stdin, sys.stdout, __name__)

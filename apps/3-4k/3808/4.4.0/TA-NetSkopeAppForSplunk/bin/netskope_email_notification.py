import sys
import traceback
import requests
import log
import time

from solnlib.splunkenv import get_splunkd_uri
import splunklib.client as client
import splunklib.results as results
from netskope_utils import read_conf_file

logger = log.get_logger("email_notification")

INTERNAL_VERIFY_SSL = False
NETSKOPE_ACCOUNT_CONF = "ta_netskopeappforsplunk_account"
NETSKOPE_SETTINGS_CONF = "ta_netskopeappforsplunk_settings"
INPUT_CONF = "inputs"
SOURCETYPE_MAPPING = {
    "alerts": "netskope:alert",
    "clients": "netskope:clients",
    "network": "netskope:network",
    "application": "netskope:application",
    "audit": "netskope:audit",
    "connection": "netskope:connection",
    "infrastructure": "netskope:infrastructure",
    "incident": "netskope:incident",
    "web_transaction": "netskope:web_transaction"
}

EMAIL_SUBJECT = "[NetSkope Add-on for Splunk][Email Notification Triggered] No Data has been collected since last "\
    "{} hours."
EMAIL_DEFAULT_BODY = "No Data has been collected since last {} hours for Input: {}, Tenant: {} and "\
    "sourcetype: [$result.sourcetype$]. {}"


class SendEmailNotification:
    """Class to handle sending email notifications."""

    def __init__(self):
        """Initialize the SendEmailNotification class."""
        pass

    def run(self):
        """Run the email notification process."""
        session_key = self._get_session_key()

        email_config = read_conf_file(session_key, NETSKOPE_SETTINGS_CONF, stanza="email_notification")
        notification_status = (
            int(email_config.get("email_enable"))
            if email_config.get("email_enable") is not None
            else 0
        )

        if notification_status:
            account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF)
            suppress_enabled = (
                int(email_config.get("enable_throttle"))
                if email_config.get("enable_throttle") is not None
                else 0
            )
            suppress_duration = email_config.get("throttle_duration")
            conf_file_stanzas = read_conf_file(session_key, INPUT_CONF)

            default_indexes = set(self._get_default_indexes(session_key))

            for input_stanza in conf_file_stanzas:
                if "netskope_events_v2://" in input_stanza and conf_file_stanzas[input_stanza].get("disabled") == '0':
                    current_time = int(time.time())
                    if (suppress_enabled
                            and not self._check_timestamp(session_key, input_stanza, suppress_duration, current_time)):
                        continue
                    input_name = input_stanza.split("://")[-1]
                    index = []
                    input_index = conf_file_stanzas[input_stanza].get("index")
                    if input_index == "default":
                        for default_index in default_indexes:
                            index.append(default_index)
                    else:
                        index.append(input_index)

                    global_account = conf_file_stanzas[input_stanza].get("global_account")
                    tenant_name = account_config.get(global_account, {}).get("hostname")

                    event_types = conf_file_stanzas[input_stanza].get("event_type").split("~")
                    sourcetypes = []
                    for event_type in event_types:
                        sourcetypes.append(SOURCETYPE_MAPPING[event_type])

                    result = self._create_and_execute_query(
                        session_key,
                        sourcetypes,
                        index,
                        email_config,
                        input_name,
                        tenant_name
                    )
                    if len(result):
                        self._set_timestamp(session_key, input_name, current_time)
                        logger.info(
                            "Email has been sent successfully for Input: {}, Tenant: {} and Sourcetype: {}.".format(
                                input_name,
                                tenant_name,
                                result
                            ))

                elif ("netskope_alerts_v2://" in input_stanza or "netskope_alerts://" in input_stanza
                      and conf_file_stanzas[input_stanza].get("disabled") == '0'):
                    current_time = int(time.time())
                    if (suppress_enabled
                            and not self._check_timestamp(session_key, input_stanza, suppress_duration, current_time)):
                        continue
                    self._send_email(
                        session_key,
                        input_stanza,
                        conf_file_stanzas,
                        default_indexes,
                        email_config,
                        "alerts",
                        account_config,
                        current_time
                    )

                elif "netskope://" in input_stanza and conf_file_stanzas[input_stanza].get("disabled") == '0':
                    current_time = int(time.time())
                    if (suppress_enabled
                            and not self._check_timestamp(session_key, input_stanza, suppress_duration, current_time)):
                        continue
                    input_name = input_stanza.split("://")[-1]
                    index = []
                    input_index = conf_file_stanzas[input_stanza].get("index")
                    if input_index == "default":
                        for default_index in default_indexes:
                            index.append(default_index)
                    else:
                        index.append(input_index)

                    global_account = conf_file_stanzas[input_stanza].get("global_account")
                    tenant_name = self._get_tenant_name(account_config, global_account)

                    event_types = conf_file_stanzas[input_stanza].get("event_type").split("~")
                    sourcetypes = []
                    for event_type in event_types:
                        sourcetypes.append(SOURCETYPE_MAPPING[event_type])

                    result = self._create_and_execute_query(
                        session_key,
                        sourcetypes,
                        index,
                        email_config,
                        input_name,
                        tenant_name
                    )
                    if len(result):
                        self._set_timestamp(session_key, input_name, current_time)
                        logger.info(
                            "Email has been sent successfully for Input: {}, Tenant: {} and Sourcetype: {}.".format(
                                input_name,
                                tenant_name,
                                result
                            ))

                elif "netskope_clients://" in input_stanza and conf_file_stanzas[input_stanza].get("disabled") == '0':
                    current_time = int(time.time())
                    if (suppress_enabled
                            and not self._check_timestamp(session_key, input_stanza, suppress_duration, current_time)):
                        continue
                    self._send_email(
                        session_key,
                        input_stanza,
                        conf_file_stanzas,
                        default_indexes,
                        email_config,
                        "clients",
                        account_config,
                        current_time
                    )

                elif ("netskope_webtransactions_v2://" in input_stanza
                      and conf_file_stanzas[input_stanza].get("disabled") == '0'):
                    current_time = int(time.time())
                    if (suppress_enabled
                            and not self._check_timestamp(session_key, input_stanza, suppress_duration, current_time)):
                        continue
                    self._send_email(
                        session_key,
                        input_stanza,
                        conf_file_stanzas,
                        default_indexes,
                        email_config,
                        "web_transaction",
                        account_config,
                        current_time
                    )
        else:
            logger.debug("Email notificaiton is disabled.")

    def _send_email(
            self,
            session_key,
            input_stanza,
            conf_file_stanzas,
            default_indexes,
            email_config,
            input_type,
            account_config,
            current_time):
        input_name = input_stanza.split("://")[-1]
        index = []
        input_index = conf_file_stanzas[input_stanza].get("index")
        if input_index == "default":
            for default_index in default_indexes:
                index.append(default_index)
        else:
            index.append(input_index)

        global_account = conf_file_stanzas[input_stanza].get("global_account")
        tenant_name = self._get_tenant_name(account_config, global_account)

        sourcetypes = [SOURCETYPE_MAPPING[input_type]]
        status = self._create_and_execute_query(session_key, sourcetypes, index, email_config, input_name, tenant_name)

        if status:
            self._set_timestamp(session_key, input_name, current_time)
            logger.info("Email has been sent successfully for Input: {}, Tenant: {}.".format(input_name, tenant_name))

    def _get_default_indexes(self, session_key):
        """Get the default Indexes."""
        uri = get_splunkd_uri()
        url: str = "{}/services/authorization/roles".format(uri)
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer {}".format(session_key),
        }
        params = {
            "output_mode": "json"
        }
        response = requests.get(url, headers=headers, params=params, verify=INTERNAL_VERIFY_SSL)

        if response.status_code == 200:
            logger.debug("Successfully got the default Indexes.")
        else:
            logger.warn("Failed to get the default Indexes.")
            return []

        response = response.json()
        roles = response.get("entry")
        indexes = []
        for role in roles:
            index = role.get("content").get("srchIndexesDefault")
            indexes.extend(index)

        return indexes

    def _create_index_query(self, indexes):
        """Create a query from the given indexes."""
        indexes_list = ["index=\"{}\"".format(index) for index in indexes]
        index_query = " OR ".join(indexes_list)

        return index_query

    def _create_sourcetype_query(self, sourcetypes):
        """Create a query from the given sourcetype."""
        sourcetype_list = ["sourcetype=\"{}\"".format(sourcetype) for sourcetype in sourcetypes]
        sourcetype_query = " OR ".join(sourcetype_list)

        return sourcetype_query

    def _add_sourcetype(self, sourcetypes):
        """Create a query to add all the sourcetypes."""
        query = ""
        base_query = "| append [| makeresults | eval sourcetype=\"{}\", recentTime=0]"
        for each in sourcetypes:
            query += base_query.format(each)

        return query

    def _create_and_execute_query(self, session_key, sourcetypes, indexes, email_config, input_name, tenant_name):
        """Create a query and execute it."""
        sourcetype_query = self._create_sourcetype_query(sourcetypes)
        index_query = self._create_index_query(indexes)
        add_sourcetype_query = self._add_sourcetype(sourcetypes)
        current_time = int(time.time())
        notify_after = int(email_config.get("notify_after"))
        query = "| metadata type=sourcetypes {} | search {} | table sourcetype, recentTime {} "\
            "| sort - recentTime | dedup sourcetype | where {} - recentTime > {} " \
                "| table sourcetype | mvcombine sourcetype delim=\", \" | nomv sourcetype".format(
                    index_query,
                    sourcetype_query,
                    add_sourcetype_query,
                    current_time,
                    notify_after * 60 * 60
                )

        message = EMAIL_DEFAULT_BODY.format(
            notify_after, input_name, tenant_name, email_config.get("additional_message")
        )
        send_email_query = " | sendemail to=\"{}\" format=html subject=\"{}\" message=\"{}\""\
            " server={}".format(
                email_config.get("email_address"),
                EMAIL_SUBJECT.format(notify_after),
                message,
                email_config.get("smtp_server")
            )

        final_query = query + send_email_query
        service = client.connect(token=session_key)
        result = results.JSONResultsReader(service.jobs.oneshot(final_query, output_mode='json'))
        result = list(result)
        logger.debug("Executed the query to get inactive sourcetypes.")
        return result

    def _get_tenant_name(self, account_config, global_account):
        """Get tenant name from the account stanza."""
        for account in account_config:
            if account == global_account:
                return account_config.get(account).get("hostname")
        return ""

    def _check_timestamp(self, session_key, input_stanza, suppress_duration, current_time):
        """Check the timestamp for suppressing email."""
        input_name = input_stanza.split("://")[-1]
        timestamp = self._get_timestamp(session_key, input_name)
        suppress_duration = int(suppress_duration) * 3600
        if timestamp is not None and timestamp != 0 and suppress_duration > (current_time - int(timestamp)):
            return False
        else:
            if timestamp is None:
                self._add_input(session_key, input_name)
            return True

    def _get_timestamp(self, session_key, input_type):
        """Get timstamp from the lookup."""
        query = "| inputlookup netskope_email_notification where _key=\"{}\" | table timestamp".format(input_type)
        service = client.connect(token=session_key)
        result = results.JSONResultsReader(service.jobs.oneshot(query, output_mode='json'))
        result = list(result)
        if len(result) > 0 and isinstance(result, list) and isinstance(result[0], dict):
            timestamp = list(result)[0].get("timestamp", None)
            return timestamp

        return None

    def _set_timestamp(self, session_key, input_name, timestamp):
        """Get timstamp from the lookup."""
        query = "| inputlookup netskope_email_notification where _key=\"{}\" | eval timestamp=\"{}\", key=_key "\
            "| outputlookup netskope_email_notification key_field=key".format(input_name, timestamp)
        service = client.connect(token=session_key)
        result = results.JSONResultsReader(service.jobs.oneshot(query, output_mode='json'))

        return result

    def _add_input(self, session_key, input_name):
        """Get timstamp from the lookup."""
        query = "| makeresults | eval input=\"{}\", timestamp={} | outputlookup netskope_email_notification"\
            " key_field=input append=true".format(input_name, 0)
        service = client.connect(token=session_key)
        result = results.JSONResultsReader(service.jobs.oneshot(query, output_mode='json'))

        return result

    def _get_session_key(self):
        """
        Get the session key.

        :return: This function returns the session_key value.
        """
        session_key = sys.stdin.readline().strip()
        return session_key


if __name__ == "__main__":
    send_email_notification_object = SendEmailNotification()
    try:
        send_email_notification_object.run()
    except Exception:
        logger.error("Error occurred in sending Email Notification. Traceback: %s.", traceback.format_exc())

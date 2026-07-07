import sys
import traceback

import splunk.auth

from nbalib import sections
from nbalib import sendlog
from nbalib import logger
from nbalib import confs
from nbalib import api

from nbalib.asoc3 import six

DHCP_SENDLOG_SCRIPT_FILES = (
    "script://./bin/nba_sendlog_dhcp.py",
    "script://.\\bin\\nba_sendlog_dhcp.py",
)


class SendlogDHCP(sendlog.Sendlog):
    def __init__(self, config, session_key, log):
        super(SendlogDHCP, self).__init__(config, session_key, log)

        self.in_scope = 0
        self.out_scope = 0
        self.invalid_events = 0
        self.no_leases = 0

    def get_query(self):
        tags = 'tag="network" tag="session" tag="dhcp"'
        logs_index = self.get_logs_index('nbalogsindexdhcp')
        timeranges = self.format_timeranges()

        return (
            '| prjob num_of_reducers=0 [search {0} {1} {2} _indextime > {3} _indextime <= {4} '
            '| eval dest_ip = if(isnull(dest_ip), dest, dest_ip) '
            '| eval time = strftime(_time, "%Y-%m-%dT%H:%M:%S%z") '
            '| eval msg_types = mvjoin(\'msg_types{{}}\', ",") '
            '| table _indextime, time, dest_ip, dest_nt_host, dest_mac, user, '
            'lease_duration, signature, msdhcp_id, msg_types]'
        ).format(logs_index, tags, timeranges, self.period.start, self.period.end)

    def parse_indextime(self, result):
        return self.get_indextime(result.get('_indextime'))

    def parse_result(self, result):
        src_ip = result.get('dest_ip', '')
        if not src_ip:
            self.invalid_events += 1
            return None

        scope_groups = self.scope.in_scope(src_ip)
        if not scope_groups:
            self.out_scope += 1
            return None
        self.in_scope += 1

        if not self.is_lease(result):
            self.no_leases += 1
            return None

        src_host = result.get('dest_nt_host', '')
        src_mac = result.get('dest_mac', '')
        src_user = result.get('user', '')

        if not src_host and not src_mac and not src_user:
            self.invalid_events += 1
            return None

        api_log = self._create_api_log(src_ip, result)
        return api_log.content

    @staticmethod
    def is_lease(result):
        msdhcp_id = result.get('msdhcp_id')
        if msdhcp_id == "10" or msdhcp_id == "11":
            return True

        signature = result.get('signature')
        if isinstance(signature, six.string_types) and signature.lower().strip() in ["dhcpack", "dhcp ack"]:
            return True

        msg_types = result.get('msg_types')
        if isinstance(msg_types, six.string_types):
            for mtype in msg_types[:100].split(","):
                if mtype.lower() == "ack":
                    return True

        return False

    @staticmethod
    def _create_api_log(src_ip, result):
        api_log = sendlog.APILog()

        api_log.set('type', sections.DHCP.name)
        api_log.set('ts', result.get('time', ''))

        api_log.set('srcIP', src_ip)
        api_log.set_non_empty('srcHost', result.get('dest_nt_host'))
        api_log.set_non_empty('srcMac', result.get('dest_mac'))
        api_log.set_non_empty('srcUser', result.get('user'))

        api_log.set_integer('duration', result.get('lease_duration'))

        return api_log

    def after_send_failure(self):
        self._reset_log_metrics()

    def after_send(self):
        self._log_metrics()

    def _log_metrics(self):
        self._log.info((
            "events passed through the monitoring scopes: {0}, "
            "events filtered out: {1}, invalid events: {2}, no leases {3}"
        ).format(self.in_scope, self.out_scope, self.invalid_events, self.no_leases))

        if self.out_scope > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageOutOfScope())

        if self.invalid_events > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageInvalidLogs())

        self._reset_log_metrics()

    def _reset_log_metrics(self):
        self.in_scope = 0
        self.out_scope = 0
        self.invalid_events = 0
        self.no_leases = 0


def save_data_messages(log, session_key):
    config = confs.Config(session_key, stanza=sections.DHCP.name)
    log.ui_save(config)


def main(log):
    log.info("--- sendlog start")

    # If the script is called by splunk, session key is passed in stdin
    if len(sys.argv) > 1:
        session_key = splunk.auth.getSessionKey(sys.argv[1], sys.argv[2])
    else:
        session_key = sys.stdin.readline()
    log.info("got session key")

    try:
        sendlog_config = sendlog.Config(sections.DHCP.name, script_paths=DHCP_SENDLOG_SCRIPT_FILES)
        sendlog_dhcp = SendlogDHCP(sendlog_config, session_key, log)
        log.info("sendlog created")

        sendlog_dhcp.run()
    except (sendlog.SendlogError, api.MasterNodeError) as exc:
        log.warn(repr(exc))
        save_data_messages(log, session_key)
    except api.AuthError as exc:
        log.warn(repr(exc))
        log.ui_append(logger.MessageUnauthorizedAPI(exc.api_messages))
        save_data_messages(log, session_key)
    except confs.PerrmisionException as exc:
        log.error(repr(exc))
        log.ui_append(logger.MessageUnauthorizedSplunk())
        save_data_messages(log, session_key)
    except Exception as exc:
        log.error(repr(exc))
        log.error(traceback.format_exc())
        log.ui_append(logger.MessageUnexpectedError(repr(exc)))
        save_data_messages(log, session_key)

    log.info("sendlog exit")


if __name__ == "__main__":
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "sendlog_dhcp")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())

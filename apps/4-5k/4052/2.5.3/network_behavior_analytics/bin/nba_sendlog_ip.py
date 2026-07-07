import sys
import traceback

import splunk.auth

from nbalib import validators
from nbalib import sections
from nbalib import sendlog
from nbalib import logger
from nbalib import anomaly
from nbalib import confs
from nbalib import api

MAX_INVALID_SAMPLE_ITEMS = 20


class SendlogIP(sendlog.Sendlog):
    def __init__(self, config, session_key, log):
        super(SendlogIP, self).__init__(config, session_key, log)
        self.anomaly = anomaly.Anomaly(config.section)

        self.in_scope = 0
        self.out_scope = 0

        self.invalid_sample = set()
        self.invalid_events = 0

    def get_query(self):
        tags = 'tag="network" tag="communicate"'
        logs_index = self.get_logs_index("nbalogsindexip")
        timeranges = self.format_timeranges()

        return (
            "| prjob num_of_reducers=0 [search {0} {1} {2} _indextime > {3} _indextime <= {4} "
            "| eval dest_ip = if(isnull(dest_ip), dest, dest_ip) "
            '| where not cidrmatch("10.0.0.0/8", dest_ip) and not cidrmatch("172.16.0.0/12", dest_ip) '
            'and not cidrmatch("192.168.0.0/16", dest_ip) and not cidrmatch("fc00::/7", dest_ip) '
            "| eval src_ip = if(isnull(src_ip), src, src_ip) "
            "| eval src_host = if(isnull(src_host), src_nt_host, src_host) "
            "| eval src_user = if(isnull(src_user), user, src_user) "
            "| eval transport = if(isnull(transport), protocol, transport) "
            "| eval bytes_out = if(isnull(bytes_out), bytes, bytes_out) "
            "| eval tcp_flags = if(isnull(tcp_flags), tcp_flag, tcp_flags) "
            "| eval tcp_flags = mvjoin('tcp_flags', \",\") "
            '| eval time = strftime(_time, "%Y-%m-%dT%H:%M:%S%z") '
            "| table _indextime, time, src_ip, src_port, src_host, src_mac, src_user, dest_ip, dest_port, "
            "transport, bytes_in, bytes_out, app, action, duration, tcp_flags]"
        ).format(logs_index, tags, timeranges, self.period.start, self.period.end)

    def parse_indextime(self, result):
        return self.get_indextime(result.get("_indextime"))

    def parse_result(self, result):
        dest_ip = result.get("dest_ip", "")
        src_ip = result.get("src_ip", "")

        if not dest_ip or not src_ip:
            self.invalid_events += 1
            return None

        valid_dest_ip = validators.IP.full_valid_ip(dest_ip)
        if not valid_dest_ip:
            self.add_invalid_sample(dest_ip)
            self.invalid_events += 1
            return None

        scope_groups = self.scope.in_scope(src_ip, dest_ip=valid_dest_ip)
        if not scope_groups:
            self.out_scope += 1
            return None

        self.in_scope += 1
        api_log = self._create_api_log(src_ip, valid_dest_ip, result)

        try:
            self.anomaly.detect(api_log.content, scope_groups, self.scope)
        except Exception as exc:
            self._log.warn("could not detect anomaly: {0}".format(repr(exc)))

        return api_log.content

    def add_invalid_sample(self, dest_ip):
        if len(self.invalid_sample) < MAX_INVALID_SAMPLE_ITEMS:
            self.invalid_sample.add(dest_ip)

    @staticmethod
    def _create_api_log(src_ip, dest_ip, result):
        api_log = sendlog.APILog()

        api_log.set("ts", result.get("time", ""))
        api_log.set("destIP", dest_ip)
        api_log.set("srcIP", src_ip)

        api_log.set_integer("srcPort", result.get("src_port"))
        api_log.set_non_empty("srcHost", result.get("src_host"))
        api_log.set_non_empty("srcMac", result.get("src_mac"))
        api_log.set_non_empty("srcUser", result.get("src_user"))

        api_log.set_non_empty_lower("proto", result.get("transport"))
        api_log.set_integer("destPort", result.get("dest_port"))

        api_log.set_integer("bytesIn", result.get("bytes_in"))
        api_log.set_integer("bytesOut", result.get("bytes_out"))

        api_log.set_non_empty("app", result.get("app"))
        api_log.set_non_empty_lower("action", result.get("action"))
        api_log.set_float("duration", result.get("duration"))
        api_log.set_non_empty("tcpFlags", result.get("tcp_flags"))

        return api_log

    def after_send_failure(self):
        self._reset_log_metrics()

    def after_send(self):
        self._log_metrics()
        self._emit_anomaly()

    def _log_metrics(self):
        self._log.info(
            (
                "events passed through the monitoring scopes: {0}, "
                "events filtered out: {1}, invalid events: {2}"
            ).format(self.in_scope, self.out_scope, self.invalid_events)
        )

        if self.out_scope > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageOutOfScope())

        if self.invalid_events > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageInvalidLogs())

        if self.invalid_sample:
            self._log.warn("invalid dest ip sample: {0}".format(self.invalid_sample))

        self._reset_log_metrics()

    def _reset_log_metrics(self):
        self.in_scope = 0
        self.out_scope = 0

        self.invalid_sample = set()
        self.invalid_events = 0

    def _emit_anomaly(self):
        anomaly_emmited = self.anomaly.emit()
        if anomaly_emmited > 0:
            self._log.info("emitted anomaly events: %s" % anomaly_emmited)


def save_data_messages(log, session_key):
    config = confs.Config(session_key, stanza=sections.IP.name)
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
        sendlog_config = sendlog.Config(sections.IP.name)
        sendlog_ip = SendlogIP(sendlog_config, session_key, log)
        log.info("sendlog created")

        sendlog_ip.run()
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
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "sendlog_ip")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())

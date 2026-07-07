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

from nbalib.asoc3 import six

TLS_SENDLOG_SCRIPT_FILES = (
    "script://./bin/nba_sendlog_tls.py",
    "script://.\\bin\\nba_sendlog_tls.py",
)

class SendlogTLS(sendlog.Sendlog):
    def __init__(self, config, session_key, log):
        super(SendlogTLS, self).__init__(config, session_key, log)
        self.anomaly = anomaly.Anomaly(config.section)

        self.in_scope = 0
        self.out_scope = 0
        self.invalid_events = 0

    def get_query(self):
        tags = 'tag="certificate"'
        logs_index = self.get_logs_index('nbalogsindextls')
        timeranges = self.format_timeranges()

        return (
            '| prjob num_of_reducers=0 [search {0} {1} {2} _indextime > {3} _indextime <= {4} '
            '| eval src_ip = if(isnull(src_ip), src, src_ip) '
            '| eval src_host = if(isnull(src_host), src_nt_host, src_host) '
            '| eval src_user = if(isnull(src_user), user, src_user) '
            '| eval dest_ip = if(isnull(dest_ip), dest, dest_ip) '
            '| eval time = strftime(_time, "%Y-%m-%dT%H:%M:%S%z") '
            '| eval ssl_start_time = strftime(ssl_start_time, "%Y-%m-%dT%H:%M:%S%z") '
            '| eval ssl_end_time = strftime(ssl_end_time, "%Y-%m-%dT%H:%M:%S%z") '
            '| table _indextime, time, src_ip, src_port, src_host, src_mac, src_user, dest_ip, dest_port, '
            'ssl_hash, ssl_cert_sha1, ssl_issuer, ssl_subject, ssl_start_time, ssl_end_time, ja3, ja3s]'
        ).format(logs_index, tags, timeranges, self.period.start, self.period.end)

    def parse_indextime(self, result):
        return self.get_indextime(result.get('_indextime'))

    def parse_result(self, result):
        dest_ip = result.get('dest_ip', '')
        src_ip = result.get('src_ip', '')
        cert_hash = self._get_cert_hash(result.get('ssl_hash'), result.get('ssl_cert_sha1'))

        if not src_ip:
            self.invalid_events += 1
            return None

        dest_ip = validators.IP.full_valid_ip(dest_ip)
        scope_groups = self.scope.in_scope(src_ip, dest_ip=dest_ip)
        if not scope_groups:
            self.out_scope += 1
            return None

        self.in_scope += 1
        api_log = self._create_api_log(src_ip, cert_hash, result)

        try:
            self.anomaly.detect(api_log.content, scope_groups, self.scope)
        except Exception as exc:
            self._log.warn('could not detect anomaly: {0}'.format(repr(exc)))

        return api_log.content

    @staticmethod
    def _get_cert_hash(cert_hash, cert_hash_sha1):
        if isinstance(cert_hash, six.string_types) and len(cert_hash) == 40:
            return cert_hash

        if isinstance(cert_hash_sha1, six.string_types) and len(cert_hash_sha1) == 40:
            return cert_hash_sha1

        return cert_hash

    @staticmethod
    def _create_api_log(src_ip, cert_hash, result):
        api_log = sendlog.APILog()

        api_log.set('ts', result.get('time', ''))
        api_log.set('srcIP', src_ip)

        api_log.set_integer('srcPort', result.get('src_port'))
        api_log.set_non_empty('srcHost', result.get('src_host'))
        api_log.set_non_empty('srcMac', result.get('src_mac'))
        api_log.set_non_empty('srcUser', result.get('src_user'))

        api_log.set_ip('destIP', result.get('dest_ip'))
        api_log.set_integer('destPort', result.get('dest_port'))

        api_log.set_non_empty('certHash', cert_hash)
        api_log.set_non_empty('ja3', result.get('ja3'))
        api_log.set_non_empty('ja3s', result.get('ja3s'))

        api_log.set_non_empty('issuer', result.get('ssl_issuer'))
        api_log.set_non_empty('subject', result.get('ssl_subject'))

        api_log.set_non_empty('validFrom', result.get('ssl_start_time'))
        api_log.set_non_empty('validTo', result.get('ssl_end_time'))

        return api_log

    def after_send_failure(self):
        self._reset_log_metrics()

    def after_send(self):
        self._log_metrics()
        self._emit_anomaly()

    def _log_metrics(self):
        self._log.info((
            "events passed through the monitoring scopes: {0}, "
            "events filtered out: {1}, invalid events: {2}"
        ).format(self.in_scope, self.out_scope, self.invalid_events))

        if self.out_scope > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageOutOfScope())

        if self.invalid_events > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageInvalidLogs())

        self._reset_log_metrics()

    def _reset_log_metrics(self):
        self.in_scope = 0
        self.out_scope = 0
        self.invalid_events = 0

    def _emit_anomaly(self):
        anomaly_emmited = self.anomaly.emit()
        if anomaly_emmited > 0:
            self._log.info("emitted anomaly events: %s" % anomaly_emmited)


def save_data_messages(log, session_key):
    config = confs.Config(session_key, stanza=sections.TLS.name)
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
        sendlog_config = sendlog.Config(sections.TLS.name, script_paths=TLS_SENDLOG_SCRIPT_FILES)
        sendlog_tls = SendlogTLS(sendlog_config, session_key, log)
        log.info("sendlog created")

        sendlog_tls.run()
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
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "sendlog_tls")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())

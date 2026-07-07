import sys
import traceback
import re

import splunk.auth

from nbalib import sections
from nbalib import sendlog
from nbalib import logger
from nbalib import anomaly
from nbalib import confs
from nbalib import api
from nbalib import validators

from nbalib.asoc3 import six

MAX_INVALID_SAMPLE_ITEMS = 20
INVALID_QTYPE_THRESHOLD = 0.1

class SendlogDNS(sendlog.Sendlog):
    def __init__(self, config, session_key, log):
        super(SendlogDNS, self).__init__(config, session_key, log)
        self.anomaly = anomaly.Anomaly(config.section)

        self.in_scope = 0
        self.out_scope = 0

        self.invalid_sample = set()
        self.invalid_events = 0
        self.invalid_qtype = 0

    def get_query(self):
        tags = 'tag="dns" tag="network" tag="resolution"'
        logs_index = self.get_logs_index('nbalogsindexdns')
        timeranges = self.format_timeranges()

        return (
            '| prjob num_of_reducers=0 [search {0} {1} {2} _indextime > {3} _indextime <= {4} '
            '| eval src_ip = if(isnull(src_ip), src, src_ip) '
            '| eval src_host = if(isnull(src_host), src_nt_host, src_host) '
            '| eval src_user = if(isnull(src_user), user, src_user) '
            '| eval record_type = if(isnull(record_type), questiontype, record_type) '
            '| eval reply_code = if(isnull(reply_code), reply_code_id, reply_code) '
            '| eval time = strftime(_time, "%Y-%m-%dT%H:%M:%S%z") '
            '| table _indextime, time, src_ip, src_port, src_host, src_mac, src_user, '
            'query, record_type, reply_code]'
        ).format(logs_index, tags, timeranges, self.period.start, self.period.end)

    def parse_indextime(self, result):
        return self.get_indextime(result.get('_indextime'))

    def parse_result(self, result):
        query = result.get('query', '')
        src_ip = result.get('src_ip', '')

        if not query or not src_ip:
            self.invalid_events += 1
            return None

        query = self.convert_from_ms_format(query)
        scope_groups = self.scope.in_scope(src_ip, fqdn=query)
        if not scope_groups:
            self.out_scope += 1
            return None

        if not validators.FQDN.is_valid_api(query):
            self.add_invalid_sample(query)
            self.invalid_events += 1
            return None

        self.in_scope += 1
        api_log = self._create_api_log(src_ip, query, result)

        try:
            self.validate_optional_fields(result)
        except Exception as exc:
            self._log.warn('unable to validate optional fields: {0}'.format(repr(exc)))

        try:
            self.anomaly.detect(api_log.content, scope_groups, self.scope)
        except Exception as exc:
            self._log.warn('could not detect anomaly: {0}'.format(repr(exc)))

        return api_log.content

    @staticmethod
    def convert_from_ms_format(query):
        if not isinstance(query, six.string_types):
            return query

        if query.startswith('(') and query.endswith(')'):
            query = re.sub(r'\(\d+\)', ".", query)

        return query.strip('.').lower()

    def add_invalid_sample(self, query):
        if len(self.invalid_sample) < MAX_INVALID_SAMPLE_ITEMS:
            self.invalid_sample.add(query)

    @staticmethod
    def _create_api_log(src_ip, query, result):
        api_log = sendlog.APILog()

        api_log.set('ts', result.get('time', ''))
        api_log.set('query', query)
        api_log.set('srcIP', src_ip)

        api_log.set_integer('srcPort', result.get('src_port'))
        api_log.set_non_empty('srcHost', result.get('src_host'))
        api_log.set_non_empty('srcMac', result.get('src_mac'))
        api_log.set_non_empty('srcUser', result.get('src_user'))

        api_log.set_non_empty('qtype', result.get('record_type'))
        api_log.set_non_empty('rcode', result.get('reply_code'))

        return api_log

    def validate_optional_fields(self, result):
        if not validators.RecordType.is_valid(result.get('record_type', '')):
            self.invalid_qtype += 1

    def after_send_failure(self):
        self._reset_log_metrics()

    def after_send(self):
        self._log_metrics()
        self._emit_anomaly()

    def _log_metrics(self):
        self._log.info((
            "events passed through the monitoring scopes: {0}, "
            "events filtered out: {1}, invalid events: {2}, invalid record type: {3}"
        ).format(self.in_scope, self.out_scope, self.invalid_events, self.invalid_qtype))

        if self.out_scope > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageOutOfScope())

        if self.invalid_events > 0 and self.in_scope == 0:
            self._log.ui_append(logger.MessageInvalidLogs())

        if self._invalid_qtype_above_threshold():
            self._log.ui_append(logger.MessageInvalidRecordType())

        if self.invalid_sample:
            self._log.warn("invalid fqdns sample: {0}".format(self.invalid_sample))

        self._reset_log_metrics()

    def _reset_log_metrics(self):
        self.in_scope = 0
        self.out_scope = 0

        self.invalid_sample = set()
        self.invalid_events = 0
        self.invalid_qtype = 0

    def _emit_anomaly(self):
        anomaly_emmited = self.anomaly.emit()
        if anomaly_emmited > 0:
            self._log.info("emitted anomaly events: %s" % anomaly_emmited)

    def _invalid_qtype_above_threshold(self):
        if self.in_scope <= 0:
            return False

        return self.invalid_qtype / float(self.in_scope) >= INVALID_QTYPE_THRESHOLD

def save_data_messages(log, session_key):
    config = confs.Config(session_key, stanza=sections.DNS.name)
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
        sendlog_config = sendlog.Config(sections.DNS.name)
        sendlog_dns = SendlogDNS(sendlog_config, session_key, log)
        log.info("sendlog created")

        sendlog_dns.run()
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
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "sendlog_dns")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())

import sys
import traceback

import splunk.auth

from nbalib import datatypes
from nbalib import sections
from nbalib import sendlog
from nbalib import logger
from nbalib import anomaly
from nbalib import confs
from nbalib import api

MAX_INVALID_SAMPLE_ITEMS = 20


class SendlogHTTP(sendlog.Sendlog):
    def __init__(self, config, session_key, log):
        super(SendlogHTTP, self).__init__(config, session_key, log)
        self.anomaly = anomaly.Anomaly(config.section)

        self.in_scope = 0
        self.out_scope = 0

        self.invalid_sample = set()
        self.invalid_events = 0

    def get_query(self):
        tags = 'tag="web"'
        logs_index = self.get_logs_index('nbalogsindexhttp')
        timeranges = self.format_timeranges()

        return (
            '| prjob num_of_reducers=0 [search {0} {1} {2} _indextime > {3} _indextime <= {4} '
            '| eval src_ip = if(isnull(src_ip), src, src_ip) '
            '| eval src_host = if(isnull(src_host), src_nt_host, src_host) '
            '| eval src_user = if(isnull(src_user), user, src_user) '
            '| eval url = if(isnull(url), site, url) '
            '| eval bytes_out = if(isnull(bytes_out), bytes, bytes_out) '
            '| eval http_referrer = if(isnull(http_referrer), http_referer, http_referrer) '
            '| eval time = strftime(_time, "%Y-%m-%dT%H:%M:%S%z") '
            '| table _indextime, time, src_ip, src_port, src_host, src_mac, src_user, url, '
            'app, action, status, bytes_in, bytes_out, http_content_type, http_method, '
            'http_referrer, http_user_agent]'
        ).format(logs_index, tags, timeranges, self.period.start, self.period.end)

    def parse_indextime(self, result):
        return self.get_indextime(result.get('_indextime'))

    def parse_result(self, result):
        src_ip = result.get('src_ip', '')
        url = result.get('url', '')

        if not src_ip or not url:
            self.invalid_events += 1
            return None

        parsed_url = datatypes.URL(url)
        if not parsed_url.is_valid:
            self.add_invalid_sample(url)
            self.invalid_events += 1
            return None

        scope_groups = self._get_scope_groups(src_ip, parsed_url)
        if not scope_groups:
            self.out_scope += 1
            return None

        self.in_scope += 1
        api_log = self._create_api_log(src_ip, parsed_url, result)

        try:
            self.anomaly.detect(api_log.content, scope_groups, self.scope, dest_is_ip=parsed_url.is_ip)
        except Exception as exc:
            self._log.warn('could not detect anomaly: {0}'.format(repr(exc)))

        return api_log.content

    def _get_scope_groups(self, src_ip, parsed_url):
        if parsed_url.is_ip:
            return self.scope.in_scope(src_ip, dest_ip=parsed_url.hostname)

        return self.scope.in_scope(src_ip, fqdn=parsed_url.hostname)

    @staticmethod
    def _create_api_log(src_ip, parsed_url, result):
        api_log = sendlog.APILog()

        api_log.set('ts', result.get('time', ''))
        api_log.set('url', parsed_url.get_cleaned_url())
        api_log.set('srcIP', src_ip)

        api_log.set_integer('srcPort', result.get('src_port'))
        api_log.set_non_empty('srcHost', result.get('src_host'))
        api_log.set_non_empty('srcMac', result.get('src_mac'))
        api_log.set_non_empty('srcUser', result.get('src_user'))

        api_log.set_non_empty('app', result.get('app'))
        api_log.set_non_empty_lower('action', result.get('action'))
        api_log.set_non_empty_lower('method', result.get('http_method'))

        api_log.set_non_empty('contentType', result.get('http_content_type'))
        api_log.set_non_empty('userAgent', result.get('http_user_agent'))

        referrer_url = datatypes.URL(result.get('http_referrer'))
        api_log.set_non_empty('referrer', referrer_url.get_cleaned_url())

        api_log.set_integer('status', result.get('status'))
        api_log.set_integer('bytesIn', result.get('bytes_in'))
        api_log.set_integer('bytesOut', result.get('bytes_out'))

        return api_log

    def add_invalid_sample(self, url):
        if len(self.invalid_sample) < MAX_INVALID_SAMPLE_ITEMS:
            self.invalid_sample.add(url)

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

        if self.invalid_sample:
            self._log.warn("invalid url sample: {0}".format(self.invalid_sample))

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
    config = confs.Config(session_key, stanza=sections.HTTP.name)
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
        sendlog_config = sendlog.Config(sections.HTTP.name)
        sendlog_http = SendlogHTTP(sendlog_config, session_key, log)
        log.info("sendlog created")

        sendlog_http.run()
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
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "sendlog_http")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())

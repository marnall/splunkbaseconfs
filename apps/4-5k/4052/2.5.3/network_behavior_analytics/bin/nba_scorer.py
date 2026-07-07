import sys
import traceback
import time
import json

import splunk.auth

from nbalib.stores import threatstore, flagstore, mitrestore
from nbalib import sections
from nbalib import dateasoc
from nbalib import anomaly
from nbalib import logger
from nbalib import alerts
from nbalib import confs
from nbalib import api
from nbalib import scopes


class Scorer(object):
    """
    Scorer recives alerts from AlphaSOC API. Every response can
    contains a new follow value which must be saved in main app config.
    It is used to define which alerts was already fetched from the API.
    """

    def __init__(self, session_key, log, config_name=None):
        self._session_key = session_key
        self._log = log

        self.app_config = confs.Config(self._session_key, name=config_name, stanza=sections.Alerts.name)

        self.runtime_health_check()
        self.apply_initial_api_key()

        self.api_key = self.authorize()

    def apply_initial_api_key(self):
        try:
            initial_api_key = self.app_config.get_from_stanza('initial_api_key', stanza=sections.NBA.stanza)
            if initial_api_key:
                api.ApiKeyStorage.save(initial_api_key, self._session_key)
                self.app_config.set_in_stanza('initial_api_key', "", stanza=sections.NBA.stanza)

                self._log.info("initial api key has been applied")
        except Exception as exc:
            self._log.error('unable to save initial api key: {0}'.format(str(exc)))

    def retrieve(self):
        """
        Retrive alerts from API. Do it in a loop to support API pagination.
        API key need to be authorized already and then make at least one query (more_alerts = True).
        When response is ready, save new follow and print events to the splunk index.
        """

        master_node = self.is_master_node()
        if not master_node:
            return

        self.scope_api_export()

        received_counter = 0
        emmited_counter = 0
        more_alerts = True

        while more_alerts is True:
            current_follow, follow_type = self.get_current_follow()
            response = self.fetch_api_alerts(current_follow)

            alerts_batch = self.format_alerts(response.alerts, response.threats)
            emmited_counter += self.emit_alerts(alerts_batch)

            received_counter += len(response.alerts)
            more_alerts = response.more

            self.save_new_follow(response.follow, follow_type)

            if more_alerts is True:
                self._log.info("results were truncated, make additional call to the api")

        self._log.info("retrived alerts: {0}, emmited alerts: {1}".format(received_counter, emmited_counter))
        if received_counter > 0 and received_counter - emmited_counter > 0:
            self._log.ui_append(logger.MessageInvalidAlerts())

    def runtime_health_check(self):
        self.app_config.set('last_runtime', int(time.time()))

    def authorize(self):
        auth = api.Auth(self._session_key)
        account_details = auth.account_status(self.app_config, check_master_node=False)
        self.print_endpoints_stats(account_details.licensing)

        return account_details.api_key

    def print_endpoints_stats(self, details):
        try:
            if details.today is None or details.endpoints_seen_today is None:
                return

            event = {}
            event['type'] = 'stats_endpoints'
            event['ts'] = dateasoc.date_to_string(dateasoc.iso8601_to_date(details.today))
            event['unique_endpoints'] = details.endpoints_seen_today

            event_json = json.dumps(event, separators=(', ', ':'))
            print(event_json)
        except Exception as exc:
            self._log.warn('could not format stats_endpoints event: {0}'.format(str(exc)))

    def is_master_node(self):
        return self.app_config.is_enabled('master_node', stanza=sections.NBA.stanza)

    def get_current_follow(self):
        on_premise = self.app_config.is_enabled('api_on_premise', stanza=sections.NBA.stanza)

        follow_type = "follow_cim_on_premise" if on_premise else "follow_cim"
        follow_value = self.app_config.get(follow_type, "")

        self._log.info('got current {0} value: {1}'.format(follow_type, follow_value))

        return follow_value, follow_type

    def save_new_follow(self, follow, follow_type):
        if follow:
            self.app_config.set(follow_type, follow)
            self._log.info('new {0} value set to: {1}'.format(follow_type, follow))

    def fetch_api_alerts(self, follow):
        alphasoc_api = api.API(self._session_key)
        result = alphasoc_api.alerts(self.api_key, follow)

        if result.has_error():
            self._log.error('could not fetch alerts from api: {0}'.format(result.error))
            self._log.ui_append(logger.MessageAPIConnection(result.code))

        return result

    def format_alerts(self, api_alerts, threats):
        alerts_batch = alerts.Batch(threats=threats)

        for api_alert in api_alerts:
            try:
                alerts_batch.add(api_alert)
            except Exception as exc:
                self._log.error(str(exc))

        return alerts_batch

    def emit_alerts(self, alerts_batch):
        emmited_counter = 0
        alerts_batch.sort()

        for alert in alerts_batch:
            try:
                print(alert.dumps())
                emmited_counter += 1
            except Exception as exc:
                self._log.error(repr(exc))

        return emmited_counter

    def update_threats(self):
        alphasoc_api = api.API(self._session_key)
        result = alphasoc_api.inventory_threats(self.api_key)

        if result.has_error():
            self._log.error('could not fetch threats definitons from api: {0}'.format(result.error))
            self._log.ui_append(logger.MessageStoreNotUpdated())
            return

        try:
            self._store_threats(result.threats)
        except Exception as exc:
            self._log.error("unable to update threats store: {0}".format(repr(exc)))
            self._log.ui_append(logger.MessageStoreNotUpdated())

    def _store_threats(self, threats):
        if not isinstance(threats, dict):
            raise ValueError("threats dictionary has invalid format: {0}".format(threats))

        if not threats:
            return

        threats = anomaly.AnomalyThreat.append_to_threats(threats)
        ts = threatstore.ThreatStore(self._session_key)
        ts.replace(threats)

        self._log.info("threats definitions updated: {0}".format(len(threats)))

    def update_flags(self):
        alphasoc_api = api.API(self._session_key)
        result = alphasoc_api.inventory_flags(self.api_key)

        if result.has_error():
            self._log.error('could not fetch flags definitons from api: {0}'.format(result.error))
            self._log.ui_append(logger.MessageStoreNotUpdated())
            return

        try:
            self._store_flags(result.flags)
        except Exception as exc:
            self._log.error("unable to update flags store: {0}".format(repr(exc)))
            self._log.ui_append(logger.MessageStoreNotUpdated())

    def _store_flags(self, flags):
        if not isinstance(flags, dict):
            raise ValueError("flags dictionary has invalid format: {0}".format(flags))

        if not flags:
            return

        flags = anomaly.AnomalyFlag.append_to_flags(flags)
        fs = flagstore.FlagStore(self._session_key)
        fs.replace(flags)

        self._log.info("flags definitions updated: {0}".format(len(flags)))

    def update_mitre(self):
        alphasoc_api = api.API(self._session_key)

        # Update MITRE ATT&CK tactics
        result = alphasoc_api.inventory_mitre_tactics(self.api_key)
        if result.has_error():
            self._log.error('could not fetch MITRE ATT&CK tactics from api: {0}'.format(result.error))
            self._log.ui_append(logger.MessageStoreNotUpdated())
            return

        try:
            self._store_mitre_tactics(result.tactics)
        except Exception as exc:
            self._log.error("unable to update MITRE ATT&CK tactics store: {0}".format(repr(exc)))
            self._log.ui_append(logger.MessageStoreNotUpdated())

        # Update MITRE ATT&CK techniques
        result = alphasoc_api.inventory_mitre_techniques(self.api_key)
        if result.has_error():
            self._log.error('could not fetch MITRE ATT&CK techniques from api: {0}'.format(result.error))
            self._log.ui_append(logger.MessageStoreNotUpdated())
            return

        try:
            self._store_mitre_techniques(result.techniques)
        except Exception as exc:
            self._log.error("unable to update MITRE ATT&CK techniques store: {0}".format(repr(exc)))
            self._log.ui_append(logger.MessageStoreNotUpdated())

        # Update MITRE ATT&CK matrix
        result = alphasoc_api.inventory_mitre_matrix(self.api_key)
        if result.has_error():
            self._log.error('could not fetch MITRE ATT&CK matrix from api: {0}'.format(result.error))
            self._log.ui_append(logger.MessageStoreNotUpdated())
            return

        try:
            self._store_mitre_matrix(result.matrix)
        except Exception as exc:
            self._log.error("unable to update MITRE ATT&CK matrix store: {0}".format(repr(exc)))
            self._log.ui_append(logger.MessageStoreNotUpdated())

    def _store_mitre_tactics(self, tactics):
        if not isinstance(tactics, list):
            raise ValueError("tactics list has invalid format: {0}".format(tactics))

        if not tactics:
            return

        ms = mitrestore.TacticStore(self._session_key)
        ms.replace(tactics)

        self._log.info("mitre tactics definitions updated: {0}".format(len(tactics)))

    def _store_mitre_techniques(self, techniques):
        if not isinstance(techniques, list):
            raise ValueError("techniques list has invalid format: {0}".format(techniques))

        if not techniques:
            return

        ms = mitrestore.TechniqueStore(self._session_key)
        ms.replace(techniques)

        self._log.info("mitre techniques definitions updated: {0}".format(len(techniques)))

    def _store_mitre_matrix(self, matrix):
        if not isinstance(matrix, list):
            raise ValueError("matrix list has invalid format: {0}".format(matrix))

        if not matrix:
            return

        ms = mitrestore.MatrixStore(self._session_key)
        ms.replace(matrix)

        self._log.info("mitre matrix definitions updated: {0}".format(len(matrix)))

    def sync_settings(self):
        self._sync_source_display()

    def _sync_source_display(self):
        try:
            alerts.SourceDisplayStorage(self._session_key).sync()
        except Exception as exc:
            self._log.error("unable to sync source display option: {0}".format(repr(exc)))

        self._log.info("source display option synced")

    def scope_api_export(self):
        try:
            exported = self.app_config.is_enabled('scope_api_exported', stanza=sections.NBA.stanza)
            if exported:
                return

            scope = scopes.Scope()
            alphasoc_api = api.API(self._session_key)
            response = alphasoc_api.groups_raw_post(self.api_key, scope.json_dump())

            if response.has_error():
                self._log.error('sending monitoring scope to api: {0}'.format(response.error))
                return

            self.app_config.set_in_stanza('scope_api_exported', True, stanza=sections.NBA.stanza)
            self._log.info('monitoring scope exported to api')
        except Exception as exc:
            self._log.error("exporting monitoring scope: {0}".format(repr(exc)))

    def migrate(self):
        self.migrate_scopes_remove_arpa()

    def migrate_scopes_remove_arpa(self):
        try:
            migrated = self.app_config.is_enabled('scopes_remove_arpa', stanza=sections.NBA.migration_stanza)
            if migrated:
                return

            scope = scopes.Scope()
            for group in scope.groups_list():
                scope.entry_remove(group, scopes.EntryType.TRUSTED_DOMAINS, "*.arpa")
            scope.save()

            self.app_config.set_in_stanza('scopes_remove_arpa', True, stanza=sections.NBA.migration_stanza)
            self._log.info('migration done; arpa removed from monitoring scope')
        except Exception as exc:
            self._log.error("migration; removing arpa from monitoring scope: {0}".format(repr(exc)))


def main(log):
    log.info("--- scorer start")

    # If the script is called by splunk, session key is passed in stdin
    if len(sys.argv) > 1:
        session_key = splunk.auth.getSessionKey(sys.argv[1], sys.argv[2])
    else:
        session_key = sys.stdin.readline()
    log.info("got session key")

    try:
        scorer = Scorer(session_key, log)
        log.info("scorer created")

        scorer.retrieve()
        scorer.update_threats()
        scorer.update_flags()
        scorer.update_mitre()
        scorer.sync_settings()

        scorer.migrate()
    except api.MasterNodeError as exc:
        log.warn(repr(exc))
    except api.AuthError as exc:
        log.warn(repr(exc))
        log.ui_append(logger.MessageUnauthorizedAPI(exc.api_messages))
    except confs.PerrmisionException as exc:
        log.error(repr(exc))
        log.ui_append(logger.MessageUnauthorizedSplunk())
    except Exception as exc:
        log.error(repr(exc))
        log.error(traceback.format_exc())
        log.ui_append(logger.MessageUnexpectedError(repr(exc)))
    finally:
        config = confs.Config(session_key, stanza=sections.Alerts.name)
        log.ui_save(config)

    log.info("scorer exit")


if __name__ == "__main__":
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "scorer")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())

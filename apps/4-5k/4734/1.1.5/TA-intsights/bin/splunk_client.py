"""Splunk client class."""
import json
import splunk.entity
import splunklib.client as client
import splunklib.results as results
from splunklib.binding import AuthenticationError

SOURCE_TO_PUSH_TO = "intsights_alerts"
SEARCH_QUERY = "search source={}".format(SOURCE_TO_PUSH_TO)


class SplunkConnector:
    """Splunk client connector class."""

    def __init__(self, session_key, app_name, logger):
        """Splunk client connector class init."""
        self._s = self._connect(session_key, app_name)
        self._logger = logger

    def _connect(self, session_key, app_name):
        try:
            return client.connect(
                host='localhost',
                port=8089,
                token=session_key,
                owner="nobody",
                app=app_name
            )

        except AuthenticationError:
            self._logger.error("Unable to authenticate user on Splunk")
        self._logger.debug("User successfully Logged in...")


class SplunkClient:
    """Splunk client class."""

    def __init__(self, session_key, app_name, conf_name, stanza_name, logger):
        """Splunk client connector class init."""
        self._session_key = session_key
        self._app_name = app_name
        self._conf_name = conf_name
        self._stanza_name = stanza_name
        self._service = SplunkConnector(session_key, app_name, logger)
        self._logger = logger
        self._logger.debug("Created Splunk Client for " + stanza_name)

    def get_alerts(self):
        """Splunk client connector class get alerts."""
        alerts = set()
        rr = results.ResultsReader(self._service._s.jobs.export(SEARCH_QUERY))
        for result in rr:
            try:
                if isinstance(result, dict):
                    alert_id = json.loads(result.get('_raw'))['_id']
                    alerts.add(alert_id)
            except Exception:
                continue

        return alerts

    def push_alerts(self, complete_alerts):
        """Splunk client connector class push alerts."""
        target = self._service._s.indexes['main']
        for json_object in complete_alerts:
            try:
                target.submit(
                    event=json.dumps(json_object),
                    sourcetype="_json",
                    source=SOURCE_TO_PUSH_TO
                )

            except Exception:
                continue

    def get_intsights_creds(self, account_type):
        """Splunk client connector class get intsights creds."""
        try:
            self._logger.info("Looking for entity: {}-{}".format(self._app_name, account_type))
            entities = splunk.entity.getEntities(
                ['admin', 'passwords'],
                namespace=self._app_name,
                owner='nobody',
                sessionKey=self._session_key,
                search="{}-{}".format(self._app_name, account_type)
            )

            if entities:
                for title in entities:
                    if entities[title].get("realm") == "{}-{}".format(self._app_name, account_type):
                        return entities[title]['username'], entities[title]['clear_password']
            else:
                self._logger.error("Could not get entity: {}-{}".format(self._app_name, account_type))
                return None, None

        except Exception as e:
            raise Exception("Could not get {} credentials from splunk. Error: {}".format(self._app_name, e))

    def get_proxy_creds(self):
        """Splunk client connector class get intsights creds."""
        try:
            entities = splunk.entity.getEntities(
                ['admin', 'passwords'],
                namespace=self._app_name,
                owner='nobody',
                sessionKey=self._session_key,
                search="{}-proxy".format(self._app_name)
            )

            if entities:
                for title in entities:
                    if entities[title].get("realm") == "{}-proxy".format(self._app_name):
                        return entities[title]['username'], entities[title]['clear_password']
            else:
                return None, None

        except Exception as e:
            raise Exception("Could not get {} proxy credentials from splunk. Error: {}".format(self._app_name, e))

    def get_proxy_address(self):
        """Splunk client connector class get proxy address."""
        proxy_address = None
        try:

            entity = splunk.entity.getEntity(
                '/admin/conf-{}'.format(self._conf_name),
                self._stanza_name,
                namespace=self._app_name,
                sessionKey=self._session_key,
                owner='nobody',
            )

            try:
                proxy_address = entity.get('intsights-HTTPS_PROXY_ADDRESS')

                if(proxy_address is not None and len(proxy_address) > 0):
                    self._logger.debug("User request proxy...")
                    return proxy_address
                else:
                    self._logger.debug("No proxy present...")
                    return None
            except Exception as ex:
                self._logger.debug("Exception getting entity...")
                self._logger.debug(ex)
                return None

        except Exception as ex:
            self._logger.debug("Exception requesting proxy address...")
            self._logger.debug(ex)
            return None

    def feed_ingestion_enabled(self):
        """Splunk client connector class alerts ingestion enabled."""
        saved_feed_ingestion_enabled = {}
        try:
            entity = splunk.entity.getEntity(
                '/admin/conf-{}'.format(self._conf_name),
                self._stanza_name,
                namespace=self._app_name,
                sessionKey=self._session_key,
                owner='nobody'
            )
        except Exception as e:
            self._logger.error("Could not get {} threat feed flags from splunk. Error: {}".format(self._app_name, str(e)))
            raise Exception("Could not get {} threat feed flags from splunk. Error: {}".format(self._app_name, str(e)))

        try:
            self._logger.debug("enabled_feeds says: " + str(int(entity.get('enabled_feeds'))))
            saved_feed_ingestion_enabled["enabled_feeds"] = int(entity.get('enabled_feeds'))
        except Exception:
            self._logger.debug("enabled_feeds failed to get entities..." + '/admin/conf-{}'.format(self._conf_name))
            saved_feed_ingestion_enabled["enabled_feeds"] = None

        try:
            self._logger.debug("enabled_documents says: " + str(int(entity.get('enabled_documents'))))
            saved_feed_ingestion_enabled["enabled_documents"] = int(entity.get('enabled_documents'))

        except Exception:
            self._logger.debug("enabled_documents failed to get entities..." + '/admin/conf-{}'.format(self._conf_name))
            saved_feed_ingestion_enabled["enabled_documents"] = None

        try:
            self._logger.debug("enabled_emails says: " + str(int(entity.get('enabled_emails'))))
            saved_feed_ingestion_enabled["enabled_emails"] = int(entity.get('enabled_emails'))

        except Exception:
            self._logger.debug("enabled_emails failed to get entities..." + '/admin/conf-{}'.format(self._conf_name))
            saved_feed_ingestion_enabled["enabled_emails"] = None

        if(len(saved_feed_ingestion_enabled) > 0):
            return saved_feed_ingestion_enabled
        else:
            return None

    def alerts_ingestion_enabled(self):
        """Splunk client connector class alerts ingestion enabled."""
        try:
            entity = splunk.entity.getEntity(
                '/admin/conf-{}'.format(self._conf_name),
                self._stanza_name,
                namespace=self._app_name,
                sessionKey=self._session_key,
                owner='nobody'
            )

        except Exception as e:
            self._logger.error("Could not get {} alert ingestion flag from splunk. Error: {}".format(self._app_name, str(e)))
            raise Exception("Could not get {} alert ingestion flag from splunk. Error: {}".format(self._app_name, str(e)))

        try:
            self._logger.debug("alerts_ingestion_enabled says: " + str(int(entity.get('is_ingest_alerts'))))
            return int(entity.get('is_ingest_alerts'))

        except Exception:
            self._logger.debug("alerts_ingestion_enabled failed to get entities..." + '/admin/conf-{}'.format(self._conf_name))
            return None

    def get_ioc_filters(self):
        """Splunk client connector class get ioc filters."""
        filters = []
        try:
            a_filter = {}
            entity = splunk.entity.getEntity(
                '/admin/conf-{}'.format(self._conf_name),
                self._stanza_name,
                namespace=self._app_name,
                sessionKey=self._session_key,
                owner='nobody'
            )

            default_weeks = 26
            try:
                weeks = int(entity.get('weeks'))
            except:
                weeks = default_weeks

            if weeks:
                if weeks > default_weeks:
                    a_filter['weeks'] = default_weeks
                else:
                    a_filter['weeks'] = weeks
            else:
                a_filter['weeks'] = default_weeks

            sources_csv = entity.get('sources')
            if sources_csv:
                a_filter['sources'] = [item.lower().strip() for item in sources_csv.split(',')]
            else:
                a_filter['sources'] = []

            severities_csv = entity.get('severities')
            if severities_csv:
                a_filter['severities'] = [item.lower().strip() for item in severities_csv.split(',')]
            else:
                a_filter['severities'] = []

            types_csv = entity.get('types')
            if types_csv:
                a_filter['types'] = [item.lower().strip() for item in types_csv.split(',')]
            else:
                a_filter['types'] = []

            filters.append(a_filter)

            saved_feed_ingestion_enabled = self.feed_ingestion_enabled()

            if(saved_feed_ingestion_enabled is not None):
                for feed_ingestion_type in saved_feed_ingestion_enabled.keys():
                    if saved_feed_ingestion_enabled[feed_ingestion_type] == 1:
                        a_filter[feed_ingestion_type] = True
                    else:
                        a_filter[feed_ingestion_type] = False
                    filters.append(a_filter)

        except Exception as e:
            raise Exception("Could not get {} ioc filters from splunk. Error: {}".format(self._app_name, str(e)))

        self._logger.debug("User request filters...")

        if len(filters) == 0:
            return [{"sources": [], "severities": [], "types": [], "source types": []}]
        else:
            return filters

    def get_kv_store(self, collection):
        """Splunk client connector class get kv store."""
        try:
            kv_store = client.KVStoreCollectionData(collection)

        except Exception:
            raise Exception("Could not get kv store")

        return kv_store

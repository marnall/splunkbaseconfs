import json
import logging
import os
import re
import time
import traceback

import okta_rest_client as oac
import okta_checkpoint as ock
from splunktalib.common import log, util
from datetime import datetime
from multiprocessing.pool import ThreadPool

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)

THREADS_COUNT = 30

METRICS_INFO = {
    "event": {
        "endpoint": "/api/v1/events",
        "sourcetype": "okta:im",
        "source": "okta:event"
    },
    "user": {
        "endpoint": "/api/v1/users",
        "sourcetype": "okta:im",
        "source": "okta:user"
    },
    "group": {
        "endpoint": "/api/v1/groups",
        "sourcetype": "okta:im",
        "source": "okta:group"
    },
    "application": {
        "endpoint": "/api/v1/apps",
        "sourcetype": "okta:im",
        "source": "okta:app"
    }
}


def get_related_members((obj, endpoint, category, field_name, record)):
    """
    The entrance method to collect related info. Such as:
    get the members of one group,
    get the accessible users/groups of one app.
    This is implemented using global method for teh need of multiple threads.
    :param category: the category of the related member, such as "user", "group".
    :param field_name: the field name of the related info to be set in the record,
                       such as "member", "assigned_users", "assigned_groups"
    """
    rl_members = obj._collect_related_members(endpoint, record.get("id"),
                                              category)
    record[field_name] = rl_members
    return record


class OktaObject(object):
    """
    Okta base object for modular input output
    """

    def __init__(self, record_time, sourcetype, source, data):
        record_time = util.datetime_to_seconds(datetime.strptime(
            record_time, '%Y-%m-%dT%H:%M:%S.%fZ'))
        self.record_time = record_time if record_time else time.time()
        self._data = data
        self._sourcetype = sourcetype
        self._source = source

    def to_string(self, index, host):
        evt_fmt = ("<event><time>{0}</time><source>{1}</source>"
                   "<sourcetype>{2}</sourcetype><host>{3}</host>"
                   "<index>{4}</index><data><![CDATA[ {5} ]]></data></event>")
        data = json.dumps(self._data)
        data = re.sub(r'[\s\r\n]+', " ", data)
        return evt_fmt.format(self.record_time, self._source, self._sourcetype,
                              host, index, data)


class OktaCollector(object):
    """
    The base class of data collector for Okta.
    """

    def __init__(self, config):
        self.config = config
        self._check_exit_handler()
        self._canceled = False

    def _exit_handler(self, signum, frame=None):
        self._canceled = True
        _LOGGER.info("cancellation received. sign num=%s", signum)
        if os.name == 'nt':
            return True

    def _check_exit_handler(self):
        try:
            if os.name == 'nt':
                import win32api
                win32api.SetConsoleCtrlHandler(self._exit_handler, True)
            else:
                import signal
                signal.signal(signal.SIGTERM, self._exit_handler)
                signal.signal(signal.SIGINT, self._exit_handler)
        except Exception as ex:
            _LOGGER.warn("Fail to set signal, skip this step: %s: %s",
                         type(ex).__name__, ex)
            _LOGGER.error(traceback.format_exc())

    def print_stream(self, records, metric):
        metric_info = METRICS_INFO.get(metric.strip().lower())
        source = metric_info.get("source")
        sourcetype = metric_info.get("sourcetype")

        index = self.config.get("index", "default")
        host = self.config.get("url").lower().replace("http://", "").replace(
            "https://", "")
        print "<stream>"
        for record in records:
            if metric == 'event':
                record_time = record["published"]
            else:
                record_time = datetime.utcnow().strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ")
            entry = OktaObject(record_time, sourcetype, source, record)
            print entry.to_string(index, host)
        print "</stream>"

    def _compose_rest_params(self, after_id=None):
        limit = self.config.get("page_size", 1000)
        params = {"limit": limit}
        if after_id:
            params["after"] = after_id
        return params

    def _get_after_id(self, response):
        """
        The method to get the after id in the next page link.
        """
        if response.get("headers"):
            link = response.get("headers").get("link")
            after_pattern = re.compile('\?after=(\w+)&[^;]+;\s*rel="next"')
            if after_pattern.search(link):
                return after_pattern.search(link).groups()[0]
        return None

    def collect_data(self, metric):
        """
        The method to get user/group/app data.
        This method will be overridden for the event data collector.
        """
        (total_count, after_id) = self._do_collect(metric)
        while after_id:
            (count, after_id) = self._do_collect(metric, after_id)
            if count > 0:
                total_count += count
        _LOGGER.info("Totally get %i records for metric %s", total_count,
                     metric)

    def _do_collect(self,metric):
        """
        Implemented in the subclass
        """
        pass

    def _collect_related_members(self, endpoint, id, category):
        """
        The method to collect related members: such as the group member of one groupid,
        the users/groups who are accessible to one app id.
        :param endpoint:
        :param id: group id or  app id
        :param category: the category of the member, such as "user", "group"
        """
        (gp_members, after_id) = self._do_collect_related_members(endpoint, id,
                                                                  category)
        while after_id:
            (members, after_id) = self._do_collect_related_members(
                endpoint, id, category, after_id)
            if members:
                gp_members.extend(members)
        _LOGGER.info("Totally get %i %s assigned to %s", len(gp_members),
                     category, id)
        return gp_members

    def _do_collect_related_members(self, endpoint, id, category, after=None):
        """
        The detail method to collect related members, after id is used to pagination.
        """
        endpoint = endpoint + "/" + id + "/" + category
        response = self._request_response(endpoint, after)
        members = []
        if response.get("content"):
            records = response.get("content")
            for record in records:
                if record.get("id"):
                    members.append(record.get("id"))
            after_id = self._get_after_id(response)
            return (members, after_id)
        _LOGGER.info("No records returned.")
        return (members, None)

    def _request_response(self, endpoint, after):
        params = self._compose_rest_params(after)
        client = oac.OktaRestClient(self.config)
        response = client.request(endpoint, params)
        return response


class OktaEventCollector(OktaCollector):
    """
    This class is for data collection of 'event' metric
    """
    def __init__(self, config):
        super(OktaEventCollector, self).__init__(config)
        self.ckpt = ock.OktaCheckpoint(config)

    def collect_data(self, metric):
        batch_size = self.config.get("batch_size", 10000)
        try:
            batch_size = int(batch_size)
        except:
            _LOGGER.error(
                "Cannot convert Batch Size %s to integer, use 10000 by default.",
                batch_size)
            batch_size = 10000

        total_count = 0
        while total_count < batch_size:
            count = self._do_collect(metric)
            if count > 0:
                total_count += count
            else:
                break
        _LOGGER.info("Totally get %i records for metric %s", total_count,
                     metric)

    def _compose_rest_params(self):
        limit = self.config.get("page_size", 1000)
        params = {"limit": limit}

        if self.ckpt.last_event_id:
            params["after"] = self.ckpt.last_event_id
        else:
            params["filter"] = "published ge \"{}\"".format(self.config.get(
                "start_date"))

        if self.config.get("end_date"):
            end_filter = "published lt \"{}\"".format(self.config.get(
                "end_date"))
            params["filter"] = "{} and {}".format(
                params["filter"],
                end_filter) if params.get("filter") else end_filter
        return params

    def _do_collect(self, metric):
        if self._canceled:
            _LOGGER.info("Stop this data input since splunk exits")
            return None

        self.ckpt.read()
        if self.ckpt.is_end_date_expired():
            _LOGGER.info(
                "Stop this data input since data collection finished by %s",
                self.config.get("end_date"))
            return None

        metric_info = METRICS_INFO.get(metric.strip().lower())
        endpoint = metric_info.get("endpoint")
        params = self._compose_rest_params()
        client = oac.OktaRestClient(self.config)
        response = client.request(endpoint, params)
        if response.get("content"):
            records = response.get("content")
            self.print_stream(records, metric)
            count = len(records)
            _LOGGER.info("Get %i records returned.", count)
            last_event_id = records[-1].get("eventId")
            last_event_date = records[-1].get("published")
            self._write_ckpt(last_event_id, last_event_date)
            return count

        _LOGGER.info("No records returned.")
        return 0

    def _write_ckpt(self, last_event_id, last_event_date):
        self.ckpt.last_event_id = last_event_id
        self.ckpt.last_event_date = last_event_date
        self.ckpt.write()


class OktaUserCollector(OktaCollector):
    """
    This class is for data collection for metric 'user'
    """

    def __init__(self, config):
        super(OktaUserCollector, self).__init__(config)

    def _do_collect(self, metric, after=None):
        if self._canceled:
            _LOGGER.info("Stop this data input since splunk exits")
            return None

        metric_info = METRICS_INFO.get(metric.strip().lower())
        endpoint = metric_info.get("endpoint")

        response = self._request_response(endpoint, after)
        if response.get("content"):
            records = response.get("content")
            self.print_stream(records, metric)
            count = len(records)
            after_id = self._get_after_id(response)
            return (count, after_id)
        _LOGGER.info("No records returned.")
        return (0, None)


class OktaGroupCollector(OktaCollector):
    """
    This class is for data collection of metric 'group'
    """

    def __init__(self, config):
        super(OktaGroupCollector, self).__init__(config)

    def _do_collect(self, metric, after=None):
        if self._canceled:
            _LOGGER.info("Stop this data input since splunk exits")
            return None

        metric_info = METRICS_INFO.get(metric.strip().lower())
        endpoint = metric_info.get("endpoint")

        response = self._request_response(endpoint, after)
        if response.get("content"):
            records = response.get("content")
            pool = ThreadPool(THREADS_COUNT)
            records = pool.map(get_related_members,
                               [(self, endpoint, "users", "members", record)
                                for record in records])
            pool.close()
            pool.join()
            self.print_stream(records, metric)
            count = len(records)
            after_id = self._get_after_id(response)
            return (count, after_id)
        _LOGGER.info("No records returned.")
        return (0, None)


class OktaAppCollector(OktaCollector):
    """
    This class is for data collection of metric 'group'
    """

    def __init__(self, config):
        super(OktaAppCollector, self).__init__(config)

    def _do_collect(self, metric, after=None):
        if self._canceled:
            _LOGGER.info("Stop this data input since splunk exits")
            return None

        metric_info = METRICS_INFO.get(metric.strip().lower())
        endpoint = metric_info.get("endpoint")

        response = self._request_response(endpoint, after)
        if response.get("content"):
            records = response.get("content")
            pool = ThreadPool(THREADS_COUNT)
            records = pool.map(
                get_related_members,
                [(self, endpoint, "users", "assigned_users", record)
                 for record in records])
            pool.close()
            pool.join()
            pool = ThreadPool(THREADS_COUNT)
            records = pool.map(
                get_related_members,
                [(self, endpoint, "groups", "assigned_groups", record)
                 for record in records])
            pool.close()
            pool.join()
            self.print_stream(records, metric)
            count = len(records)
            after_id = self._get_after_id(response)
            return (count, after_id)
        _LOGGER.info("No records returned.")
        return (0, None)


class OktaRefreshToken(OktaCollector):
    """
    This class is for the default data input 'refresh_token',
    which is used to avoid the okta server token configured in the set up page.
    """

    def __init__(self, config):
        super(OktaRefreshToken, self).__init__(config)

    def collect_data(self, metric):
        endpoint = "/api/v1/users/me"
        if self.config.get("okta_server_url", None) and self.config.get(
                "okta_server_token", None):
            client = oac.OktaRestClient(self.config)
            try:
                response = client.request(endpoint=endpoint,
                                          params=None,
                                          themethod="GET",
                                          theurl="okta_server_url",
                                          thetoken="okta_server_token")
            except Exception as ex:
                _LOGGER.warn(
                    "Fail to send request to the global Okta server %s: %s",
                    type(ex).__name__, ex)
            if not response.get("error"):
                _LOGGER.info(
                    "Send request to the global Okta server to refresh the token. The request status is {}.".format(
                        response.get("headers",[]).get("status")))
            return response
        else:
            _LOGGER.info("The global okta server has not been configured.")
            return None

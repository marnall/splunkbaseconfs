#!/usr/bin/env python3

from cbapi import CbPSCBaseAPI as CbApi
from cbapi.response import CbEnterpriseResponseAPI
from cbapi.errors import ApiError, ServerError

from splunklib.searchcommands import GeneratingCommand, Option, Configuration, EventingCommand
import json
import time
import traceback
import os


class CredentialMissingError(Exception):
    pass


try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

def get_creds(splunk_service):
    api_credentials = splunk_service.storage_passwords["credential:DA-ESS-CbResponse_realm:admin:"]

    token = api_credentials.clear_password

    cb_server = splunk_service.confs["DA-ESS-CbResponse_Settings"]["api_info"]['api_url']

    ssl_settings = splunk_service.confs['DA-ESS-CbResponse_Settings']['ssl_info']['ssl_verify']

    ssl_verify = False if ssl_settings == '0' or ssl_settings == 'false' else True

    if not cb_server or not token:
        raise CredentialMissingError(
            "Please visit the Set Up Page for the Cb Response App for Splunk to set the URL and API key for your Cb Response server.")

    return cb_server, token, ssl_verify


def get_legacy_cbapi(splunk_service):
    cb_server, token, ssl_verify = get_creds(splunk_service)
    return CbApi(cb_server, ssl_verify=ssl_verify, token=token)


def get_cbapi(splunk_service):
    cb_server, token, ssl_verify = get_creds(splunk_service)
    return CbEnterpriseResponseAPI(token=token, url=cb_server, ssl_verify=ssl_verify)


class CbSearchCommand2(GeneratingCommand):
    query = Option(name="query", require=False)
    max_result_rows = Option(name="maxresultrows", default=1000)

    field_names = []
    search_cls = None
    log_file = "da-ess-cbresponse"

    def __init__(self):
        super(CbSearchCommand2, self).__init__()
        self.setup_complete = False
        self.cb = None
        self.cb_url = "<unknown>"
        self.error_text = "<unknown>"
        self._logger.debug("init_complete")

    def error_event(self, comment, stacktrace=None):
        self._logger.debug("action=error_event")
        error_text = {"Error": comment}
        if stacktrace is not None:
            error_text["stacktrace"] = stacktrace
        self._logger.error(json.dumps(error_text))
        return {'sourcetype': 'bit9:carbonblack:json', '_time': time.time(), 'source': self.cb_url,
                '_raw': json.dumps(error_text)}

    def prepare(self):
        self._logger.debug("action=prepare")
        try:
            self.cb = get_cbapi(self.service)
            self.cb_url = self.cb.credentials.url
            self._logger.debug("action=configuration_success")
        except KeyError:
            self.error_text = "API key not set. Check that the Cb Response server is set up in the Cb Response App for Splunk configuration page."
            self._logger.error(self.error_text)
        except (ApiError, ServerError) as e:
            self.error_text = "Could not contact Cb Response server: {0}".format(str(e))
            self._logger.error(self.error_text)
        except CredentialMissingError as e:
            self.error_text = "Setup not complete: {0}".format(str(e))
            self._logger.error(self.error_text)
        except Exception as e:
            self.error_text = "Unknown error reading API key from credential storage: {0}".format(str(e))
            self._logger.error(self.error_text)
        else:
            self.setup_complete = True
            self._logger.info("No Errors on Prepare")

    def process_data(self, data_dict):
        self._logger.debug("action=process_data")
        """
        If you want to modify the data dictionary before returning to splunk, override this. // BSJ 2016-08-30
        """
        return data_dict

    def squash_data(self, data_dict):
        self._logger.debug("action=squash_data")
        for x in data_dict.keys():
            v = data_dict[x]
            data_dict[x] = str(v)
        return data_dict

    def generate_result(self, data):
        self._logger.debug("action=generate_result")
        rawdata = dict((field_name, getattr(data, field_name, "")) for field_name in self.field_names)
        squashed_data = self.squash_data(self.process_data(rawdata))
        return {'sourcetype': 'bit9:carbonblack:json', '_time': time.time(),
                'source': self.cb_url, '_raw': squashed_data}

    def generate(self):
        self._logger.debug("action=generate")
        try:
            if not self.setup_complete:
                yield self.error_event("Error: {0}".format(self.error_text))
                return  # explicitly stop the generator on prepare() error

            self._logger.debug("action=selecting cls={}".format(self.search_cls))
            query = self.cb.select(self.search_cls)
            if self.query is not None:
                self._logger.debug("action=setting_query query={}".format(self.query))
                query = query.where(self.query)

            self._logger.debug("action=running_results")
            for result in query[:int(self.max_result_rows)]:
                self._logger.info("yielding {0} {1}".format(self.search_cls.__name__, result._model_unique_id))
                yield self.generate_result(result)

        except Exception as e:
            yield self.error_event("error searching for {0} in Cb Response: {1}".format(self.query, str(e)),
                                   stacktrace=traceback.format_exc())
            return

    def transform(self, results):
        try:
            self._logger.debug("action=performing_transform")
            if not self.setup_complete:
                yield self.error_event("Error: {0}".format(self.error_text))
                return  # explicitly stop the generator on prepare() error

            self._logger.debug("action=selecting cls={}".format(self.search_cls))
            query = self.cb.select(self.search_cls)
            if self.query is not None:
                self._logger.debug("action=setting_query query={}".format(self.query))
                query = query.where(self.query)

            self._logger.debug("action=running_results")
            for result in query[:int(self.max_result_rows)]:
                self._logger.info("yielding {0} {1}".format(self.search_cls.__name__, result._model_unique_id))
                yield self.generate_result(result)

        except Exception as e:
            yield self.error_event("error searching for {0} in Cb Response: {1}".format(self.query, str(e)),
                                   stacktrace=traceback.format_exc())
            return



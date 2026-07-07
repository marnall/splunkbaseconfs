import logging as logger
import math
import sys
import os
import json
import time
from dateutil.tz import tzutc, tzlocal
import httplib2
import datetime
import re
from datetime import timedelta
from datetime import datetime
from datetime import date
from Utilities import KennyLoggins
from google_utilities import GSuiteUtilities
from ModularInput import ModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.util import normalizeBoolean
import multiprocessing.dummy as mp
from google_constants import global_scopes, app_name as _APP_NAME

# GSUITE-60 / GOOG-78: Add IOError Handling and Reporting
import errno

os.environ.setdefault("CRYPTOGRAPHY_ALLOW_OPENSSL_102", "1")
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
os.environ["PYTHONPATH"] = ",".join(sys.path)

from apiclient.discovery import build
import pytz

kl = KennyLoggins()
iLog = kl.get_logger(app_name=_APP_NAME, file_name="google-instantiation-logger", log_level=logger.INFO)
iLog.info("action=global_check path={}".format(sys.path))


class GSuiteModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self.utils = None
        self.credential = None
        self.proxy_string = None
        self.http = None
        self.retry = None
        self.build = None
        self.bigquery = None
        self.pubsub = None
        self._rawcredential = None
        self.non_delegated_credential = None
        self.non_delegated_http = None
        self.service = None
        self.secondary_service = None
        self.base_st = "google:workspaces"
        self.scopes = global_scopes
        self.current_scopes = []
        self.current_impersonation_user = "unknown"
        self._checkpoint_now_by_event = int(time.time())
        self.bigquery_threaded_data = {}
        # https://admin.google.com/ac/owl/domainwidedelegation < Enter the scopes required here. Full list below:
        # https://www.googleapis.com/auth/admin.reports.audit.readonly,https://www.googleapis.com/auth/admin.reports.usage.readonly,https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/admin.directory.user.readonly,https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly,https://www.googleapis.com/auth/drive.metadata.readonly,https://www.googleapis.com/auth/bigquery,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/classroom.courses.readonly,https://www.googleapis.com/auth/apps.alerts"

    # GOOGLE ANALYTICS APIs
    # https://developers.google.com/analytics/devguides/reporting/metadata/v3/devguide#python
    # https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries?hl=en_US
    # https://developers.google.com/analytics/devguides/reporting/core/v4/?hl=en_US THIS ONE FIRST

    def _catch_error(self, e, supplemental=None):
        if supplemental is None or type(supplemental) is not dict:
            supplemental = {}
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "input_guid=\"{}\" " \
                    "input_name=\"{}\"" \
                    "impersonation_user=\"{}\" " \
                    "scopes=\"{}\"" \
                    "{}".format(str(e),
                                type(e),
                                "{}".format(e),
                                fname,
                                exc_tb.tb_lineno,
                                self.get_config("guid"),
                                self.get_config("input_name"),
                                self.current_impersonation_user,
                                ",".join(self.current_scopes),
                                ' '.join('{}="{}"'.format(key, value) for key, value in supplemental.items()),
                                )
        if type(e) is BrokenPipeError:
            if e.errno:
                if e.errno == errno.EPIPE:
                    error_msg = "action=caught_io_epipe_error error_number={} {}".format(e.errno, error_msg)
                else:
                    error_msg = "action=caught_unknown_broken_pipe_error error_number={} {}".format(e.errno, error_msg)
            else:
                error_msg = "action=caught_broken_pipe error={} {}".format(e, error_msg)
        oldst = self.sourcetype()
        self.sourcetype("google:workspaces:error")
        self.print_error("{}".format(error_msg))
        self.print_event("{}".format(error_msg))
        self.sourcetype(oldst)

    def setup_gw(self, scope):
        try:
            self.utils = GSuiteUtilities(app_name=self._app_name, session_key=self.get_config("session_key"))
            self._config["api_key"] = self.utils.get_credential(self._app_name,
                                                                self.get_config("credential"))
            t = self.utils.get_workspace_creds(self.get_config("credential"))
            proxy_guid = t.get("proxy_guid", None)
            self._config["domain"] = t["domain"]
            self._config["impersonation_user"] = t["impersonation_user"]
            self._config["short_guid"] = self._config["guid"].split("-")[0]
            self.log.info("action=checking_for_proxy guid={}".format(proxy_guid))
            verify_ssl = True
            proxy_info = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED":
                self.log.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = httplib2.socks.PROXY_TYPE_HTTP
                self.log.debug("action=checking_ssl use_ssl={}".format(proxy.get("use_ssl")))
                if proxy.get("use_ssl") == "true" or "{}".format(proxy.get("use_ssl")) == "1":
                    proto = httplib2.socks.PROXY_TYPE_HTTP
                if proxy.get("use_ssl") == "false" or "{}".format(proxy.get("use_ssl")) == "0":
                    verify_ssl = False
                proxy_info = httplib2.ProxyInfo(
                    proto,
                    proxy_host="{}".format(proxy["proxy_url"].split(":")[0]),
                    proxy_port=int(proxy["proxy_url"].split(":")[1]),
                    proxy_pass=proxy.get("proxy_pass", None),
                    proxy_user=proxy.get("proxy_user", None))
                self.log.info("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                            proxy["proxy_url"]))
            self.log.info("action=setting_up_base_api user={} scopes={}".format(self.get_config("impersonation_user"),
                                                                                ";".join(self.scopes[scope])))
            self.host("google:workspaces:{}".format(self._config["domain"]))
            # These are not in the header due to complication issues when including before the path is set.
            # import pkg_resources
            # import importlib
            # importlib.reload(pkg_resources)
            if scope == "bigquery":
                # pkg_resources.get_distribution('google-cloud-bigquery')
                from google.cloud import bigquery
                self.bigquery = bigquery
            if scope == "pubsub":
                # pkg_resources.get_distribution('google-cloud-pubsub')
                from google.cloud import pubsub_v1
                from google.api_core import retry
                self.retry = retry
                self.pubsub = pubsub_v1
            from google.oauth2 import service_account
            from google.auth.exceptions import RefreshError
            import google_auth_httplib2
            import six
            import urllib
            self.build = build
            api_key = self.get_config("api_key")
            if api_key is None:
                self.log.fatal("action=failed_to_get_api_key api_key={} credential_guid={}".format(
                    api_key, self.get_config("credential")
                ))
                exit(244)
            credential = urllib.parse.unquote(self.get_config("api_key"))
            self._rawcredential = credential
            self.non_delegated_credential = service_account.Credentials.from_service_account_info(
                json.loads(credential),
                scopes=self.scopes[scope])
            self.credential = self.non_delegated_credential.with_subject(self.get_config("impersonation_user"))
            self.log.info("action=setup_http proxy_info={}".format(proxy_info))
            self.http = google_auth_httplib2.AuthorizedHttp(
                self.credential,
                http=httplib2.Http(proxy_info=proxy_info))
            self.non_delegated_http = google_auth_httplib2.AuthorizedHttp(
                self.non_delegated_credential,
                http=httplib2.Http(proxy_info=proxy_info))
            # # Reference for credential handling
            # https://developers.google.com/identity/protocols/oauth2/service-account#expiration
        # Handling of the error
        except Exception as e:
            self._catch_error(e)
            raise e

    def is_integer(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    # analytics

    def _format_date(self, dS):
        if dS == "today":
            return datetime.datetime.today().strftime("%Y-%m-%d")
        if dS == "yesterday":
            return (datetime.date.today() - datetime.timedelta(1)).strftime("%Y-%m-%d")
        return dS

    def _build_report_request_metric_object_simple(self, m):
        return {"expression": f"{m}"}

    def _build_report_request_dimension_object_simple(self, d):
        return {"name": f"{d}"}

    def _build_report_request_metric_object_simple_v4(self, m):
        return {"name": f"{m}"}

    def _build_report_request_dimension_object_simple_v4(self, d):
        return {"name": f"{d}"}

    def _build_report_request(self, attr, metrics, dimensions):
        a = dict(attr)
        a["dimensions"] = [self._build_report_request_dimension_object_simple(x) for x in dimensions]
        a["metrics"] = [self._build_report_request_metric_object_simple(x) for x in metrics]
        return a

    def _build_report_request_v4(self, attr, metrics, dimensions):
        a = dict(attr)
        self.log.debug("a={} metrics={} dimensions={}".format(a, metrics, dimensions))
        a["dimensions"] = [self._build_report_request_dimension_object_simple_v4(x) for x in dimensions]
        a["metrics"] = [self._build_report_request_metric_object_simple_v4(x) for x in metrics]
        return a

    def _get_uuid(self):
        return ""

    def _sanitize(self, s):
        return s.replace('\\u200e', "__u200e__").replace('\\u2010', "__u2010__")

    def _threaded_analytics_row_v4(self, report, row, dimensionHeaders, metricHeaders, input_guid, accountId,
                                   webPropertyId, websiteUrl):
        try:
            row_result = {
                "report": {x: report[x] for x in report if x not in ["data"]},
                "response": row,
                "metrics": {},
                "dimensions": {},
                "accountId": "{}".format(accountId),
                "webPropertyId": "{}".format(webPropertyId),
                "websiteUrl": "{}".format(websiteUrl)
            }
            dimensionsResponse = row.get('dimensionValues', [])
            metricsResponse = row.get('metricValues', [])
            self.log.odebug(action="enumerate_dimensionHeaders",
                            dimensionHeaders=dimensionHeaders,
                            dimensionsResponse=dimensionsResponse,
                            pass_test=len(dimensionsResponse) == len(dimensionHeaders))
            if len(dimensionsResponse) == len(dimensionHeaders):
                for i, dimHead in enumerate(dimensionHeaders):
                    self.log.odebug(action="enumerated_header",
                                    i=i,
                                    dimHead=dimHead,
                                    input_guid=input_guid,
                                    dimensionsResponse=dimensionsResponse[i])
                    dimension_name = self._sanitize(dimHead.get("name", "no_name_attribute"))
                    dimension_value = dimensionsResponse[i].get("value", "no_value_attribute")
                    row_result[dimension_name] = self._sanitize(dimension_value)
                    row_result["dimensions"][dimension_name] = dimension_value
            for i, values in enumerate(metricsResponse):
                self.log.odebug(action="enumerate_header_metrics",
                                i=i, values=values)
                for mi, metHead in enumerate(metricHeaders):
                    self.log.odebug(action="enumerated_metric_header",
                                    i=i,
                                    dimHead=metHead,
                                    input_guid=input_guid,
                                    metricsResponse=metricsResponse[mi])
                    metric_name = self._sanitize(metHead.get("name", "no_name_attribute"))
                    metric_value = metricsResponse[mi].get("value", "no_value_attribute")
                    row_result[metric_name] = self._sanitize(metric_value)
                    row_result["metrics"][metric_name] = metric_value
            self.debug("input_guid={} row_result={}".format(input_guid, row_result))
            time_field = self.get_config("time_field", "WEAINTFOUNDSH_T")
            explicit_time_field = row_result.get(time_field, None)
            view_tz = self.get_config("timeZone", "Etc/GMT")
            updated_tz = pytz.timezone(view_tz).localize(datetime.utcnow()).strftime('%z')
            self.debug(
                "input_guid={} explicit_time_field={} time_field={} time_zone={}".format(input_guid,
                                                                                         explicit_time_field,
                                                                                         self.get_config("time_field",
                                                                                                         "WEAINTFOUNDSH_T"),
                                                                                         updated_tz))
            time_formats = {"date": "%Y%m%d",
                            "dateHour": "%Y%m%d%H",
                            "dateHourMinute": "%Y%m%d%H%M"}
            explicit_time = None
            if explicit_time_field:
                explicit_time = datetime.strptime(explicit_time_field, time_formats[time_field]).strftime(
                    "%a, %d %b %Y %H:%M:%S {}".format(updated_tz))
                self.log.debug("explicit_time_field={} time_field={} timestamp=\"{}\"".format(explicit_time_field,
                                                                                              self.get_config(
                                                                                                  "time_field",
                                                                                                  "WEAINTFOUNDSH_T"),
                                                                                              explicit_time))
                row_result["timestamp"] = explicit_time
            self.print_event("{}".format(json.dumps(row_result)))
        except Exception as e:
            self._catch_error(e, {"input_guid": input_guid, "row": row})
        # self.print_event(''.join(filter(lambda qt: qt in string.printable, anEvent)),
        #                  explicit_time=explicit_time)

    def get_analytics_checkpoint_name(self):
        return "input-{}-view-{}.json".format(self.get_config("guid"), self.get_config("view").replace("/", "-"))

    def get_analytics_checkpoint(self):
        chkpnt_name = self.get_analytics_checkpoint_name()
        chkpnt_obj = self._get_checkpoint(chkpnt_name)
        executed_timeranges_field = "executed_timeranges"
        if executed_timeranges_field not in chkpnt_obj.keys():
            chkpnt_obj[executed_timeranges_field] = []
        return chkpnt_obj

    def set_analytics_checkpoint(self, chkpoint):
        self._set_object_checkpoint(self.get_analytics_checkpoint_name(), chkpoint["last_execution"], chkpoint)

    def analytics_api_reports(self, data_date, write_mod_input=True):
        view = self.get_config("view")
        guid = self.get_config("guid")
        self.log.oinfo(action="getting_analytics", guid=guid, view=view)
        self._analytics_api_reports_v4(data_date, write_mod_input)

    def _analytics_api_reports_v4(self, data_date, write_mod_input=True):
        # self.log.warn("report=v4 data_date={} input_guid={} msg=not_implemented".format(data_date, self.get_config("guid")))
        chkpnt_name = "UNKNWON-MASSIVE_ERROR"
        try:
            api_endpoint = "analyticsdata"
            api_version = "v1beta"
            input_guid = self.get_config("guid")
            self.log.info(
                "report=v4 input_guid={} function=google_analytics_api_reports data_date={}".format(input_guid,
                                                                                                    data_date))
            chkpnt_name = self.get_analytics_checkpoint_name()
            chkpnt_obj = self.get_analytics_checkpoint()
            executed_timeranges_field = "executed_timeranges"
            if executed_timeranges_field not in chkpnt_obj.keys():
                chkpnt_obj[executed_timeranges_field] = []
            self.log.info("report=v4 input_guid={} checkpoint={}".format(input_guid, chkpnt_obj))
            analytics = self.build(api_endpoint, api_version, http=self.non_delegated_http)
            dimensions = self.get_config("dimensions").split(",")
            if len(dimensions) > 9:
                raise Exception("Dimensions can contain a max of 9 items")
            metrics = self.get_config("metrics").split(",")
            if len(metrics) > 10:
                raise Exception("Please limit metrics to 10 total.")
            date_ranges = {}
            if data_date in chkpnt_obj[executed_timeranges_field]:
                self.log.warn("input_guid={} action=date_consumed message='{}' time_range={}".format(input_guid,
                                                                                                     "Date range was already consumed via modular input.",
                                                                                                     data_date))
                return {"checkpoint": chkpnt_name, date: data_date}
            if self.get_config("start_date"):
                date_ranges["startDate"] = self._format_date(self.get_config("start_date"))
            else:
                date_ranges["startDate"] = data_date
            if self.get_config("end_date"):
                date_ranges["endDate"] = self._format_date(self.get_config("end_date"))
            else:
                date_ranges["endDate"] = data_date
            selected_dates = [date_ranges["startDate"]]
            self.debug("report=v4 input_guid={} non-backfill selected_dates={}".format(input_guid, selected_dates))
            import re
            property_id = self.get_config("view")
            # don't do more than 100,000,000 results.
            runaway = 100000000
            limit = 100000
            offset = 0
            continue_pulling = True
            total_count = 0
            while total_count < runaway and continue_pulling:
                starting_report_request_attributes = {
                    "property": property_id,
                    "limit": limit,
                    "offset": offset,
                    'dateRanges': [date_ranges],
                    'keepEmptyRows': True
                }
                report_request = self._build_report_request_v4(starting_report_request_attributes, metrics, dimensions)
                self.debug(
                    "report=v4 input_guid={} limit={} offset={} report_request={}".format(input_guid, limit, offset,
                                                                                          report_request))
                report_response = analytics.properties().runReport(property=property_id, body=report_request).execute()
                self.debug("report=v4 input_guid={} report_response={}".format(input_guid, report_response))
                accountId = self.get_config("accountId")
                webPropertyId = self.get_config("webPropertyId")
                websiteUrl = self.get_config("websiteUrl")
                report_response["request"] = report_request
                dimensionHeaders = report_response.get('dimensionHeaders', [])
                metricHeaders = report_response.get('metricHeaders', [])
                rows = report_response.get('rows', [])
                # is_data_golden = report_response.get('data', {}).get('isDataGolden', False)
                offset += limit
                total_count += len(rows)
                if len(rows) < limit:
                    self.debug("action=stopping_pull row_length={} limit={}".format(len(rows), limit))
                    continue_pulling = False
                self.debug(
                    "action=report_response date={} input_guid={} rows={} dHeaders={} mHeaders={}".format(date_ranges,
                                                                                                          input_guid,
                                                                                                          len(rows),
                                                                                                          dimensionHeaders,
                                                                                                          metricHeaders))
                p = mp.Pool(10)
                matrix = [(report_response, row, dimensionHeaders, metricHeaders, input_guid, accountId,
                           webPropertyId, websiteUrl)
                          for num, row in enumerate(rows)]
                p.starmap(self._threaded_analytics_row_v4, matrix)
                p.close()
                p.join()
            if data_date not in chkpnt_obj[executed_timeranges_field]:
                chkpnt_obj[executed_timeranges_field].append(data_date)
            if write_mod_input:
                self._set_object_checkpoint(chkpnt_name, time.time(), chkpnt_obj)
            return {"checkpoint": chkpnt_name, date: data_date}
        except Exception as e:
            self._catch_error(e, {"data_date": data_date, "write_mod_input": write_mod_input})
            return {"checkpoint": chkpnt_name}

    def analytics_set_checkpoint(self, dates):
        chkpnt_name = self.get_analytics_checkpoint_name()
        chkpnt_obj = self._get_checkpoint(chkpnt_name)
        executed_timeranges_field = "executed_timeranges"
        if executed_timeranges_field not in chkpnt_obj.keys():
            chkpnt_obj[executed_timeranges_field] = []
        for dd in dates:
            if dd not in chkpnt_obj[executed_timeranges_field]:
                chkpnt_obj[executed_timeranges_field].append(dd)
        self._set_object_checkpoint(chkpnt_name, time.time(), chkpnt_obj)

    # forms
    def get_answers(self, response):
        answers = []
        for a in response["answers"]:
            ans = response["answers"][a]
            for k in ["createTime", "lastSubmittedTime", "responseId"]:
                ans[k] = response[k]
            answers.append(ans)
        return answers

    def get_form(self):
        try:
            form_id = self.get_config("form_id")
            self.log.info("action=get_forms id={}".format(form_id))
            ss = self.build('forms', 'v1', http=self.http)
            responses = ss.forms().responses().list(formId=form_id).execute()["responses"]
            form_data = ss.forms().get(formId=form_id).execute()
            self.log.info("action=got_form def={}".format(form_data))
            self.print_event(json.dumps(form_data), "timestamp", None,
                             source="google:workspaces:forms:{}".format(form_id),
                             sourcetype="google:workspaces:forms:data")
            self.log.info("action=get_forms responses={}".format(responses))
            dest = self.get_config("destination").split(",")
            destination = dest[0]
            order = None
            if len(dest) > 1:
                order = dest[1]
            destination = "index"
            self.log.info("action=check_destination destination={} order={} dest={}".format(destination, order, dest))
            if destination == "transform":
                self.print_multiple_events(
                    [self._do_lookup_form(ss, form_id, order, destination) for ss in responses],
                    source="google:workspaces:forms:{}".format(form_id),
                    sourcetype="google:workspaces:forms:transform")
            elif destination == "kvstore":
                kvstore_events = [self._do_kvstore_form(ss, form_id, order, destination) for ss in responses]
                self.print_multiple_events(
                    kvstore_events,
                    source="google:workspaces:forms:{}".format(form_id),
                    sourcetype="google:workspaces:forms:kvstore")
            elif destination == "index":
                self.print_multiple_events(responses,
                                           source="google:workspaces:forms:responses:{}".format(
                                               form_id),
                                           sourcetype="google:workspaces:forms:data")
                self.print_multiple_events([x for r in responses for x in self.get_answers(r)],
                                           source="google:workspaces:forms:{}:answers".format(
                                               form_id),
                                           sourcetype="google:workspaces:forms:data")
            else:
                self.log.fatal("action=no_destination destination={}".format(destination))
            return responses
        except Exception as e:
            self.print_error("Get Forms Error: {}".format(e))
            self._catch_error(e)

    # Spreadsheet

    def get_spreadsheets(self, spreadsheet_id=None, include_grid_data=False):
        try:
            self.log.info("action=get_spreadsheets id={} data_include={}".format(spreadsheet_id, include_grid_data))
            ss = self.build('sheets', 'v4', http=self.http)
            return ss.spreadsheets().get(spreadsheetId=spreadsheet_id, includeGridData=include_grid_data).execute()
        except Exception as e:
            self.print_error("Get Spreadsheets Error: {}".format(e))
            self._catch_error(e, {"spreadsheet_id": spreadsheet_id, "include_grid_data": include_grid_data})

    def get_spreadsheet(self):
        try:
            self.log.info("action=start_spreadsheet spreadsheet={} sheet={}".format(
                self.get_config("ss_id"), self.get_config("ss_sheet")
            ))
            sheet_information = self.get_spreadsheets(self.get_config("ss_id"), True)
            individual_sheets = self.get_config("ss_sheet").split(",")
            sheet_title = sheet_information.get("properties", {}).get("title", "").replace(" ", "_").lower()
            self.log.info(
                "action=checking_for_inclusion title={} sheets_to_keep={} available_sheets={}".format(
                    sheet_title,
                    json.dumps(individual_sheets),
                    json.dumps([
                        {"id":
                            sheet.get("properties",
                                      {}).get(
                                "sheetId"),
                            "title": sheet.get(
                                "properties",
                                {}).get(
                                "title")} for sheet
                        in
                        sheet_information.get(
                            "sheets", [])])))
            sheets = [sheet for sheet in sheet_information.get("sheets", []) if
                      "{}".format(sheet.get("properties", {}).get("sheetId")) in individual_sheets]
            self.log.debug("action=got_sheets sheet_count={}".format(len(sheets)))
            sheet_data = [self._parse_spreadsheet_data({"title": sheet_title, "id": self.get_config("ss_id")}, sheet)
                          for sheet in sheets]
            # self.log.debug("action=parsed_sheets sheets={}".format(json.dumps(sheet_data)))
            dest = self.get_config("destination").split(",")
            destination = dest[0]
            order = None
            if len(dest) > 1:
                order = dest[1]
            self.log.info("action=check_destination destination={} order={} dest={}".format(destination, order, dest))
            if destination == "transform":
                self.print_multiple_events(
                    [self._do_lookup_sheet(ss, sheet_title, order, destination) for ss in sheet_data],
                    source="google:workspaces:spreadsheets:{}".format(self.get_config("ss_id")),
                    sourcetype="google:workspaces:spreadsheets:transform")
            elif destination == "kvstore":
                kvstore_events = [self._do_kvstore_sheet(ss, sheet_title, order, destination) for ss in sheet_data]
                self.print_multiple_events(
                    kvstore_events,
                    source="google:workspaces:spreadsheets:{}".format(self.get_config("ss_id")),
                    sourcetype="google:workspaces:spreadsheets:kvstore")
            elif destination == "index":
                [self.print_multiple_events(ss,
                                            source="google:workspaces:spreadsheets:{}:{}".format(
                                                self.get_config("ss_id"),
                                                ss[0]["metadata"]["sheet_properties"]["sheetId"]),
                                            sourcetype="google:workspaces:spreadsheets:data") for ss in sheet_data if
                 ss is not None]
            else:
                self.log.fatal("action=no_destination destination={}".format(destination))
        except Exception as e:
            self._catch_error(e)

    def _do_lookup_sheet(self, sheet, sheet_title, order, destination):
        s_id = sheet[0]["metadata"]["sheet_properties"].get("title")
        t_name = re.sub('[^0-9a-zA-Z]+', '_',
                        "google_workspace_csv_ss_{}_s_{}_transform".format(sheet_title, s_id).lower())
        filename = "{}.csv".format(t_name)
        ret_obj = {"transform_name": t_name, "filename": filename, "error": False, "metadata": sheet[0]["metadata"],
                   "destination": destination, "order": order}
        self.log.info(
            "action=checking_transform_exists filename={} sheet={} title={} order={}".format(filename, len(sheet),
                                                                                             sheet_title, order))
        r = self.utils.check_transform_exists(t_name, do_create=True, filename=filename)
        fields = "fields"
        starting_index = 0
        if order == "ordered":
            fields = "ordered_fields"
            starting_index = -1
        if r is not None:
            self.utils.write_lookup(filename,
                                    [row.get(fields) for row in sheet if row.get("row_index") > starting_index])
        else:
            ret_obj["error"] = True
            ret_obj[
                "error_message"] = "Failed to create Transforms Stanza, please see utilities log for detailed error."
        return ret_obj

    def _do_kvstore_sheet(self, sheet, sheet_title, order, destination):
        try:
            s_id = sheet[0]["metadata"]["sheet_properties"].get("title")
            t_name = re.sub('[^0-9a-zA-Z]+', '_',
                            "google_workspace_kvstore_ss_{}_s_{}_transform".format(sheet_title, s_id).lower())
            ret_obj = {"collection_name": t_name, "error": False, "metadata": sheet[0]["metadata"],
                       "destination": destination,
                       "order": order}
            fields = "fields"
            starting_index = 0
            if order == "ordered":
                fields = "ordered_fields"
                starting_index = -1
            fl = ["_key"]
            [fl.extend(x.get(fields).keys()) for x in sheet]
            fields_list = list(set(fl))
            self.log.info("action=kvstore_generate_fields_list fields_list={}".format(fields_list))
            r = self.utils.check_collection_exists(t_name, do_create=True,
                                                   fields_list=fields_list)
            if r is not None:
                def set_list(row):
                    list_fields = row.get(fields)
                    list_fields["_key"] = "row_{}".format("{}".format(row.get("row_index")).rjust(10, '0'))
                    return list_fields

                data = [set_list(row) for row in sheet if row.get("row_index") > starting_index]
                c_name = "{}_col".format(t_name)
                self.log.info("action=sync_to_kvstore action=deleting_existing_items collection={}".format(c_name))
                self.utils.delete_kvstore_all_items(c_name)
                self.log.info("action=sync_to_kvstore action=batch_save_items collection={}".format(c_name))
                exclude_types = [bytes, bytearray]
                ret_obj["kvstore_batch_save"] = [
                    x if not type(x) in exclude_types else {"incorrect_type": "{}".format(type(x))} for x in
                    self.utils.kvstore_batch_save(c_name, data)]
            else:
                ret_obj["error"] = True
                ret_obj[
                    "error_message"] = "Failed to create Collection or Transforms Stanzas, please see utilities log for detailed error."
            return ret_obj
        except Exception as e:
            self._catch_error(e)

    def _parse_spreadsheet_data(self, ss, sheet_information, destination=False):
        try:
            sheet_data = sheet_information.get("data", {})[0].get("rowData", [])
            hr = []
            for index, item in enumerate(sheet_data[0].get("values")):
                hr.append(item.get("formattedValue", "COLUMN_{}".format("{}".format(index).rjust(5, '0'))))
            metadata = {"spreadsheet_title": ss.get("title", "not_available"),
                        "spreadsheet_id": ss.get("id", "not_available"),
                        "sheet_properties": sheet_information.get("properties"),
                        "header_row": hr}
            metadata["sheet_properties"]["destination"] = self.get_config("destination").split(",")[0]
            self.info("header_row={}".format(json.dumps(hr)))
            return [self._parse_row(hr, metadata, sheet, idx) for idx, sheet in enumerate(sheet_data)]
        except Exception as e:
            self.catch_error(e)

    def _parse_row(self, hr, md, sh, ridx):
        try:
            obj = {"metadata": md, "fields": {}, "ordered_fields": {}, "row_index": ridx}
            if sh is None:
                return obj
            if sh.get("values") is None:
                return obj
            for idx, it in enumerate(sh.get("values")):
                field_name = "COLUMN_{}".format("{}".format(idx).rjust(5, '0'))
                field_value = it.get("formattedValue", "")
                obj["ordered_fields"][field_name] = field_value
                try:
                    field_name = hr[idx].replace(" ", "_")
                except IndexError:
                    pass
                obj["fields"][field_name] = field_value
            return obj
        except Exception as e:
            self.catch_error(e)

    # PUBSUB

    def get_pubsub(self):
        from concurrent.futures import TimeoutError
        # TODO: Add proxy support for pubsub
        subscriber = self.pubsub.SubscriberClient(credentials=self.non_delegated_credential)
        subscription_path = subscriber.subscription_path(self.get_config("project"), self.get_config("subscription"))
        # SHOULD be only Input to *actually use interval*
        perc = float(self.get_config("percent_of_interval") or 0.75)
        timeout = round(int(self.get_config("interval")) * perc) or 60
        max_messages = int(self.get_config("max_messages")) or 1000000
        self.info("action=pubsub_listen path={} timeout={} interval={} percent_of_interval={} max_messages={}".format(
            subscription_path,
            timeout,
            self.get_config("interval"),
            perc, max_messages))
        self.info("action=pubsub_listen setup_subscription")
        # Wrap subscriber in a 'with' block to automatically call close() when done.
        with subscriber:
            try:
                # When `timeout` is not set, result() will block indefinitely,
                # unless an exception is encountered first.
                self.info("action=pubsub_listen result timeout={}".format(timeout))
                response = subscriber.pull(
                    request={"subscription": subscription_path, "max_messages": max_messages},
                    retry=self.retry.Retry(deadline=timeout)
                )
                self.info("action=pubsub_listen done response")
                ack_ids = []
                p = mp.Pool(10)
                matrix = [(num, result, ack_ids)
                          for num, result in enumerate(response.received_messages)]
                p.starmap(self._print_threaded_pubsub, matrix)
                p.close()
                p.join()
                # Acknowledges the received messages so they will not be sent again.
                self.debug("action=pubsub_listen ack_ids={}".format(ack_ids))
                if len(ack_ids) > 0:
                    subscriber.acknowledge(
                        request={"subscription": subscription_path, "ack_ids": ack_ids}
                    )
                    self.info("action=pubsub_listen acked_events={}".format(len(response.received_messages)))
            except Exception as e:
                self._catch_error(e)
                # streaming_pull_future.cancel()

    # #### USAGE REPORTS MI #####
    def get_directory_report(self, user_key=None):
        try:
            self.info("function=admin_directory_users status=starting")
            service = self.build('admin', 'directory_v1', http=self.http)
            page_token = None
            local_count = 0
            total_count = 0
            error_found = False
            params = {"customer": "my_customer", "orderBy": "email", "viewType": "admin_view"}
            if user_key is not None:
                params["query"] = " OR ".join([f"email={user_key}"])
            thread_params = {"st": "usage:directory", "tf": "timestamp"}
            do_email_forward = self.get_config("email_forward_check", "false")
            if do_email_forward is None:
                do_email_forward = "false"
            if do_email_forward.lower() in ["1", 1, "true"]:
                self.secondary_service = self.build('gmail', 'v1', http=self.http)
            while not error_found:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug(f"action=paginate page_token={page_token}")
                    current_page = service.users().list(**params).execute()
                    self.debug("action=paginate has_users={}".format("users" in current_page))
                    if "users" in current_page:
                        p = mp.Pool(10)
                        matrix = [(num,
                                   result,
                                   thread_params)
                                  for num, result in enumerate(current_page["users"])]
                        p.starmap(self._print_threaded_directory, matrix)
                        p.close()
                        p.join()
                        total_count = total_count + len(current_page["users"])
                        local_count = local_count + len(current_page["users"])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    self.log.debug("action=caught_admin_error error_type={} error={}".format(type(e), e))
                    self._catch_error(e)
                    error_found = True
                    break
            self.log.info("action=completed_run application_name={} total_count={}".format(
                self.get_config("application_name"),
                total_count))
        except Exception as e:
            self._catch_error(e)

    def get_chrome_report(self):
        try:
            # TODO: Write a <done> event for every days worth of data.
            self.log.info("function=chrome_os_devices_usage status=starting")
            service = self.build('admin', 'directory_v1', http=self.http)
            page_token = None
            total_count = 0
            params = {'customerId': 'my_customer', 'orderBy': "status", 'projection': "FULL"}
            thread_params = {"st": "usage:chrome", "tf": "timestamp"}
            self.info("operation=starting_while_loop_for_pages")
            while True:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug("Have A Page? :%s" % page_token)
                    current_page = service.chromeosdevices().list(**params).execute()
                    self.debug("got a current_page")
                    if "chromeosdevices" in current_page:
                        p = mp.Pool(10)
                        matrix = [(num,
                                   result,
                                   thread_params)
                                  for num, result in enumerate(current_page["chromeosdevices"])]
                        p.starmap(self._print_threaded, matrix)
                        p.close()
                        p.join()
                        total_count = total_count + len(current_page.get('chromeosdevices'))
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except TypeError as e:
                    self._catch_error("error=type_error message={}".format(e))
                    break
                except Exception as e:
                    self._catch_error(e)
            self.log.info("action=completed_run application_name={} total_count={}".format(
                self.get_config("application_name"),
                total_count))
        except Exception as e:
            self._catch_error(e)

    def _get_usage_checkpoint(self, key):
        chkpointfile = os.path.join(self._config["checkpoint_dir"], "{}_{}".format(self.host(), key)).replace(":", "_")
        chk_time = 0
        self._loaded_checkpoints[key] = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
        self.debug("set checkpoint load time to: {}".format(self._loaded_checkpoints[key]))
        try:
            if os.path.isfile(chkpointfile):
                self.debug(f"action=get_usage_checkpoint filename={chkpointfile}")
                chk_time = self._read_file(chkpointfile)
                self.debug("found a value in the file for {} : {}".format(key, chk_time))
                chk_time = json.loads(chk_time)
            else:
                # assume that this means the checkpoint is not there
                # Let's Default to 60 minutes ago. Just to start pulling data.
                # TODO: Make loading a checkpoint configurable in respect to the look back time (in minutes)
                self.debug("Setting Checkpoint {} default time".format(key))
                wibbly_wobbly_timey_wimey = datetime.utcnow() - timedelta(
                    minutes=self.checkpoint_default_lookback())
                chk_time = (wibbly_wobbly_timey_wimey - datetime.utcfromtimestamp(0)).total_seconds()
                chk_time = float(chk_time)
                chk_time = {"last_execution": chk_time}
        except Exception as e:
            self._catch_error(e)
        self.debug("Returning CheckPoint Time {}".format(chk_time))
        return chk_time

    def _get_usage_checkpoint_name(self, domain, application_name):
        filename = "{}_{}-domain-{}_usage-{}.txt".format(self.host().replace(":", "_"), self.get_config("guid"), domain,
                                                         application_name)
        self.log.debug(f"action=creating_filename filename={filename}")
        return filename

    def _usage_base(self):
        domain = self.get_config("domain")
        application_name = self.get_config("application_name")
        get_chkpnt_name = self._get_usage_checkpoint_name(domain, application_name)
        self.log.info(f"action=getting_checkpoint filename={get_chkpnt_name}")
        self.sourcetype("google:workspaces:usage:{}".format(application_name))
        lb = self.get_config("lookback")
        self.log.debug(
            "action=evaluating_lookback application_name={} lookback={} lookback_type={}".format(application_name,
                                                                                                 lb, type(lb)))
        if int(lb) > 0:
            self.log.debug(
                "action=evaluating_lookback application_name={} new_lookback={}".format(application_name,
                                                                                        (int(lb) * 1440)))
            self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
        chkpnt_obj = self._get_usage_checkpoint(get_chkpnt_name)
        chkpnt = int("{}".format(chkpnt_obj["last_execution"]).split('.')[0])
        chkpnt_now = int(time.time())
        start_time_diff = chkpnt_now - chkpnt
        self.info(
            "status=starting application_name={} chkpnt={} chkpnt_now={} diff={} obj={}".format(
                application_name, chkpnt, chkpnt_now, start_time_diff, chkpnt_obj))
        # Set start time to one week ago, to avoid too many results
        # 2015-04-23T14:24:48.802688Z
        rightNowDate = date.fromtimestamp(chkpnt_now)
        thenDate = date.fromtimestamp(chkpnt)
        if "last_date" in chkpnt_obj:
            self.info("action=setting_thenDate found_date={}".format(chkpnt_obj["last_date"]))
            thenDate = datetime.strptime(chkpnt_obj["last_date"], "%Y-%m-%d").date()
        numDays = (rightNowDate - thenDate).days
        self.info("action=calculating_report_dates checkpoint={}  rightNow={} numDays={} ".format(chkpnt, chkpnt_now,
                                                                                                  numDays))
        if numDays < 1:
            self.info("operation=checkpoint_check numberOfDays=%s checkpoint=%s execution_time=%s" % (
                numDays, chkpnt, rightNowDate))
            return None, None, None
        reportDates = [d.strftime("%Y-%m-%d") for d in [rightNowDate - timedelta(days=x) for x in range(0, numDays)]]
        self.info(f"action=usage_user_reports dates_to_check={reportDates} application_name={application_name}")
        chkpnt_name = "{}-domain-{}_usage-{}.txt".format(self.get_config("guid"), domain, application_name)
        return chkpnt_now, chkpnt_name, reportDates

    def _set_usage(self, results, chkpnt_name, chkpnt_now):
        used_dates = [datetime.strptime(x["date"], "%Y-%m-%d") for x in results if x["count"] > 0]
        used_dates.sort()
        if len(used_dates) > 0:
            self.info("action=usage_user last={} sorted={}".format(used_dates[-1], used_dates))
            last_date = datetime.strftime(used_dates[-1], "%Y-%m-%d")
            self.log.info(f"action=saving_checkpoint name={chkpnt_name} last_found={last_date}")
            self._set_object_checkpoint(chkpnt_name, chkpnt_now, {"last_date": last_date})
        else:
            self.log.warn(
                f"action=saving_checkpoint name={chkpnt_name} msg='not saving checkpoint: No used Dates Found'")

    def _get_customer_usage_report_day(self, day):
        try:
            service = self.build('admin', 'reports_v1', http=self.http)
            application_name = self.get_config("application_name")
            page_token = None
            params = {'date': day}
            self.info("operation=starting_while_loop_for_pages application_name={} date={}".format(
                application_name, day))
            local_count = 0
            thread_params = {"st": "usage:{}".format(application_name), "tf": "timestamp"}
            while True:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug("Have A Page? :%s" % page_token)
                    current_page = service.customerUsageReports().get(**params).execute()
                    self.debug("got a current_page")
                    if "usageReports" in current_page:
                        p = mp.Pool(5)
                        matrix = [(num,
                                   result,
                                   thread_params)
                                  for num, result in enumerate(current_page["usageReports"])]
                        p.starmap(self._print_threaded_usage, matrix)
                        p.close()
                        p.join()
                        local_count = local_count + len(current_page["usageReports"])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    self.log.error("action=caught_usage_error error_type={} error={}".format(type(e), e))
                    break
            return {"date": day, "count": local_count}
        except Exception as e:
            self._catch_error(e)

    def get_customer_usage_report(self):
        try:
            chkpnt_now, chkpnt_name, reportDates = self._usage_base()
            if reportDates is None:
                self.log.warn("action=not_running reason=InvalidDates")
                return
            application_name = self.get_config("application_name")
            results = []
            self.info("action=starting_usage application_name={} reportDates={}".format(application_name, reportDates))
            try:
                results = [self._get_customer_usage_report_day(reportDate)
                           for num, reportDate in enumerate(reportDates)]
            except Exception as e:
                self.log.warn("action=thread_exception type=\"{}\" exception=\"{}\"".format(type(e), e))
            self.info("action=found_events application_name={} counter={}".format(application_name, results))
            self._set_usage(results, chkpnt_name, chkpnt_now)
        except Exception as e:
            self._catch_error(e)

    def _get_user_usage_report_day(self, day):
        try:
            service = self.build('admin', 'reports_v1', http=self.http)
            application_name = self.get_config("application_name")
            page_token = None
            params = {'userKey': 'all', 'date': day}
            self.info("operation=starting_while_loop_for_pages application_name={} date={}".format(
                application_name, day))
            local_count = 0
            thread_params = {"st": "usage:{}".format(application_name), "tf": "timestamp"}
            while True:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug("Have A Page? :%s" % page_token)
                    current_page = service.userUsageReport().get(**params).execute()
                    self.debug("got a current_page")
                    if "usageReports" in current_page:
                        p = mp.Pool(5)
                        matrix = [(num,
                                   result,
                                   thread_params)
                                  for num, result in enumerate(current_page["usageReports"])]
                        p.starmap(self._print_threaded_usage, matrix)
                        p.close()
                        p.join()
                        local_count = local_count + len(current_page["usageReports"])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    error_msg = " " \
                                "error_message=\"{}\" " \
                                "error_type=\"{}\" " \
                                "error_arguments=\"{}\" " \
                                "error_filename=\"{}\" " \
                                "error_line_number=\"{}\" " \
                                "input_guid=\"{}\" " \
                                "input_name=\"{}\" " \
                        .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, self.get_config("guid"),
                                self.get_config("input_name"))
                    self.log.error("action=caught_usage_error {}".format(error_msg))
                    break
            return {"date": day, "count": local_count}
        except Exception as e:
            self._catch_error(e)

    def get_user_usage_report(self):
        try:
            chkpnt_now, chkpnt_name, reportDates = self._usage_base()
            if reportDates is None:
                self.log.warn("action=not_running reason=InvalidDates")
                return
            application_name = self.get_config("application_name")
            results = []
            self.info("action=starting_usage application_name={} reportDates={}".format(application_name, reportDates))
            try:
                results = [self._get_user_usage_report_day(reportDate)
                           for num, reportDate in enumerate(reportDates)]
            except Exception as e:
                self.log.warn("action=thread_exception type=\"{}\" exception=\"{}\"".format(type(e), e))
            self.info("action=found_events application_name={} counter={}".format(application_name, results))
            self._set_usage(results, chkpnt_name, chkpnt_now)
        except Exception as e:
            self._catch_error(e)

    def _usage_fix(self, evt):
        evt["timestamp"] = "{} 00:00:00".format(evt["date"])
        for param in evt["parameters"]:
            if "name" in param:
                k = param["name"].replace(":", "_")
                v = "NO_TYPE_FOUND"
                if "intValue" in param:
                    v = param["intValue"]
                elif "boolValue" in param:
                    v = param["boolValue"]
                elif "stringValue" in param:
                    v = param["stringValue"]
                elif "datetimeValue" in param:
                    v = param["datetimeValue"]
                param[k] = v
        return evt

    # ##### END USAGE REPORTS ####
    # ##### ALERTS ####
    def process_alert_api_evts(self, res, source):
        return res

    def get_alerts_report(self):
        try:

            domain = self.get_config("domain")
            application_name = "alerts"
            chkpnt_name = "{}-domain-{}_alerts-{}.txt".format(self.get_config("guid"), domain, application_name)
            self.log.debug(f"action=read process=checkpoint file={chkpnt_name}")
            lb = self.get_config("lookback")
            self.log.debug(
                "action=evaluating_lookback application_name={} lookback={} lookback_type={}".format(application_name,
                                                                                                     lb, type(lb)))
            if int(lb) > 0:
                self.log.debug(
                    "action=evaluating_lookback application_name={} new_lookback={}".format(application_name,
                                                                                            (int(lb) * 1440)))
                self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
            self.log.debug(f"action=read process=checkpoint file={chkpnt_name}")
            chkpnt_obj = self._get_checkpoint(chkpnt_name)
            chkpnt = "{}".format(chkpnt_obj["last_execution"])
            chkpnt_now = int(time.time())
            self.log.debug(
                f"action=read process=checkpoint file={chkpnt_name} value={chkpnt} new_checkpoint_time={chkpnt_now}")
            self.sourcetype("google:workspaces:alerts")
            self.info(
                "function=alerts_report status=starting application_name={} time_of_gmtime={} timezone_of_localtime={}".format(
                    application_name, time.strftime("%Y-%m-%dT%H:%M:%S%z  %Z", time.gmtime()),
                    time.strftime("%Y-%m-%dT%H:%M:%S%z %Z", time.localtime())))
            service = self.build('alertcenter', 'v1beta1', http=self.http)
            start_time = time.strftime("%Y-%m-%dT%H:%M:%S", (time.localtime(int(chkpnt.split(".")[0]))))
            self.log.debug("action=create_start_time zero_chkpnt={} int_chkpnt={} localtime={} start_time={}".format(
                chkpnt.split(".")[0],
                int(chkpnt.split(".")[0]),
                time.localtime(int(chkpnt.split(".")[0])),
                start_time
            ))
            # ASA-211 TZ parsing is weird. Google must either have "Z" or [+-]\d\d:\d\d neither of which is native to python
            # ASA-248 Problems with strftime and localtime in Python causes issues in data collection
            my_local_tz = time.strftime("%z")
            last_two = my_local_tz[-2:]
            first_two = my_local_tz[:-2]
            myTZ = "{}:{}".format(first_two, last_two)
            start_time = "{}{}".format(start_time, myTZ)
            self.info("operation=setting_api_constraints_time special={} application_name={}".format(start_time,
                                                                                                     application_name))
            self.info(
                "operation=setting_api_constraints_time start_time={} end_time={} application_name={}".format(
                    start_time,
                    "REMOVED",
                    application_name))
            total_count = 0
            page_token = None
            filter_items = ['createTime>="{}"'.format(start_time)]
            alert_transpose = {"token": "Domain wide takeout",
                               "gmail": "Gmail phishing",
                               "identity": "Google identity",
                               "operations": "Google Operations",
                               "state": "State Sponsored Attack",
                               "mobile": "Mobile device management"}
            source = self.get_config("src")
            if source != "all":
                filter_items.append('source="{}"'.format(alert_transpose[source]))
            params = {'filter': " AND ".join(filter_items)}
            thread_params = {"st": "alerts", "tf": "createTime", "app_name": application_name}
            self.log.info("action=params filter={} thread_params={}".format(params['filter'], thread_params))
            while True:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug("operation=has_page application_name={} token={}".format(application_name, page_token))
                    self.debug("operation=has_page application_name={} param_type={} params={}".format(application_name,
                                                                                                       type(params),
                                                                                                       params))
                    current_page = service.alerts().list(**params).execute()
                    self.debug(
                        "operation=has_page application_name={} current_page={}".format(application_name,
                                                                                        list(current_page.keys())))
                    if "alerts" in current_page:
                        self.debug("operation=has_items_in_page")
                        p = mp.Pool(10)
                        matrix = [(num,
                                   self.process_alert_api_evts(result, source),
                                   thread_params)
                                  for num, result in enumerate(current_page["alerts"])]
                        p.starmap(self._print_threaded, matrix)
                        p.close()
                        p.join()
                        # NOTICE THAT "time" is not valid. it is "id.time", but will need to refactor to fix.
                        total_count += total_count + len(current_page["alerts"])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    self.log.error("error={}".format(e))
                    self._catch_error(e)
                    break
            self.info(
                "action=found_events num_events={0} application_name={1} start_time=\"{2}\"".format(
                    total_count, application_name, start_time))
            if total_count > 0:
                self.log.info(
                    "action=saving_checkpoint checkpoint_file={} checkpoint={} items_found={} application_name={}".format(
                        chkpnt_name,
                        chkpnt,
                        total_count,
                        application_name))
                self._set_checkpoint(chkpnt_name, checkpoint_time=chkpnt_now)
            else:
                self.log.warn("action=saving_checkpoint "
                              "msg='not saving checkpoint in case there was a communication error' "
                              "start={} items_found={} application_name={}".format(start_time, total_count,
                                                                                   application_name))
            try:
                self.log.debug("application_name={} start_time={} chckpnt_now={} num_events={}".format(
                    application_name, start_time, chkpnt_now, total_count
                ))
            except Exception as e:
                self.log.error("error={}".format(e))
                self._catch_error(e)
        except Exception as e:
            self._catch_error(e)
            raise e

    # ##### END ALERTS ####
    # ##### THREADED PRINTERS #####
    def _print_threaded_pubsub(self, num, evt, ack_ids):
        try:
            ack_ids.append(evt.ack_id)
            data = ""
            try:
                data = json.loads(str(evt.message.data, 'UTF-8'))
            except:
                data = str(evt.message.data, 'UTF-8')
            self.print_event(json.dumps({"data": data}), sourcetype="google:workspaces:pubsub")
        except Exception as e:
            self._catch_error(e, {"num": num, "evt": evt, "ack_ids": ack_ids})

    def _print_threaded_directory(self, num, evt, kw):
        try:
            do_email_forward = self.get_config("email_forward_check", "false")
            if do_email_forward is None:
                do_email_forward = "false"
            uid = evt.get("primaryEmail", "me")
            self.log.debug(
                "action=print_threaded_directory num={} primaryEmail={} email_forward_check={}".format(num, uid,
                                                                                                       do_email_forward))
            if do_email_forward.lower() in ["1", "true", 1]:
                self.log.debug("action=accessing_gmail_settings id={} evt={}".format(uid, list(evt.keys())))
                try:
                    results = self.secondary_service.users().settings().forwardingAddresses().list(userId=uid).execute()
                    self.log.debug("action=forwarding_settings userId={} settings={}".format(uid, results))
                    if "forwardingAddresses" in results:
                        if "mail" not in evt.keys():
                            evt["mail"] = {}
                        if "settings" not in evt["mail"]:
                            evt["mail"]["settings"] = {}
                        evt["forwardingAddresses"] = results["forwardingAddresses"]
                except Exception as e:
                    self.log.warn("action=forwarding_settings userId={} action_status=failed e={}".format(uid, e))
            self.log.debug("action=after_forward_settings num={} evt={}".format(num, list(evt.keys())))
            self._print_threaded(num, evt, kw)
        except Exception as e:
            self.log.warn(
                "action=caught_error  error_type={} error={} num={} kw={} evt={}".format(type(e), e, num, kw,
                                                                                         list(evt.keys())))
            self._catch_error(e, {"num": num, "evt": evt})

    def _print_threaded(self, num, evt, kw):
        try:
            st = kw.get("st", None)
            s = kw.get("s", None)
            tf = kw.get("tf", "time")
            self.log.debug(
                "action=print_threaded_event num={} st={} s={} tf={} evt={}".format(num,
                                                                                    "{}:{}".format(self.base_st, st), s,
                                                                                    tf, list(evt.keys())))
            self.print_event(json.dumps(evt), time_field=tf, sourcetype="{}:{}".format(self.base_st, st), source=s)
        except Exception as e:
            self.log.warn(
                "action=caught_error  error_type={} error={} num={} kw={} evt={}".format(type(e), e, num, kw,
                                                                                         list(evt.keys())))
            self._catch_error(e, {"num": num, "evt": evt})

    def _print_threaded_usage(self, num, evt, kw):
        try:
            st = kw.get("st", None)
            s = kw.get("s", None)
            tf = kw.get("tf", "time")
            self.log.debug(
                "action=print_threaded_event num={} st={} s={}".format(num, "{}:{}".format(self.base_st, st), s))
            self.print_event(json.dumps(self._usage_fix(evt)), time_field=tf,
                             sourcetype="{}:{}".format(self.base_st, st), source=s)
        except Exception as e:
            self._catch_error(e, {"num": num, "evt": evt})

    # ##### END THREADED PRINTERS #####
    # ##### ADMIN REPORTS ####
    def get_admin_report(self, user_key="all", app_name=None):
        try:
            domain = self.get_config("domain")
            clean_user_key = ''.join(uke for uke in user_key if uke.isalnum())
            if app_name is None:
                application_name = self.get_config("application_name")
                chkpnt_name = f"{self.get_config('guid')}-domain-{domain}_report-{application_name}.txt"
            else:
                application_name = app_name
                chkpnt_name = f"{self.get_config('guid')}-{clean_user_key}-{domain}_report-{application_name}.txt"
            self.log.debug("problem_type=checkpoint chkpnt_name={}".format(chkpnt_name))
            lb = self.get_config("lookback")
            self.log.debug(
                "problem_type=checkpoint action=evaluating_lookback application_name={} lookback={} lookback_type={}".format(
                    application_name,
                    lb, type(lb)))
            if int(lb) > 0:
                self.log.debug(
                    "problem_type=checkpoint action=evaluating_lookback application_name={} new_lookback={}".format(
                        application_name,
                        (int(lb) * 1440)))
                self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
            chkpnt_obj = self._get_checkpoint(chkpnt_name)
            self.log.debug("problem_type=checkpoint application_name={} chkpnt_obj={}".format(application_name,
                                                                                              json.dumps(chkpnt_obj)))
            chkpnt = "{}".format(chkpnt_obj["last_execution"])
            self.log.debug("problem_type=checkpoint application_name={} chkpnt={}".format(application_name, chkpnt))
            chkpnt_now = int(time.time())
            self._checkpoint_now_by_event = chkpnt_now
            # GOOG-22 Updated the int call to account for floats in the checkpoint.
            self.log.debug(
                "problem_type=checkpoint application_name={} chkpnt_now={} chkpnt_diff={}".format(application_name,
                                                                                                  chkpnt_now,
                                                                                                  chkpnt_now - int(
                                                                                                      f"{chkpnt.split('.')[0]}")))
            self.sourcetype("google:workspaces:report:{}".format(application_name))
            self.info(
                "problem_type=checkpoint function=adminReportV1 status=starting application_name={} time_of_gmtime={} timezone_of_localtime={}".format(
                    application_name, time.strftime("%Y-%m-%dT%H:%M:%S%z  %Z", time.gmtime()),
                    time.strftime("%Y-%m-%dT%H:%M:%S%z %Z", time.localtime())))
            service = self.build('admin', 'reports_v1', http=self.http)
            start_time = time.strftime("%Y-%m-%dT%H:%M:%S", (time.localtime(int(chkpnt.split(".")[0]))))
            # ASA-211 TZ parsing is weird. Google must either have "Z" or [+-]\d\d:\d\d neither of which is native to python
            # ASA-248 Problems with strftime and localtime in Python causes issues in data collection
            my_local_tz = time.strftime("%z")
            last_two = my_local_tz[-2:]
            first_two = my_local_tz[:-2]
            myTZ = "{}:{}".format(first_two, last_two)
            start_time = "{}{}".format(start_time, myTZ)
            self.log.debug(
                "problem_type=checkpoint application_name={} local_tz={} last_two={} first_two={} myTZ={} start_time={}".format(
                    application_name, my_local_tz, last_two, first_two, myTZ, start_time
                ))
            self.info(
                "problem_type=checkpoint operation=setting_api_constraints_time special={} application_name={}".format(
                    start_time,
                    application_name))
            self.info(
                "problem_type=checkpoint operation=setting_api_constraints_time start_time={} end_time={} application_name={}".format(
                    start_time,
                    "REMOVED",
                    application_name))
            total_count = 0
            page_token = None
            params = {'applicationName': application_name, 'userKey': user_key, 'startTime': start_time}
            self.info(
                "problem_type=checkpoint operation=starting_while_loop_for_pages application_name={} start_time={} checkpoint={}".format(
                    application_name, start_time, chkpnt))
            thread_params = {"st": "admin:report:{}".format(application_name), "tf": "time", "app": application_name}
            # removed a weird client_id thing for token application name. Not sure why there.
            while True:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug("operation=has_page application_name={} token={}".format(application_name, page_token))
                    self.debug("operation=has_page application_name={} param_type={} params={}".format(application_name,
                                                                                                       type(params),
                                                                                                       params))
                    current_page = service.activities().list(**params).execute()
                    self.debug(
                        "operation=has_page application_name={} page_items_length={} current_page={}".format(
                            application_name,
                            len(current_page["items"]) if "items" in current_page else 0,
                            list(current_page.keys())))
                    if "items" in current_page:
                        self.debug("operation=has_items_in_page")
                        p = mp.Pool(10)
                        matrix = [(num,
                                   self.process_admin_api_evts(result),
                                   thread_params)
                                  for num, result in enumerate(current_page["items"])]
                        p.starmap(self._print_threaded, matrix)
                        p.close()
                        p.join()
                        # NOTICE THAT "time" is not valid. it is "id.time", but will need to refactor to fix.
                        total_count += total_count + len(current_page["items"])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    self.log.error("error={}".format(e))
                    self._catch_error(e)
                    break
            self.info(
                "problem_type=checkpoint action=found_events num_events={0} application_name={1} start_time=\"{2}\"".format(
                    total_count, application_name, start_time))
            if total_count > 0:
                self.log.info(
                    "problem_type=checkpoint action=saving_checkpoint checkpoint={} items_found={} application_name={}".format(
                        self._checkpoint_now_by_event,
                        total_count,
                        application_name))
                self.log.debug(
                    "problem_type=checkpoint application_name={} action=setting_checkpoint chkpnt_name={} checkpoint_time={} event_checkpoint_time={}".format(
                        application_name, chkpnt_name, chkpnt_now, self._checkpoint_now_by_event))
                self._set_checkpoint(chkpnt_name, checkpoint_time=self._checkpoint_now_by_event)
            else:
                self.log.debug(
                    "problem_type=checkpoint action=not_setting_checkpoint start={} items_found={} application_name={}".format(
                        start_time, total_count, application_name))
                self.log.warn("action=saving_checkpoint "
                              "msg='not saving checkpoint in case there was a communication error' "
                              "start={} items_found={} application_name={}".format(start_time, total_count,
                                                                                   application_name))
            try:
                self.log.debug(
                    "problem_type=checkpoint application_name={} start_time={} chckpnt_now={} num_events={}".format(
                        application_name, start_time, chkpnt_now, total_count
                    ))
            except Exception as e:
                self.log.error("error={}".format(e))
                self._catch_error(e)
        except Exception as e:
            self._catch_error(e)
            raise e

    def process_admin_api_evts(self, evt):
        try:
            # _checkpoint_now_by_event
            evt_time = 1
            if "events" in evt:
                for event in evt["events"]:
                    if "parameters" in event:
                        for param in event["parameters"]:
                            if "value" in param:
                                param[param["name"]] = param["value"]
                            elif "intValue" in param:
                                param[param["name"]] = param["intValue"]
                            elif "multiValue" in param:
                                param[param["name"]] = param["multiValue"]
                            elif "boolValue" in param:
                                param[param["name"]] = param["boolValue"]
                            else:
                                if "multiMessageValue" in param:
                                    for pp in param["multiMessageValue"]:
                                        if "parameter" in pp:
                                            for pewpew in pp["parameter"]:
                                                if "value" in pewpew:
                                                    param[pewpew["name"]] = pewpew["value"]
                                                elif "intValue" in pewpew:
                                                    param[pewpew["name"]] = pewpew["intValue"]
                                                elif "multiValue" in pewpew:
                                                    param[pewpew["name"]] = pewpew["multiValue"]
                                                elif "boolValue" in pewpew:
                                                    param[pewpew["name"]] = pewpew["boolValue"]
                                                else:
                                                    param[pewpew["name"]] = "NO NESTED VALUE DETECTED"
                                else:
                                    param[param["name"]] = "NO VALUE DETECTED"
            offset = 0
            try:
                evt_raw_time = evt.get("id", {}).get("time", "")
                evt_time = int(
                    datetime.strptime(evt_raw_time, "%Y-%m-%dT%H:%M:%S.%fZ").astimezone(tzlocal()).strftime("%s"))
                evt["time"] = evt_raw_time
                evt["timestamp"] = evt_raw_time
                offset = round((datetime.utcnow() - datetime.now()).total_seconds())
                self.log.debug(
                    "action=datalock checkpoint_now={} event_time={} evt_raw_time={} offset={} self_evt={}".format(
                        self._checkpoint_now_by_event,
                        evt_time,
                        evt_raw_time,
                        offset,
                        self._checkpoint_now_by_event < evt_time - offset))
            except Exception as e:
                self.log.debug("action=datalock exception={}".format(e))
            # This is comparing "local time" with "utc time". Needs to adjust
            if self._checkpoint_now_by_event < evt_time - offset:
                self.log.info(
                    "action=datalock msg='checkpoint time is smaller than event time. Updating Checkpoint time' chkpoint={} evt={}".format(
                        self._checkpoint_now_by_event, evt_time))
                self._checkpoint_now_by_event = evt_time
            return evt
        except Exception as e:
            self._catch_error(e)

    # ##### END ADMIN REPORTS ####
    # ### GOOGLE VAULT ####
    def _setup_vault(self):
        self.service = self.build('vault', 'v1', http=self.http)

    def list_matters(self):
        self._setup_vault()
        list_response1 = self.service.matters().list(view='FULL', pageSize=10).execute()
        self.print_multiple_events(list_response1['matters'])

    # ### END VAULT ####
    # #### CLASSROOM ####
    def get_classroom(self):
        try:
            self.service = self.build('classroom', 'v1', http=self.http)
            course_ids = self.get_config("course_ids")
            write_courses = self.get_config("write_courses") == "1"
            service_name = self.get_config("servicename")
            self.log.info("action=start_classroom course_ids={} write_courses={} service_name={}".format(
                course_ids, write_courses, service_name))
            courses = self.courses(write_courses=(self.get_config("write_courses") == "1"))
            self.log.debug("action=got_courses courses={}".format(courses))
            # Thread this for all the courses in teh courses varaible,
            # remove the service, and add in threaded output on the paginator.
            # self_functions[service_name](course=kwargs.get("course"), service=self.service)
            p = mp.Pool(10)
            matrix = [(service_name, x) for x in courses]
            p.starmap(self.threaded_classroom_report, matrix)
            p.close()
            p.join()
            return
        except Exception as e:
            self._catch_error(e)

    def courses(self, write_courses=False):
        try:
            function_name = "courses"
            self.info("function={} status=starting write_courses={}".format(function_name, write_courses))
            self.sourcetype("google:workspaces:classroom:courses")
            page_token = None
            local_count = 0
            total_count = 0
            error_found = False
            params = {}
            course_ids = []
            courses = []
            config_courses = self.get_config("course_ids")
            if config_courses is not None:
                courses = config_courses.split(",")
            self.log.info("action=restrict_courses courses={}".format(courses))

            def add_course_id(course=None, service=None):
                if course["id"] in courses or len(courses) < 1:
                    course_ids.append(course["id"])
                return course

            while True and not error_found:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    self.debug("function={} page_token={}".format(function_name, page_token))
                    current_page = self.service.courses().list(**params).execute()
                    self.debug("function={} got_current_page".format(function_name))
                    if "courses" in current_page:
                        writeThem = [add_course_id(x) for x in current_page["courses"]]
                        if write_courses:
                            self.print_multiple_events(writeThem, time_field="updateTime")
                        total_count = total_count + len(current_page["courses"])
                        local_count = local_count + len(current_page["courses"])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    self.log.warn(
                        "function={} action=caught_admin_error error_type={} error={}".format(function_name, type(e),
                                                                                              e))
                    error_found = True
                    break
            return course_ids
        except Exception as e:
            self._catch_error(e)

    def threaded_classroom_report(self, report, course):
        try:
            self_functions = {
                "courses:aliases": self.courses_aliases,
                "courses:topics": self.courses_topics,
                "classroom:invitations": self.classroom_invitations,
                "courses:announcements": self.courses_announcements,
                "courses:work": self.courses_work,
                "courses:students": self.courses_students,
                "courses:teachers": self.courses_teachers
            }
            if report not in self_functions:
                self.log.warn("report={} error=not_found".format(report))
            return self_functions[report](course=course)
        except Exception as e:
            self.log.warn("report={} error={} course={}".format(report, e, course))
            self._catch_error(e)

    def courses_announcements(self, course=None):
        return self.classroom_paginator(self.service.courses().announcements(), "announcements", course)

    def courses_work(self, course=None):
        return self.classroom_paginator(self.service.courses().courseWork(), "courseWork", course)

    def courses_students(self, course=None):
        return self.classroom_paginator(self.service.courses().students(), "students", course)

    def courses_teachers(self, course=None):
        return self.classroom_paginator(self.service.courses().teachers(), "teachers", course)

    def courses_aliases(self, course=None):
        return self.classroom_paginator(self.service.courses().aliases(), "aliases", course)

    def courses_topics(self, course=None):
        return self.classroom_paginator(self.service.courses().topics(), "topic", course)

    def classroom_invitations(self, course=None):
        return self.classroom_paginator(self.service.invitations(), "invitations", course)

    def classroom_threader(self, evt, sourcetype, source):
        self.print_event(json.dumps(evt), sourcetype=sourcetype, source=source)

    def classroom_paginator(self, api_caller, objecti, course=None, service=None):
        try:
            self.log.info("status=starting objecti={}".format(objecti))
            page_token = None
            local_count = 0
            total_count = 0
            error_found = False
            params = {"courseId": course}
            while True and not error_found:
                try:
                    if page_token:
                        params['pageToken'] = page_token
                    else:
                        self.log.warn("action=no_more_pages objecti={} course={}".format(objecti, course))
                    self.debug("page_token={}".format(page_token))
                    current_page = api_caller.list(**params).execute()
                    self.debug("got_current_page")
                    if objecti in current_page:
                        p = mp.Pool(10)
                        matrix = [(x,
                                   "google:workspaces:classroom:courses:{}".format(objecti),
                                   "google:workspaces:input:{}".format(self.get_config("guid")))
                                  for x in current_page[objecti]]
                        p.starmap(self.classroom_threader, matrix)
                        p.close()
                        p.join()
                        total_count = total_count + len(current_page[objecti])
                        local_count = local_count + len(current_page[objecti])
                    page_token = current_page.get('nextPageToken')
                    if not page_token:
                        break
                except Exception as e:
                    self.log.error(
                        "action=error_found error_message=\"objecti={} course={} {}\" error_type={} ".format(objecti,
                                                                                                             course, e,
                                                                                                             type(e)))
                    self._catch_error(e)
                    error_found = True
                    break
        except Exception as e:
            self._catch_error(e)

    # #### END CLASSROOM ####
    # START Big Query

    def _bigquery_table_information(self, table):
        dataset = self.get_config("dataset")
        project = self.get_config("project")
        dataset_ref = self.service.dataset(dataset, project=project)
        table_ref = dataset_ref.table(table)
        table = self.service.get_table(table_ref)
        # Get Checkpoint, setting execution times and last calls
        return table

    def bigquery_ingest_all_tables(self):
        """
        Using the checkpoint for the project/dataset, keep track of 1) table name, and 2) last index.
        If "table.num_rows" > last_index, then consume from there. for now, do this for all tables.
        It's not scalable, but I can fix that later.
        :param project:
        :param dataset:
        :return:
        """
        try:
            self.log.info(
                "action=starting project={} dataset={}".format(self.get_config("project"), self.get_config("dataset")))

            # TODO: Add proxy support for bigquery
            self.service = self.bigquery.Client(project=self.get_config("project"),
                                                credentials=self.non_delegated_credential)
            dataset_ref = self.service.dataset(self.get_config("dataset"), project=self.get_config("project"))
            self.log.info("action=get_dataset_ref ref={}".format(dataset_ref))
            table_types = ["TABLE", "VIEW"]
            if self.get_config("ingest_type") == "vrow":
                table_types = ["VIEW"]
            tables = [(t.table_id, "vrow" if t._properties["type"] == "VIEW" else "row") for t in
                      [self._bigquery_table_information(t.table_id) if t._properties["type"] in table_types else None
                       for t in
                       self.service.list_tables(dataset_ref)] if t]
            self.log.info("action=get_dataset_ref tables={}".format(tables))
            p = mp.Pool(10)
            p.starmap(self.get_table_results, tables)
            p.close()
            p.join()
        except Exception as e:
            self._catch_error(e)

    def get_table_results(self, table, ingest_type, activity_logs=False):
        try:
            # TODO: Add proxy support for bigquery
            self.service = self.bigquery.Client(project=self.get_config("project"),
                                                credentials=self.non_delegated_credential)
            project = self.get_config("project")
            dataset = self.get_config("dataset")
            start_row = self.get_config("start_row")
            pastafarian = self.get_config("enriched_pasta")
            table_information = self._bigquery_table_information(table)
            self.log.info(
                "action=start_table_consume table={} project={} dataset={} start_row={} ingest_type={}".format(
                    table, project, dataset, start_row, ingest_type
                ))
            if self.get_config("consume_table_info"):
                self.print_multiple_events([{"table_information": "{}".format(table_information.__dict__)}],
                                           sourcetype="google:workspaces:bigquery:table:information",
                                           source="google:workspaces:bigquery:table:information:{}".format(table))
            _chkpoint = self._load_bq_table_information_checkpoint(dataset, table_information)
            self.log.warn("action=set_table_checkpoint action=Loaded_checkpoint chkpoint={}".format(_chkpoint))
            if (ingest_type == "row") and \
                    (table_information.num_rows <= _chkpoint["last_row"] or table_information.num_rows == 0):
                self.log.info(
                    "action=stop_execution project={} dataset={} table_information={} last_row={} num_rows={}".format(
                        project, dataset, table, _chkpoint.get("last_row"), table_information.num_rows
                    ))
                return
            self.log.info(
                "action=did_not_stop_execution project={} dataset={} table_information={} last_row={} num_rows={}".format(
                    project, dataset, table, _chkpoint.get("last_row"), table_information.num_rows
                ))
            fields = table_information.schema[:]
            extra_params = {"selected_fields": fields}
            last_row = _chkpoint["last_row"]
            first_run = _chkpoint["first_run"]
            self.log.info("action=checkpoint first_run={} type_first_run={}".format(first_run, type(first_run)))
            last_checkpoint = int(math.floor(_chkpoint["last_execution"]))
            _chkpoint["last_execution"] = int(math.floor(time.time()))
            self.log.warn(
                "action=set_table_checkpoint last_execution={} last_row={}".format(_chkpoint["last_execution"],
                                                                                   last_row))
            start_index = start_row
            if start_row is not None and int(start_row) > int(last_row):
                self.log.info("action=setting_start_row start_row={} last_row={}".format(start_row, last_row))
                extra_params["start_index"] = start_row
            else:
                self.log.info("action=setting_start_row last_row={}".format(last_row))
                extra_params["start_index"] = last_row
                start_index = last_row
            extra_params["max_results"] = int(self.get_config("max_rows", 250000))
            self.log.info("action=list_rows ingest_type={} extra_params={}".format(ingest_type, len(extra_params)))
            rows = []
            time_field = "timestamp"
            if ingest_type == "time":
                time_field = pastafarian
                if first_run and len("{}".format(start_index)) == 10:
                    last_checkpoint = int(start_index)
                else:
                    self.log.warn(
                        "action=setting_checkpoint status=failure start_index={} last_checkpoint={} length_start_index={}".format(
                            start_index, last_checkpoint, len("{}".format(start_index))
                        ))
                t_time = datetime.fromtimestamp(last_checkpoint).astimezone()
                query = "SELECT * FROM `{}.{}.{}` WHERE {} >= TIMESTAMP(\"{}\", \"{}\")".format(
                    project, dataset, table, pastafarian, t_time.strftime("%Y-%m-%d %H:%M:%S"), t_time.strftime("%Z"))
                self.log.info("action=ingest_type ingest_type={} query='{}'".format(ingest_type, query))
                timejob = self.service.query(query)
                rows = timejob.result()
                # FIX THE TIMESTAMP ISSUE FOR THE FIELDS
                # SELECT * FROM `<project>.<dataset>.<table>` WHERE event_info.timestamp_usec>1627572755827619 LIMIT 100
            elif ingest_type == "query":
                if first_run and len("{}".format(start_index)) == 10:
                    last_checkpoint = int(start_index)
                else:
                    self.log.warn(
                        "action=setting_checkpoint status=failure start_index={} last_checkpoint={} length_start_index={}".format(
                            start_index, last_checkpoint, len("{}".format(start_index))
                        ))
                query = pastafarian.replace("##TIMESTAMP##", "{}".format(last_checkpoint))
                self.log.warn("action=ingest_type ingest_type={} query='{}'".format(ingest_type, query))
                job = self.service.query(query)
                rows = job.result()
                # FIX THE TIMESTAMP ISSUE FOR THE FIELDS
            elif ingest_type == "row":
                rows = self.service.list_rows(table_information, **extra_params)
            elif ingest_type == "vrow":
                sql = table_information._properties["view"]["query"]
                self.log.info("action=sql sql={}".format(sql))
                query = "{} LIMIT {} OFFSET {}".format(sql, extra_params["max_results"], extra_params["start_index"])
                self.log.info("action=get_table_vrow sql={} table={}".format(query, table))
                job = self.service.query(query)
                rows = job.result()
            else:
                raise NotImplementedError("Big Query Ingest Type Not Implemented: {}".format(ingest_type))
            # Find the first occurance of a timestamp field. If none, it becomes ingest time.
            if ingest_type in ["vrow", "row", "query"]:
                for field in rows.schema:
                    self.log.info("action=check_for_time field_name={} field_type={}".format(field.name,
                                                                                             field.field_type))
                    if "{}".format(field.field_type) == "TIMESTAMP":
                        time_field = field.name
                        break
                    if "{}".format(field.name) == "event_info":
                        time_field = "event_info"
                if time_field == "timestamp" and pastafarian:
                    time_field = pastafarian
            self.log.info("action=set_time_field time_field={}".format(time_field))
            self.sourcetype("google:workspaces:bigquery:table:data")
            start_row = self.get_config("start_row")
            p = mp.Pool(10)
            self.bigquery_threaded_data["row_counter"] = 0
            field_names = [field.name for field in rows.schema]
            p.starmap(self.threaded_bigquery_report,
                      [(row, time_field, table, field_names, activity_logs) for row in rows])
            p.close()
            p.join()
            row_count = self.bigquery_threaded_data["row_counter"]
            last_row_index = int(extra_params["start_index"]) + row_count
            _chkpoint["last_row"] = last_row_index
            self.log.warn("action=set_table_checkpoint row_count={} last_row_index={} _checkpoint={}".format(row_count,
                                                                                                             last_row_index,
                                                                                                             _chkpoint))
            self.log.info(
                "action=setting_checkpoint project={} dataset={} table_information={} last_row={} num_rows={} added_rows={}".format(
                    project, dataset, table, _chkpoint.get("last_row"), table_information.num_rows, row_count
                ))
            self._set_bq_table_information_checkpoint(dataset, table_information, _chkpoint)
            return
        except Exception as e:
            self._catch_error(e)

    def _check_cell_values(self, cell_value):
        if isinstance(cell_value, dict):
            return cell_value
        return "{!s:<16}".format(cell_value)

    def threaded_bigquery_report(self, row, time_field, table, field_names, activity_logs=False):
        try:
            self.bigquery_threaded_data["row_counter"] += 1
            row_object = {field_names[i]: self._check_cell_values(row[i]) for i in range(len(row))}
            tf = time_field
            if time_field == "event_info.timestamp_usec":
                try:
                    row_object["bigquery_time_field"] = int(
                        "{}".format(row_object.get("event_info", {}).get("timestamp_usec", 1000000))) / 1000000
                except Exception as e:
                    self.log.error("action=set_time_field tf={} has_event_info={} has_timestamp_usec={}"
                                   .format(tf,
                                           "event_info" in row_object,
                                           "timestamp_usec" in row_object.get("event_info", {})))
                    self._catch_error(e)
            elif len(re.findall(r'.*usec.*', time_field, re.IGNORECASE)) > 0:
                try:
                    row_object["bigquery_time_field"] = int("{}".format(row_object.get(tf, 1000000))) / 1000000
                except Exception as e:
                    self.log.error("action=set_time_field tf={} has_event_info={} has_timestamp_usec={}"
                                   .format(tf,
                                           "event_info" in row_object,
                                           "timestamp_usec" in row_object.get("event_info", {})))
                    self._catch_error(e)
            else:
                row_object["bigquery_time_field"] = row_object.get("bigquery_time_field", row_object.get(tf, None))
                if row_object["bigquery_time_field"] is None:
                    row_object["bigquery_time_field"] = time.time()
            row_object["bq_field_of_time"] = tf
            self.log.debug("action=set_time_field  tf={} value={}".format(tf, row_object.get(tf, "NotAvail")))
            if activity_logs:
                self.log.warn("action=Consume_Activity_Logs msg=not_implemented")
            else:
                self.print_multiple_events([row_object],
                                           time_field=tf,
                                           sourcetype="google:workspaces:bigquery:table:data",
                                           source="google:workspaces:bigquery:{}:{}:{}:{}".format(
                                               self.get_config("project"),
                                               self.get_config("dataset"),
                                               table,
                                               self.get_config(
                                                   "short_guid")))
        except Exception as e:
            self.log.warn(
                "action=caught_error error_type={} error={} table={} row={}".format(type(e), e, table, row))
            self._catch_error(e)

    def _load_bq_table_information_checkpoint(self, dataset, table):
        # 1609557959
        _chkpoint_key = "{}_{}_{}_{}.txt".format(
            self.get_config("domain"), dataset, table.table_id, self.get_config("short_guid", "")).replace(":", '_')
        _chkpoint = self._get_checkpoint(_chkpoint_key)
        self.log.debug("action=checkpoint found_checkpoint {}".format(_chkpoint))
        if _chkpoint.get("last_row") is None:
            self.log.debug("action=checkpoint checkpoint None")
            _chkpoint = {"num_rows": 0, "last_row": 0, "first_run": True}
            self._set_object_checkpoint(_chkpoint_key, time.time(), _chkpoint)
            self.log.debug("action=checkpoint checkpoint set {}".format(_chkpoint))
        t = _chkpoint.get("first_run", False)
        _chkpoint["first_run"] = normalizeBoolean(t)
        self.log.info("action=checkpoint type=configured_checkpoint checkpoint={}".format(_chkpoint))
        return _chkpoint

    def _set_bq_table_information_checkpoint(self, dataset, table, data):
        _chkpoint_key = "{}_{}_{}_{}.txt".format(
            self.get_config("domain"), dataset, table.table_id, self.get_config("short_guid")).replace(":", '_')
        current_checkpoint = self._get_checkpoint(_chkpoint_key)
        self.log.warn("action=set_table_checkpoint current_checkpoint={}".format(current_checkpoint))
        self.log.warn("action=set_table_checkpoint settingtable={} data={}".format(table.table_id, data))
        current_checkpoint = data
        current_checkpoint["total_table_rows"] = table.num_rows
        current_checkpoint["first_run"] = False
        self.log.warn("action=set_table_checkpoint setting_checkpoint={} contents={}".format(_chkpoint_key,
                                                                                             current_checkpoint))
        self._set_object_checkpoint(_chkpoint_key, data["last_execution"], current_checkpoint)

    # END Big Query
    # #### CHECKPOINT HELPERS ####
    def _set_object_checkpoint(self, chkpnt_name, checkpoint_time, obj):
        try:
            chkpointfile = os.path.join(self._config["checkpoint_dir"],
                                        "{}_{}".format(self.host(), chkpnt_name)).replace(":", "_")
            t = obj
            t["last_execution"] = checkpoint_time
            self.log.info(f"action=saving_checkpoint filename={chkpointfile} contents={json.dumps(t)}")
            self._write_file(chkpointfile, json.dumps(t))
            return True
        except Exception as e:
            self._catch_error(e)
            return False

    def _set_checkpoint(self, chkpnt_name, checkpoint_time):
        try:
            # So to avoid "long runs" and "time lapse" in checkpointing,
            # if no time is passed, use the time the checkpoint was loaded.
            # if "now" is passed, use "now". Can I haz tautology?
            # First identified in ASA-3
            chkpointfile = os.path.join(self._config["checkpoint_dir"],
                                        "{}_{}".format(self.host(), chkpnt_name)).replace(":", "_")
            self._write_file(chkpointfile, json.dumps({
                "last_execution": "{}".format(checkpoint_time)
            }))
            return True
        except Exception as e:
            self._catch_error(e)
            return False

    def _get_checkpoint(self, key):
        chk_time = 0
        chkpointfile = os.path.join(self._config["checkpoint_dir"], "{}_{}".format(self.host(), key)).replace(":", "_")
        self._loaded_checkpoints[key] = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
        self.debug("action=set_checkpoint_load_time problem_type=checkpoint key={} loaded_time={}".format(chkpointfile,
                                                                                                          self._loaded_checkpoints[
                                                                                                              key]))
        try:
            if os.path.isfile(chkpointfile):
                self.debug(
                    "action=file_exists_checkpoint problem_type=checkpoint checkpoint_file='{}'".format(chkpointfile))
                chk_time = self._read_file(chkpointfile)
                self.debug(
                    "action=found_checkpoint_value problem_type=checkpoint key={} value={}".format(key, chk_time))
                chk_time = json.loads(chk_time)
            else:
                # assume that this means the checkpoint is not there
                # Let's Default to 60 minutes ago. Just to start pulling data.
                # TODO: Make loading a checkpoint configurable in respect to the look back time (in minutes)
                self.debug("action=set_default_checkpoint problem_type=checkpoint  key={}".format(key))
                wibbly_wobbly_timey_wimey = datetime.utcnow() - timedelta(
                    minutes=self.checkpoint_default_lookback())
                chk_time = (wibbly_wobbly_timey_wimey - datetime.utcfromtimestamp(0)).total_seconds()
                chk_time = {"last_execution": float(chk_time)}
                self.debug(
                    "action=set_default_checkpoint problem_type=checkpoint  chkpnt={}".format(json.dumps(chk_time)))
        except Exception as e:
            self._catch_error(e)
        self.debug("Returning CheckPoint Time {}".format(chk_time))
        return chk_time

    # #### END CHECKPOINT HELPERS ####

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        return True

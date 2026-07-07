import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as util
from KennyLoggins import KennyLoggins
import json
import logging
import os
import hashlib
import splunk
import six
from google_utilities import GSuiteUtilities
from google_constants import app_name
from datetime import timedelta
from datetime import datetime

from google_constants import global_scopes

os.environ.setdefault("CRYPTOGRAPHY_ALLOW_OPENSSL_102", "1")
sys.path.insert(0, make_splunkhome_path(["etc", "apps", app_name, "lib"]))
sys.path.append(make_splunkhome_path(["etc", "apps", app_name, "lib"]))
os.environ["PYTHONPATH"] = ",".join(sys.path)

from apiclient.discovery import build
from google.oauth2 import service_account
import google_auth_httplib2
import urllib

if sys.platform == "win32":
    import msvcrt

    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

logger = KennyLoggins(app_name, "ga_api_metadata", logging.INFO)

# Google Stuff
import httplib2

httplib2.CA_CERTS = "{}/{}".format(os.path.join(util.get_apps_dir(), app_name, 'bin'), "cacerts.txt")
_LOCALDIR = os.path.join(util.get_apps_dir(), app_name, 'local')
if not os.path.exists(_LOCALDIR):
    os.makedirs(_LOCALDIR)


def get_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


class handle(splunk.rest.BaseRestHandler):
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        splunk.rest.BaseRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
        self.utils = GSuiteUtilities(app_name=app_name, session_key=sessionKey)
        self.gw_credential = None
        self.proxy = None
        self._rawcredential = self.build = self.non_delegated_credential = None
        self.credential = self.http = self.non_delegated_http = None
        self.service = None
        self.service_v4 = None
        self.service_v4_data = None

    def _catch_error(self, e):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        return "log_level=ERROR exception='{}' exception_type='{}' filename='{}' exception_line='{}' args='{}'".format(
            str(e), type(e), fname, exc_tb.tb_lineno, "{}".format(e)
        ), "{}".format(str(e))

    def setup(self, query_parameters, api, api_version, scopes=None):
        if scopes is None:
            scopes = []
        try:
            credential = query_parameters.get("credential", "").strip().lower()
            logger.debug("action=starting_setup")
            if credential is None:
                raise Exception("No Credential GUID Passed")
            api_key = self.utils.get_credential(app_name,
                                                credential)
            if api_key is None:
                raise Exception("Could not find or decrypt credential with guid {}".format(credential))
            t = self.utils.get_workspace_creds(credential)
            proxy_guid = t.get("proxy_guid", None)
            impersonation_user = t["impersonation_user"]
            logger.debug("action=checking_for_proxy guid={}".format(proxy_guid))
            verify_ssl = True
            proxy_info = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED":
                logger.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = httplib2.socks.PROXY_TYPE_HTTP
                logger.debug("action=checking_ssl use_ssl={}".format(proxy.get("use_ssl")))
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
                logger.info("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                          proxy["proxy_url"]))
            # These are not in the header due to complication issues when including before the path is set.
            # import pkg_resources
            # import importlib
            # importlib.reload(pkg_resources)
            logger.info("action=which_six six={} module={}".format(six.__file__, sys.modules['six']))
            self.build = build
            my_credential = urllib.parse.unquote(api_key)
            self._rawcredential = my_credential
            self.non_delegated_credential = service_account.Credentials.from_service_account_info(
                json.loads(my_credential),
                scopes=scopes)
            self.credential = self.non_delegated_credential.with_subject(impersonation_user)
            logger.info("action=setup_http proxy_info={}".format(proxy_info))
            self.http = google_auth_httplib2.AuthorizedHttp(
                self.credential,
                http=httplib2.Http(proxy_info=proxy_info))
            self.non_delegated_http = google_auth_httplib2.AuthorizedHttp(
                self.non_delegated_credential,
                http=httplib2.Http(proxy_info=proxy_info))
            self.service = self.build(api, api_version, http=self.http)
        except Exception as e:
            logger.error(self._catch_error(e))
            raise e


# Google Spreadsheets
class spreadsheets(handle):
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def handle_GET(self, **kwargs):
        try:
            query = self.request["query"]
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
            self.setup(query, "drive", "v3", scopes=scopes)
            mime_type = "application/vnd.google-apps.spreadsheet"
            query = "mimeType='{}'".format(mime_type)
            status = self.service.files().list(q=query).execute()
            return [{"status": "success", "data": status}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET


# Google Drive Sheets (sheet of a spreadsheet)
class sheets(handle):
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def handle_GET(self, **kwargs):
        try:
            query = self.request["query"]
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
            self.setup(query, "sheets", "v4", scopes=scopes)
            status = self.service.spreadsheets().get(spreadsheetId=query.get("ss_id")).execute()
            return [{"status": "success", "data": status}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET


# Google Analytics Metadata
class metadata(handle):
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def handle_GET(self, **kwargs):
        try:
            query = self.request["query"]
            metadata_type = query.get("type", "all").strip().lower()
            scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
            self.setup(query, 'analyticsadmin', 'v1alpha', scopes=scopes)
            self.service_v4_data = self.build('analyticsdata', 'v1beta', http=self.non_delegated_http)
            status = self.get_metadata(metadata_type, query_parameters=query)
            return [{"status": "success", "data": status}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "data": {
                "code": 400,
                "status": "error",
                "error": clean,
                "data": []
            }}]

    def get_metadata(self, metadata_type="all", **kwargs):
        try:
            ret_object = {
                "code": 200,
                "status": "OK",
                "data": []
            }
            logger.debug(
                "action=metrics_dimensions action=get_metadata type={} kwargs={}".format(metadata_type, kwargs))
            if metadata_type.lower() in ["all", "metrics", "dimensions"]:
                logger.debug("action=metrics_dimensions kwargs={}".format(kwargs))
                results = {}
                qp = kwargs.get("query_parameters", {})
                view = "{}".format(qp.get("view", 0))
                prop_vers = qp.get("property_version", "v4")
                logger.debug(f"action=gw_meta_data_type view={view} version={prop_vers}")
                view = qp.get("view", "")
                results = self.service_v4_data.properties().getMetadata(name=f'{view}/metadata').execute()
                ret_cols = results["metrics"] if "metrics" == metadata_type.lower() else results["dimensions"]
                logger.debug("action=metrics_dimensions_v4 keys={}".format(list(results.keys())))
                ret_object["data"] = ret_cols
                return ret_object
            elif metadata_type in ["view"]:
                try:
                    # These are GA4 Profiles
                    results_v4 = self.service.accounts().list(pageSize=200).execute()
                    logger.info("service_v4={}".format(results_v4))
                    for account in results_v4.get('accounts', []):
                        chic_fil_a = "parent:{}".format(account.get("name", "*"))
                        logger.debug("action=gw_accounts_v4_check filter={}".format(chic_fil_a))
                        props = self.service.properties().list(filter=chic_fil_a, pageSize=200).execute()
                        for prop in props.get("properties", []):
                            prop["custom_profile_version"] = "v4"
                            # Update the object with the GA3 properties, to help the front end
                            prop["id"] = prop["name"]
                            prop["accountId"] = prop["parent"].split("/")[1] or "unknown"
                            prop["websiteUrl"] = "GAv4 Property"
                            prop["webPropertyId"] = prop.get("displayName", "No Display Name Found")
                            logger.debug("action=gw_accounts_v4_check property={}".format(prop))
                            ret_object["data"].append(prop)
                except Exception as e:
                    error_msg, clean = self._catch_error(e)
                    logger.error("{}".format(error_msg))
                    ret_object["code"] = 500
                    ret_object["status"] = "error"
                    ret_object["error"] = f"{clean}"
                    logger.error("action=gw_accounts_v4_check {}".format(self._catch_error(e)))
                logger.debug("action=gw_accounts_check returning={}".format(ret_object))
                return ret_object
            elif metadata_type in ["compat"]:
                if "query_parameters" in kwargs.keys():
                    qp = kwargs.get("query_parameters", {})
                    metrics = [{"expression": x} for x in qp.get("metrics", "").split(",")]
                    dimensions = [{"name": x} for x in qp.get("dimensions", "").split(",")]
                    view = "{}".format(qp.get("view", 0))
                    prop_vers = "v4"
                    logger.debug(f"action=gw_check_compat view={view} version={prop_vers}")
                    logger.debug("action=gw_check_compat qp={}".format(qp))
                    today = datetime.today()
                    yesterdaydt = today - timedelta(days=1)
                    yesterday = yesterdaydt.strftime("%Y-%m-%d")
                    try:
                        def updateMetric(met):
                            met["name"] = f'metricname{met["expression"]}'
                            return met

                        v4_body = {
                            'dateRanges': [{"startDate": yesterday, "endDate": yesterday}],
                            "limit": 1,
                            "dimensions": dimensions,
                            "metrics": [updateMetric(x) for x in metrics]
                        }
                        logger.debug("action=check_compat_v4 body={}".format(v4_body))
                        results = self.service_v4_data.properties().runReport(property=view, body=v4_body).execute()
                        logger.debug("action=check_compat_v4 result={}".format(results))
                    except Exception as e:
                        logger.error(self._catch_error(e))
                        resp = {}
                        try:
                            resp = json.loads(e.content.decode("utf-8"))
                        except:
                            pass
                        logger.error("action=metrics_dimensions_compat_v4 error={}".format(e))
                        return {
                            "code": 500,
                            "status": "error",
                            "error": resp.get("error", {}).get("message", json.dumps(resp)),
                            "data": []
                        }
                    return {
                        "code": 200,
                        "status": "success",
                        "data": []
                    }
                else:
                    return {
                        "code": 404,
                        "status": "error",
                        "error": "Nothing to do",
                        "data": []
                    }
            else:
                logger.warn("metadata_type={} action=not_found".format(metadata_type))
                clean = f"Metadata type: {metadata_type} was not found."
                return {
                    "code": 404,
                    "status": "error",
                    "error": clean,
                    "data": []
                }

        except Exception as e:
            raise Exception("action=metrics_dimensions {}".format(self._catch_error(e)))

    handle_POST = handle_GET


class checkpoints(handle):
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def handle_GET(self, **kwargs):
        try:
            query = self.request["query"]
            input_type = query.get("input_type", "all").strip().lower()
            valid_checkpoints = ["ga", "ga_analytics", "ga_ss", "ga_forms",
                                 "ga_usage", "ga_classroom", "ga_pubsub",
                                 "ga_bigquery", "ga_alerts", "ga_user"]
            return_checkpoints = {}
            for chkpoint_name in valid_checkpoints:
                if input_type == "all" or input_type == chkpoint_name:
                    folder = make_splunkhome_path(["var", "lib", "splunk", "modinputs", chkpoint_name])
                    logger.debug("action=accessing_filesystem folder={}".format(folder))
                    if os.path.exists(folder):
                        dir_list = os.listdir(folder)
                        file_list = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
                        logger.debug(
                            f"action=listing_folder folder={folder} exists=true dir_list={dir_list} file_list={file_list}")
                        for checkpoint in file_list:
                            logger.debug(f"action=found_checkpoint checkpoint={checkpoint}")
                            file_ptr = os.path.join(folder, checkpoint)
                            stats = os.stat(file_ptr)
                            logger.debug(f"action=file_ptr={file_ptr} stats={stats}")
                            return_checkpoints[checkpoint] = {"input_type": chkpoint_name,
                                                              "filename": checkpoint,
                                                              "file_hash": get_file_hash(file_ptr),
                                                              "file_dir": folder,
                                                              "file_size": stats.st_size,
                                                              "file_mod_time": stats.st_mtime}
                            with open(file_ptr, "r") as file_hndl:
                                try:
                                    contents = json.loads(file_hndl.read())
                                    for k in contents.keys():
                                        return_checkpoints[checkpoint][k] = contents[k]
                                except:
                                    return_checkpoints[checkpoint]["contents"] = "{}".format(file_hndl.read())
                    else:
                        logger.debug("action=listing_folder folder={} exists=false".format(folder))
                else:
                    logger.debug(
                        "action=perform_file_access status=denied input_type={} chkpoint_name={}".format(input_type,
                                                                                                         chkpoint_name))
            logger.debug(f"action=found_checkpoints return_checkpoints={return_checkpoints}")
            return return_checkpoints
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET


class forms(handle):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def handle_GET(self, **kwargs):
        try:
            query = self.request["query"]
            scopes = ["https://www.googleapis.com/auth/forms.body.readonly",
                      "https://www.googleapis.com/auth/drive.readonly"]
            self.setup(query, "drive", "v3", scopes=scopes)
            status = self.service.files().list(q="mimeType='application/vnd.google-apps.form'").execute()
            return [{"status": "success", "data": status}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET


class pubsub(handle):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def _get_subs(self, project_id):
        logger.debug("action=get_subs project_id={}".format(project_id))
        from google.cloud import pubsub_v1
        pub_client = pubsub_v1.PublisherClient(credentials=self.non_delegated_credential)
        topics = pub_client.list_topics(project=f"projects/{project_id}")
        ta = []
        for topic in topics:
            t = topic.name.split("/")
            ta.append(t[len(t)-1])
        return ta

    def _get_projects(self):
        prjs = self.service.projects().list().execute()
        return  [p["projectId"] for p in prjs["projects"]]

    def handle_GET(self, **kwargs):
        try:

            query = self.request["query"]
            metadata_type = query.get("type", "project").strip().lower() #can be projects or subs
            objs = []
            scopes = global_scopes["gcp"]
            if metadata_type == "project":
                self.setup(query, "cloudresourcemanager", "v1", scopes=scopes)
                objs = self._get_projects()
            if metadata_type == "subscription":
                self.setup(query, "pubsub", "v1", scopes=scopes)
                objs = self._get_subs(query.get("projectId"))
            return [{"status": "success", "data": objs}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET


class bigquery(handle):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def _get_tables(self, project_id, dataset):
        logger.debug(f"action=get_tables project_id={project_id} dataset={dataset}")
        from google.cloud import bigquery
        bq_client = bigquery.Client(project=project_id,
                                    credentials=self.non_delegated_credential)
        tables = bq_client.list_tables(dataset)
        ta = []
        if tables:
            ta = [t.table_id for t in tables]
        logger.debug(f"action=get_tables project_id={project_id} dataset={dataset} tables={ta}")
        return ta

    def _get_datasets(self, project_id):
        logger.debug(f"action=get_datasets project_id={project_id}")
        from google.cloud import bigquery
        bq_client = bigquery.Client(credentials=self.non_delegated_credential)
        datasets = bq_client.list_datasets(project=f"{project_id}")
        ta = []
        if datasets:
            ta = [d.dataset_id for d in datasets]
        logger.debug(f"action=get_tables project_id={project_id} datasets={ta} ")
        return ta

    def _get_projects(self):
        prjs = self.service.projects().list().execute()
        return  [p["projectId"] for p in prjs["projects"]]

    def handle_GET(self, **kwargs):
        try:

            query = self.request["query"]
            metadata_type = query.get("type", "project").strip().lower() #can be projects or subs
            objs = []
            scopes = global_scopes["gcp"]
            if metadata_type == "project":
                self.setup(query, "cloudresourcemanager", "v1", scopes=scopes)
                objs = self._get_projects()
            if metadata_type == "dataset":
                self.setup(query, "cloudresourcemanager", "v1", scopes=scopes)
                objs = self._get_datasets(query.get("projectId"))
            if metadata_type == "table":
                self.setup(query, "cloudresourcemanager", "v1", scopes=scopes)
                objs = self._get_tables(query.get("projectId"), query.get("dataset"))
            return [{"status": "success", "data": objs}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET


class stub(handle):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        handle.__init__(self, method, requestInfo, responseInfo, sessionKey)

    def handle_GET(self, **kwargs):
        try:
            query = self.request["query"]
            scopes = []
            self.setup(query, "", "", scopes=scopes)
            status = {}
            return [{"status": "success", "data": status}]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": clean, "operation": "error"}]

    handle_POST = handle_GET

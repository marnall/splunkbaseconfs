# Alert action - BigQuery
#
import sys
import os
import logging
import csv
import gzip
import json
from datetime import datetime, timezone
from dateutil import tz

from Utilities import KennyLoggins
from google_constants import app_name as _package_id
from google_alert_action import GWAlertAction
from splunk.Intersplunk import decodeMV
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

_alert_name = "googleworkspace-write-big-query"
# This needs added to apl_logging.conf and README/apl_logging.conf.spec using splapp
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _package_id, "lib"]))

from google.api_core.exceptions import BadRequest as GoogleBadRequest

kl = KennyLoggins()
logger = kl.get_logger(app_name=_package_id, file_name=_alert_name, log_level=logging.DEBUG)
schemaTransfer = {
    str: "STRING",
    bytes: "BYTES",
    int: "INTEGER",
    float: "FLOAT",
    bool: "BOOLEAN",
    "%Y-%m-%d %H:%M:%S.{}Z": "TIMESTAMP",
    "%Y-%m-%d": "DATE",
    "%H:%M:%S.%3": "TIME",
    "%Y-%m-%d %H:%M:%S.%3": "DATETIME",
    None: "NULLABLE"
}
schemaTransferRev = {schemaTransfer[k]: k for k in schemaTransfer}
no_cast = ["TIMESTAMP", "DATE", "TIME", "DATETIME"]

def _check_field_name(f):
    if f.startswith("__"):
        return False
    return True


class GWAlert(GWAlertAction):
    def __init__(self, settings, action_name):
        try:
            GWAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                   filename=_alert_name,
                                   stanza="global_{}_configuration".format(_alert_name))
            self.client = None
            self.path = None
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.fatal(error_msg)

    def _get_file_handler(self, form='rb'):
        return gzip.open(self.payload.get("results_file"), form)

    def _parse_types_for_bq(self, f, v, ls, is_mv):
        self._log.debug(f'action=parse field="{f}" v="{v}" schema={ls} is_mv={is_mv}')
        if f not in ls:
            ls[f] = {"mode": "NULLABLE", "type": "STRING"}
            try:
                v = int(v)
                ls[f]["type"] = "INTEGER"
            except: pass
            try:
                v = float(v)
                ls[f]["type"] = "FLOAT"
            except: pass
        if is_mv:
            ls[f]["mode"] = "REPEATED"
        if f in ["_time"]:
            l_tz = tz.gettz(self.localized_time_zone)
            l_time = int(float(v) * 1000)
            self._log.debug(f'action=parse field="{f}" parsed={l_time} splunk_tz={self.localized_time_zone} python_tz={l_tz}')
            ts = datetime.fromtimestamp(float(v), tz=l_tz)
            v = ts.astimezone(timezone.utc).strftime(schemaTransferRev["TIMESTAMP"].format(l_time%1000))
            self._log.debug(f'action=parse field="{f}" '
                            f'tz={self.localized_time_zone} '
                            f'ts="{v}"')
            ls[f]["type"] = "TIMESTAMP"
            return v
        if f in ls and ls[f]["type"] in schemaTransferRev and ls[f]["type"] not in no_cast:
            self._log.debug(f'action=parse field="{f}" type="{ls[f]["type"]}"')
            if len(v) < 1:
                ls[f]["mode"] = "NULLABLE"
                return None
            return schemaTransferRev[ls[f]["type"]](v)
        return v

    def _make_mv(self, f, d, mv, ls):
        mv_f = f"__mv_{f}"
        mvk = mv.keys()
        self._log.debug(f"action=check_mv mv_field={mv_f} mv_keys={mvk}")
        if mv_f in mvk:
            t = []
            decodeMV(d[mv_f], t)
            self._log.debug(f"action=decodeMV t={t}")
            return [self._parse_types_for_bq(f, x, ls, True) for x in t]
        return self._parse_types_for_bq(f, d[f], ls, False)

    def _process_dict(self, d, ls):
        dn = dict(d)
        mv = {x: dn[x] for x in dn.keys() if x.startswith("__mv") and len(dn[x]) > 0}
        self._log.debug(f"action=multivalue_fields mv={mv}")
        dd = {x: self._make_mv(x, dn, mv, ls) for x in dn.keys() if _check_field_name(x)}
        self._log.debug(f"action=generate_record dd={dd}")
        return dd

    def _convert_schema_to_json(self, schema):
        ret_schema = {}
        for x in schema:
            y = dict(x.__dict__)
            z = y["_properties"]
            self._log.debug(f"field=_time z {z}")
            if z.get("name") not in ret_schema:
                ret_schema[z.get("name", "")] = {
                    "type": z.get("type", "STRING"),
                    "mode": z.get("mode", "REPEATED")
                }
        return ret_schema

    def _convert_json_to_schema(self, schema):
        ret_schema = []
        for k in schema:
            self._log.debug(f'action=convert field="{k}" schema={schema[k]}')
            ret_schema.append(self.SchemaField.from_api_repr({
                "name": k,
                "type": schema[k]["type"].upper(),
                "mode": schema[k]["mode"].upper()
            }))
        return ret_schema

    def _schema_check(self, x, json_schema):
        self._log.debug(f"action=checking_final_schema_conformity x={x} schema={json_schema}")
        for f in x:
            if f in json_schema:
                self._log.debug(f'action=evaluate_type field={f} type={type(x[f])} schema={json_schema[f]}')
                if type(x[f]) == str and json_schema[f]["mode"] in ["REPEATED"]:
                    x[f] = [x[f]]
        self._log.debug(f'action=final_row {" ".join(["{}={}".format(y, type(x[y])) for y in x])}')
        return x

    def main(self):
        try:
            self._log.debug("action=start")
            self.setup_gw("bigquery")
            project = self.get_config("project_id")
            dataset = self.get_config("dataset_id")
            table = self.get_config("table_id")
            # Dark Feature for Timeout.
            timeout = self.get_config("timeout", 1800)
            table_id = f"{project}.{dataset}.{table}"
            write_preference = self.get_config("write_preference", "WRITE_EMPTY")
            wp = {"WRITE_TRUNCATE": self.bigquery.WriteDisposition.WRITE_TRUNCATE,
                  "WRITE_EMPTY": self.bigquery.WriteDisposition.WRITE_EMPTY,
                  "WRITE_APPEND": self.bigquery.WriteDisposition.WRITE_APPEND}
            results_file = self.payload.get("results_file")
            self._log.debug(
                f"action=configurations project_id={project} table_id={table_id} write_preference={write_preference} results_file={results_file}")
            # If a Proxy is needed, use the OS level Proxy "HTTPS_PROXY" environment variable.
            self.service = self.bigquery.Client(project=project,
                                                credentials=self.non_delegated_credential)
            table = self.service.get_table(table_id)
            original_schema = table.schema
            self._log.debug(f"action=loaded_table_schema schema={original_schema}")
            json_schema = self._convert_schema_to_json(original_schema[:])
            with gzip.open(self.payload.get("results_file"), "rt") as gf:
                matrix = [self._process_dict(n, json_schema) for r, n in enumerate(csv.DictReader(gf))]
            self._log.debug(f"action=loaded_results len_results={matrix}")
            new_schema = self._convert_json_to_schema(json_schema)
            self._log.debug(f"original_schema={original_schema} updated_schema={new_schema}")
            # https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.job.LoadJobConfig#google_cloud_bigquery_job_LoadJobConfig_source_format
            job_config_settings = {
                "write_disposition": wp[write_preference],
                "source_format": self.bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
            }
            if write_preference in ["WRITE_EMPTY"]:
                job_config_settings["autodetect"] = True
            if write_preference == "AWRITE_APPEND":
                job_config_settings["schema_update_options"] = ["ALLOW_FIELD_ADDITION", "ALLOW_FIELD_RELAXATION"]
            if write_preference in ["WRITE_APPEND", "WRITE_TRUNCATE"]:
                table.scheme = new_schema
                self._log.debug(f'action=update_table_schema new_schema={new_schema}')
                table = self.service.update_table(table, ["schema"])
                job_config_settings["schema"] = new_schema
            self._log.debug(f"action=setup_job_config job_config={job_config_settings} timeout={timeout}")
            job_config = self.bigquery.LoadJobConfig(**job_config_settings)
            job = self.service.load_table_from_json([self._schema_check(x, json_schema) for x in matrix], table_id,
                                                    job_config=job_config)
            try:
                job.result(timeout=timeout)
            except GoogleBadRequest as ge:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                st = f"googleworkspace:alert_action:{_alert_name}:error"
                error_msg2 = f'action=load_data_to_bq_table write_preference="{write_preference}" ' \
                             f'status=failure error_message="{ge}" error_line_number={exc_tb.tb_lineno}'
                self.addevent(error_msg2, st)
                if len(job.errors) > 0:
                    [self.addevent('reason="{}" error_message="{}"'.format(x["reason"], x["message"]), st) for x in job.errors]
                    self._log.error("{}".format(json.dumps(job.errors)))
                self._log.error(error_msg2)

        except Exception as me:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(me), type(me), "{}".format(me), fname, exc_tb.tb_lineno, self._action_name)
            self._log.error(error_msg)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = GWAlert(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evt_idx("google_workspace")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='googleworkspace_alert_action_st',
                              sourcetype="google:workspace:alert_action:{}".format(_alert_name),
                              source="google:workspace:alert_action:{}:{}".format(_alert_name,
                                                                                 modaction.payload[
                                                                                     "search_name"].replace(" ",
                                                                                                            "_")))
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)

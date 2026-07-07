from json import dumps
import datetime
import sys
import os
import csv
import gzip
import splunk.clilib.cli_common as scc
import splunk.entity as entity
from dateutil.parser import parse
import requests
from cim_actions import ModularAction
import splunk.auth as auth
import splunk_common.log as log
from itertools import chain
from collections import defaultdict
from irflow_common.irflow_client import IRFlowClient

logger = log.Logs('irflow-splunk-app').get_logger("CreateIRFlowAlert")
SPLUNK_URL = auth.splunk.getLocalServerInfo()


class CreateAlertModularAction(ModularAction):
    def __init__(self, settings, logge, action_name='unknown'):
        ModularAction.__init__(self, settings, logge, action_name=action_name)
        try:
            self.irflow_configuration = scc.getConfStanza("irflow", "config")

            for k, v in self.irflow_configuration.iteritems():
                setattr(self, k, v)
            self.log = logger
            if self.debug:
                from logging import DEBUG
                self.log.setLevel(DEBUG)
            self.log.debug("action=get_settings settings={}".format(self.irflow_configuration))
            try:
                self.payload = self.settings
            except ValueError:
                self.log.info('No alerts to process!')
                sys.exit(2)

            self.log.debug("action=get_payload payload={}".format(dumps(self.payload)))
            self.sessionKey = self.payload.get('session_key', None)
            configuration = self.payload.get("configuration")
            self.realm = configuration.get("realm", "irflow-prod")
            configs = []
            if self.realm == "irflow-prod" or self.realm == "both":
                username, password = self.get_creds(self.realm, self.api_user)
                configs.append({"api_user": username,
                               "api_key": password,
                               "address": self.address,
                               "debug": self.debug,
                               "protocol": "https",
                               "verbose": 1})
            if self.realm == "irflow-stage" or self.realm == "both":
                username, password = self.get_creds(self.realm, self.stage_api_user)
                configs.append({"api_user": username,
                               "api_key": password,
                                "address": self.stage_address,
                                "debug": self.debug,
                                "protocol": "https",
                                "verbose": 1})
                self.verify_ssl = self.stage_verify_ssl,
                self.suppress = self.stage_suppress
            self.log.debug(
                "action=get_cred realm={} user={} address={}".format(self.realm, self.api_user, self.address))
            self.irfc = [IRFlowClient(x) for x in configs]
            self.key_map = self._load_lookups("irflow_")
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self.log.error("action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))

    def _build_url(self, endpoint, search=None):
        url = "{}/servicesNS/nobody/irflow-splunk-app/{}?output_mode=json".format(
            SPLUNK_URL, "/".join(endpoint)
        )
        if search is not None:
            url = "{}&search={}".format(url, search)
        return url

    def _load_lookups(self, fltr):
        all_fields = {}
        all_fields_list = defaultdict(list)
        url = self._build_url(["data", "lookup-table-files"], search=fltr)
        self.log.debug("action=load_all_irflow_lookups url={}".format(url))
        r = self._get(url)

        sc = r.status_code
        if sc != 200:
            raise Exception("Unable to query rest url {}".format(url))
        self.log.debug("action=load_lookup_rest r={}".format(dumps(r.json()["entry"])))
        seen_ids = set()
        for lup in r.json()["entry"]:
            lookup = self._load_lookup(lup["name"])
            for k, v in chain(all_fields.items(), lookup.items()):
                if v["id"] not in seen_ids:
                    all_fields_list[k].append(v)
                    seen_ids.add(v["id"])
            all_fields.update(lookup)
        self.log.debug("action=build_collection all_fields_list={}".format(dumps(all_fields_list["src_user"])))
        return all_fields_list

    def _load_lookup(self, lookup_name):
        try:
            url = self._build_url(["data", "lookup-table-files", lookup_name])
            r = self._get(url)
            sc = r.status_code
            if sc != 200:
                raise Exception("{} Lookup not found. ".format(lookup_name))
            rj = r.json()["entry"][0]
            path = rj["content"]["eai:data"]
            self.log.debug("reading lookup path from {}".format(path))
            keys = []
            with open(path) as fh:
                lookup = csv.DictReader(fh)
                for line in lookup:
                    keys.append(line)
            self.log.debug("action=load_csv sc={} url={} path={}".format(sc, url, path))
            return {self.__f(x): {"type": x["field_type"],  # required
                                  "irflow": x["field_name"],  # required
                                  "source": rj["name"],  # required
                                  "id": x["id"],  # required
                                  "list_field": x.get("list_field", "FALSE"),  # optional
                                  "object_field": x.get("object_field", "FALSE")  # optional
                                  } for x in keys}
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("function=_load_lookup line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                                    fname, e))

    def __f(self, x):
        fi = x.get("field_splunk", None)
        unk = "unknown_{}".format(x["field_name"])
        if fi is None:
            return unk
        elif len(fi) < 1:
            return unk
        elif fi == "unk" or fi == "unknown":
            return unk
        else:
            return fi

    def _post(self, url, data):
        try:
            return requests.post(url=url, data=data, headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                                 verify=False)
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("function=_post line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                             fname, e))

    def _delete(self, url):
        try:
            return requests.delete(url=url, headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                                   verify=False)
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("function=_delete line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                               fname, e))

    def _get(self, url):
        try:
            return requests.get(url=url,
                                headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                                verify=False)

        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("function=_get line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                            fname, e))

    def getSessionKey(self):
        return self.sessionKey

    def get_evtidx(self):
        logger.info("function=_get_evtidx")
        r = self._get(
            "{}/servicesNS/nobody/irflow-splunk-app/saved/eventtypes/irflow_action_index?output_mode=json".format(
                SPLUNK_URL
            ))
        return r.status_code, r.json()["entry"][0]["content"]["search"].split("=")[1]

    def get_creds(self, realm, api_user):
        try:
            # list all credentials
            # Added search parameter to only return the realm and user we are interested in.
            # Thus the first found will be the only one found that matches.
            entities = entity.getEntities(['storage', 'passwords'], namespace='irflow-splunk-app',
                                          owner='nobody', sessionKey=self.getSessionKey(),
                                          search="{0}:{1}".format(realm, api_user))
            for i, c in entities.items():
                if c['username'] == api_user:
                    return c['username'], c['clear_password']

            raise Exception("No credentials have been found realm={}".format(realm))
        except Exception as e:
            raise Exception("Could not get %s credentials from splunk. Error: %s"
                            % ('irflow-splunk-app', str(e)))

            # return first set of credentials

    def _get_spl(self, sid):
        self.log.debug("function=_get_spl sid={}".format(sid))
        url = self._build_url(["search", "jobs", sid], search=None)
        self.log.debug("pulling sid from url {}".format(url))
        r = self._get(url)
        sc = r.status_code
        if sc == 200:
            self.log.debug("response {}".format(dumps(r.json()["entry"][0]["content"]["request"])))
            cont = r.json()["entry"][0]["content"]
            if "search" in cont["request"]:
                return cont["request"]["search"]
            else:
                return "{} | {}".format(cont["eventSearch"], cont["reportSearch"])
        return ""

    def _check_true(self, v):

        if v == "TRUE" or v == 1 or v == "True" or v is True or v == "1":
            self.log.debug("action=_check_true v={} result=True".format(v))
            return True
        else:
            self.log.debug("action=_check_true v={} result=False".format(v))
            return False

    def _map_keys(self, k, v):
        try:
            nk = self.key_map.get(k, None)
            self.log.info("action=_map_keys_k_v k={} v={} nk={}".format(k, v, nk))
            if nk is None:
                self.log.warn("function=_map_keys action=key_not_found k={} nk={}".format(k, k))
                return {k: v}
            elif len(nk) > 0:
                self.log.info("function=_map_keys action=found_irflow k={} nk={}".format(k, nk))
                return {x["irflow"]: self._check_irflow_values(x, v) for x in nk}
            else:
                self.log.warn("function=_map_keys action=mapping_unknown staus=failed k={} nk={}".format(k, nk))
                return {k: v}
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=_map_keys action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))

    def _check_irflow_values(self, nk, v):
        try:
            list_field = False
            object_field = False
            if nk is None:
                return "{}".format(v)
            if "list_field" in nk:
                self.log.debug("function=_check_irflow_values message=checking_list_field nk={}".format(nk))
                list_field = self._check_true(nk["list_field"])
            if "object_field" in nk:
                self.log.debug("function=_check_irflow_values message=checking_object_field")
                object_field = self._check_true(nk["object_field"])
            self.log.debug("function=_check_irflow_values f={} v={} list_field={} object_field={}".format(nk, v, list_field, object_field))
            return_value = None
            is_time = False
            if "type" in nk:
                self.log.debug("function=_check_irflow_values action=time_action found field_type={}".format(nk["type"]))
                if nk["type"] == "datetime":
                    is_time = True
            if list_field and object_field:
                self.log.warn("function=_check_irflow_values f={} v={} list_field={} object_field={} message='BOTH ARE TRUE'".format(nk, v, list_field, object_field))
                return_value = "{}".format(v)
            elif list_field:
                value = [s.strip() for s in v.splitlines()]
                self.log.debug("function=_check_irflow_values list_field={} v={}".format(list_field, value))
                return_value = value
            elif object_field:
                # Currently not used. Logic can be implemented at later date.
                self.log.debug("function=_check_irflow_values object_field={} v={}".format(object_field, v))
                return_value = "{}".format(v)
            else:
                self.log.debug("function=_check_irflow_values list_field={} object_field={} nk={} v={}".format(list_field, object_field, nk, v))
                return_value = "{}".format(v)
            self.log.debug("function=_check_irflow_values action=time_action field={} is_time={}".format(nk, is_time))
            if is_time:
                # Format is YYYY-MM-DD HH:MM:SS TZ
                self.log.debug("function=_check_irflow_values is_time=true action=time_action original_value=\"{}\"".format(return_value))
                try:
                    dt = int(return_value)
                    self.log.debug("function=_check_irflow_values is_time=true action=time_action found_int={} returning=value".format(dt))
                    return dt
                except Exception, e:
                    self.log.debug("function=_check_irflow_values is_time=true action=time_action {} {}".format(e, type(e)))
                try:
                    dt = (parse(return_value).replace(tzinfo=None) - datetime.datetime(1970,1,1,0,0,0,0,None)).total_seconds()
                    self.log.debug("function=_check_irflow_values is_time=true action=time_action parsed=\"{}\" returning=value".format(dt))
                    return dt
                except Exception, e:
                    self.log.error("function=_check_irflow_values is_time=true action=time_action error_on_parse=\"{}\"".format(e))
                    raise Exception("Failed to Parse Timestamp: {}".format(return_value))
                return_value = "{}".format(return_value)
            return return_value
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=_map_keys action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))

    def main(self):
        try:
            self.log.debug("function=main action=start")
            parser = self.payload['search_name']
            self.log.debug('Using IR-Flow parser: {}'.format(parser))
            results_file = self.payload.get("results_file")
            # modaction = CreateAlertModularAction(json.dumps(self.payload), logger, 'irflow_create_alert')
            self.log.debug("action=reading_results_file file={}".format(results_file))
            # Load all lookups that start with irflow_ . This are "smashed" fields, so it is possible to override from different files.

            self.log.debug("action=results_file_processing results_file={}".format(results_file))
            with gzip.open(results_file, 'rb') as fh:
                for num, result in enumerate(csv.DictReader(fh)):
                    try:
                        self.log.debug("processing result number {}".format(num))
                        result.setdefault('rid', str(num))
                        try:
                            desc = result.pop('irflow_description')
                            self.log.debug('Setting IR-Flow Alert description to: {}'.format(desc))
                        except KeyError:
                            desc = None
                            self.log.debug('No description set for this alert')
                        self.log.debug("function=main marker=result result={}".format(dumps(result)))
                        culled_json = {}
                        single_result = [self._map_keys(k, v) for k, v in result.iteritems()
                                         if not k.startswith('__') and k != "rid"]
                        self.log.debug("single_result={}".format(single_result))
                        [culled_json.update(x) for x in single_result]
                        # culled_json = {self._map_keys(k): self._check_irflow_values(k, v) for k, v in result.iteritems()
                        #                if not k.startswith('__') and k != "rid"}
                        culled_json["splQueryId"] = self.payload.get("sid", "")
                        culled_json["splSavedsearchName"] = self.payload.get("search_name", "")
                        culled_json["splQuery"] = self._get_spl(self.payload.get("sid", ""))
                        logger.info("action=before_create_event suppress={}".format(self.suppress))
                        did_complete, content = self.create_event(
                            event_fields=culled_json,
                            parser=parser,
                            event_desc=desc,
                            suppress=self._check_true(self.suppress))
                        send_arf = self.irflow_configuration.get("arf")
                        if self.payload['configuration'].get("realm") == "irflow-stage":
                            send_arf = self.irflow_configuration.get("stage_arf")
                        self.log.debug("checking_for_arf did_complete={} send_arf={}".format(did_complete, send_arf))
                        if did_complete and send_arf:
                            self.log.debug("action=sending_arf")
                            self.update(result)
                            self.invoke()
                            result["irflow_response"] = content
                            self.addevent(dumps(dict(result)),
                                          sourcetype="irflow_action:{}".format(self.payload['search_name']))
                    except Exception, e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self.log.error(
                            "function=main action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                                                  fname, e))
            self.log.info('function=main action=sending destination=ir_flow')
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=main action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))

    def create_event(self, event_fields, parser, event_desc=None, suppress=False):
        """Method to fire off IR-Flow Client to create alert in irflow

        :param event_fields:    dict of alert object fields to send
        :param parser:          Incoming Field Group Name in IR-Flow
        :param event_desc:      Alert Description
        :param suppress:        Suppress Field Warnings
        :return:
        """

        self.log.info('Send data to IR-Flow')
        self.log.info("action=send_data suppress_missing_fields={} event_fields={}".format(suppress, event_fields))
        res = [x.create_alert(alert_fields=event_fields,
                                     description=event_desc,
                                     incoming_field_group_name=parser,
                                     suppress_missing_field_warning=suppress
                                     ) for x in self.irfc]
        self.log.info('Sent alert request...')

        if res['success']:
            # Log success
            self.log.info('Alert created successfully.')
            return True, res
        else:
            # Log Failure
            self.log.info('Alert failed to send')
            self.log.info(dumps(str(res)))
            return False, res


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    modaction = None
    try:
        modaction = CreateAlertModularAction(sys.stdin.read(), logger, 'irflow_create_alert')
        modaction.main()
        sc, evttype= modaction.get_evtidx()
        logger.debug("found evt index={}".format(evttype))
        modaction.writeevents(index=evttype, source='irflow_action')
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "function=__main__ action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
        except Exception, e:
            logger.critical(e)
        print >> sys.stderr, "ERROR Unexpected err: %s" % e
        sys.exit(3)

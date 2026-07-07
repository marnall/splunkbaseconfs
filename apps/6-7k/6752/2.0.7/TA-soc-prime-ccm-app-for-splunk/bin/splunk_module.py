import ta_soc_prime_ccm_app_for_splunk_declare
import splunklib.client as client
import re
import json
import logging
from compare_params_list import *
import configparser
import requests

class OutputSplunk():
    def __init__(self, conf, force_updating_rules, rules_owner):
        try:
            self.service = client.connect(**conf)
        except Exception as err:
            message = f'Connection to Splunk is not established. Error message: {err}'
            logging.error(message)
            raise ValueError(message)
        self.conf = conf
        self.rules_owner = rules_owner
        self.successfully_installed_rules = []
        self.force_updating_rules = force_updating_rules

    def bulk_create_saved_search(self, messages) -> None:
        for message in messages:
            if message['siem_type'] == 'splunk_alert':
                self.create_saved_search(message)

    def _get_alert_params(self, rule_text: str) -> dict:
        config = configparser.ConfigParser(strict=False, interpolation=None)
        config.read_string(rule_text)
        params = [section_dict for section_name, section_dict in list(config.items()) if section_name != 'DEFAULT'][0]
        rule_name_section = config.sections()[0]
        return dict(params), rule_name_section

    def create_saved_search(self, sigma) -> None:
        # List of Saved searches from Splunk:
        savedsearches = self.service.saved_searches
        saved_search_name = (sigma["case"]["name"][:96] + '..') if len(sigma["case"]["name"]) > 99 else sigma["case"]["name"]
        try:
            alert_config, saved_search_name = self._get_alert_params(sigma["sigma"]["text"])
            actor_field = (sigma.get('tags', '-')).get('actor', '-')
            actor_field = '-' if actor_field == [] or actor_field == 'null' or actor_field is None else str(actor_field)
            alert_config['description'] = f'SP Actor:{actor_field}\nSP Rule ID:{sigma["case"]["id"]}' if alert_config['description'] is None else alert_config['description'] + f'\nSP Actor:{actor_field}\nSP Rule ID:{sigma["case"]["id"]}'
            saved_search_name = (saved_search_name[:96] + '..') if len(saved_search_name) > 99 else saved_search_name
        except Exception as err:
            sigma_text = sigma["sigma"]["text"]
            logging.info(sigma_text)
            sigma_text = sigma_text.replace('\n', ', ')
            message = f'Sigma text not recognized and dict was not created. Check sigma parameters and search request.. Error message: {err}. Alert name: {saved_search_name}. Sigma text: {sigma_text}'
            logging.warning('info_for_stats_msg = {}'.format(json.dumps(
                {"saved_search_name": sigma["case"]["name"], "type": "upload_fail",
                 "reason": "Sigma text not recognized and dict was not created. Check sigma parameters and search request.",
                 "updated_parameters": sigma_text})))
            logging.error(message)
            alert_config = None
        if alert_config and alert_config is not None:
            saved_search_query = alert_config.get("search")
            if saved_search_name in savedsearches:
                logging.debug(f'{saved_search_name} --- {alert_config}.')
                if self.force_updating_rules == True:
                    for savedsearch in savedsearches:
                        # updating procedure
                        if sigma["case"]["id"] in savedsearch.name or ( savedsearch["description"] is not None and sigma["case"]["id"] in savedsearch["description"] ):
                            logging.info(
                                f'The saved search "{saved_search_name}" is already exists in the Splunk. Check query for identical.')
                            updated_parameters = self.get_updated_parameters(savedsearch, alert_config)
                            if len(updated_parameters) > 0:
                                logging.info(
                                    f'Updating parameters for the saved search "{saved_search_name}". New parameters: "{str(updated_parameters)}".')
                                try:
                                    saved_search = savedsearch.update(**updated_parameters).refresh()
                                    if saved_search is None:
                                        logging.warning(
                                            f'Saved search "{saved_search_name}" was not updated. Something went wrong. Parameters: "{str(updated_parameters)}"')
                                        logging.warning('info_for_stats_msg = {}'.format(json.dumps(
                                            {"saved_search_name": saved_search_name, "type": "update_fail",
                                            "reason": "Something went wrong.",
                                            "updated_parameters": str(updated_parameters)})))
                                    else:
                                        logging.info(
                                            f'Parameters for the saved search "{saved_search_name}" has been updated. New parameters: "{str(updated_parameters)}"')
                                        logging.info('info_for_stats_msg = {}'.format(json.dumps(
                                            {"saved_search_name": saved_search_name, "type": "update_success",
                                            "updated_parameters": str(updated_parameters)})))
                                        self.successfully_installed_rules.append(
                                            {"case_id": sigma["case"]["id"], "siem_type": "splunk_alert"})
                                except Exception as e:
                                    logging.warning(
                                        f'Saved search "{saved_search_name}" was not updated. Reason: {str(e)}. Parameters: "{str(updated_parameters)}"')
                                    logging.warning('info_for_stats_msg = {}'.format(json.dumps(
                                        {"saved_search_name": saved_search_name, "type": "update_fail", "reason": str(e),
                                        "updated_parameters": str(updated_parameters)})))
                            else:
                                logging.info(
                                    f'Parameters and search query for "{saved_search_name}" the same that from CCM. No need to update.')
                else:
                     logging.info(f'The saved search "{saved_search_name}" is already exists in the Splunk. Updating is not needed - option "force_updating_rules" is false.')
            else:
                # upload new
                logging.info(f'{saved_search_name} --- {alert_config}.')
                try:
                    saved_search = self.service.saved_searches.create(name=saved_search_name, **alert_config)
                    logging.info(
                        f'Successfully uploaded new saved search "{saved_search_name}" to the Splunk instance.')
                    self.update_search_owner_permissions(saved_search_name)
                    logging.info('info_for_stats_msg = {}'.format(json.dumps(
                        {"saved_search_name": saved_search_name, "type": "upload_success",
                         "updated_parameters": str(alert_config)})))
                    self.successfully_installed_rules.append({"case_id": sigma["case"]["id"], "siem_type": "splunk_alert"})
                    if saved_search is None:
                        logging.warning(
                            f'Saved search "{saved_search_name}" was not uploaded. Something went wrong. Parameters: "{str(alert_config)}".')
                        logging.warning('info_for_stats_msg = {}'.format(json.dumps(
                            {"saved_search_name": saved_search_name, "type": "upload_fail",
                             "reason": "Something went wrong.", "updated_parameters": str(alert_config)})))
                except Exception as e:
                    logging.warning(
                        f'Saved search "{saved_search_name}" was not uploaded. Reason: {str(e)}. Parameters: "{str(alert_config)}"')
                    logging.warning('info_for_stats_msg = {}'.format(json.dumps(
                        {"saved_search_name": saved_search_name, "type": "upload_fail", "reason": str(e),
                         "updated_parameters": str(alert_config)})))

    def update_search_owner_permissions(self, saved_search_name):
        cert_path = False
        splunk_default_hostname = self.conf.get('host','-')
        splunk_default_port = self.conf.get('port','-')
        splunk_rule_owner = self.conf.get('owner','-')
        splunk_app = self.conf.get('app','-')
        splunk_session_key = self.conf.get('token','-')
        if splunk_session_key != '-':
            uri = 'https://'+ str(splunk_default_hostname) +':'+ str(splunk_default_port) +'/servicesNS/nobody/'+ str(splunk_app) +'/saved/searches/'+ str(requests.utils.quote(saved_search_name).replace('/', '%2F')) +'/acl'
            headers = {
                "Authorization": "Splunk " + splunk_session_key
            }
            params = {
                'owner': self.rules_owner,
                'sharing': 'global'
            }
            try:
                r = requests.post(uri, headers=headers, params=params, verify=cert_path)
                if 299 >= r.status_code >= 200:
                    logging.info("Permissions successfully updated for savedsearch: {}.".format(saved_search_name))
                else:
                    logging.error("Permissions not updated for savedsearch: {} Something wrong. Error code: {}".format(saved_search_name, r.status_code))
            except Exception as err:
                logging.error("Permissions not updated for savedsearch: {} Something wrong. Error code: {}".format(saved_search_name, err))
    def get_updated_parameters(self, savedsearch, alert_config):
        d = {}
        for param in compare_params_list:
            if alert_config.get(param) is not None:
                if param == 'actions':
                    text1 = savedsearch[param]
                    text2 = alert_config.get(param)
                    new_tuple1 = tuple((text1.replace(" ", "")).split(','))
                    new_tuple2 = tuple((text2.replace(" ", "")).split(','))
                    if sorted(new_tuple2) != sorted(new_tuple1):
                        logging.info(
                            f'Parameter "{param}" for "{savedsearch.name}" will be updated from "{savedsearch[param]}" to "{alert_config.get(param)}".')
                        d[param] = alert_config.get(param)
                else:
                    if savedsearch[param] != alert_config.get(param):
                        logging.info(
                            f'Parameter "{param}" for "{savedsearch.name}" will be updated from "{savedsearch[param]}" to "{alert_config.get(param)}".')
                        d[param] = alert_config.get(param)
        return d
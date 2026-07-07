import splunklib.client as client
import re
import json
import logging
from compare_params_list import *

class OutputSplunk():
    def __init__(self, conf):
        try:
            self.service = client.connect(**conf)
        except Exception as err:
            message = f'Connection to Splunk is not established. Error message: {err}'
            logging.error(message)
            raise ValueError(message)
        self.successfully_installed_rules = []

    def bulk_create_saved_search(self, messages) -> None:
        for message in messages:
            if message['siem_type'] == 'splunk_alert':
                self.create_saved_search(message)

    def create_saved_search(self, sigma) -> None:
        # List of Saved searches from Splunk:
        savedsearches = self.service.saved_searches
        saved_search_name = f'SP | {sigma["case"]["id"]} | {sigma["case"]["name"]}'
        saved_search_name = (saved_search_name[:96] + '..') if len(saved_search_name) > 99 else saved_search_name
        try:
            alert_config = dict(item.split(" = ") for item in
                                re.split(r'\n|\r\n', re.sub(r'\s+$', '', sigma["sigma"]["text"], flags=re.M)) if
                                " = " in item)
        except Exception as err:
            sigma_text = sigma["sigma"]["text"]
            sigma_text = sigma_text.replace('\n', ', ')
            message = f'Sigma text not recognized and dict was not created. Check sigma parameters and search request.. Error message: {err}. Alert name: {saved_search_name}. Sigma text: {sigma_text}'
            logging.warning('info_for_stats_msg = {}'.format(json.dumps(
                {"saved_search_name": saved_search_name, "type": "upload_fail",
                 "reason": "Sigma text not recognized and dict was not created. Check sigma parameters and search request.",
                 "updated_parameters": sigma_text})))
            logging.error(message)
            alert_config = None
        if alert_config and alert_config is not None:
            logging.info(f'{saved_search_name} --- {alert_config}.')
            saved_search_query = alert_config.get("search")
            if saved_search_name in savedsearches:
                for savedsearch in savedsearches:
                    # updating procedure
                    if savedsearch.name == saved_search_name:
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
                # upload new
                try:
                    saved_search = self.service.saved_searches.create(name=saved_search_name, **alert_config)
                    logging.info(
                        f'Successfully uploaded new saved search "{saved_search_name}" to the Splunk instance.')
                    logging.info('info_for_stats_msg = {}'.format(json.dumps(
                        {"saved_search_name": saved_search_name, "type": "upload_success",
                         "updated_parameters": str(alert_config)})))
                    self.successfully_installed_rules.append(
                        {"case_id": sigma["case"]["id"], "siem_type": "splunk_alert"})
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

    def get_updated_parameters(self, savedsearch, alert_config):
        d = {}
        for param in compare_params_list:
            if alert_config.get(param) is not None:
                if savedsearch[param] != alert_config.get(param):
                    logging.info(
                        f'Parameter "{param}" for "{savedsearch.name}" will be updated from "{savedsearch[param]}" to "{alert_config.get(param)}".')
                    d[param] = alert_config.get(param)
        return d
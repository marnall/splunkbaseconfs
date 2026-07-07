from thousandeyes_client import ThousandEyesClient
from exceptions import InsufficientPermissionsError
import splunk.rest as rest
import json, re

from thousandeyes_constant import THOUSANDEYES_TA_NAME

class ITSIEventSender:
    def __init__(self, session_key, logger):
        self.session_key = session_key
        self.logger = logger
        self.test_to_te_account = self._get_test_to_te_account()
        self.logger.debug(f'ITSIEventSender initialized with test mapping: {self.test_to_te_account}')

    def send_event_for_tests(self, event: dict, first_ts: str, test_ids: list):
        self._log('info', f'Sending event {event.get("event_id")} from episode {event.get("itsi_group_id")} for tests {test_ids}')
        event['te_first_time'] = first_ts
        results = []
        for test_id in test_ids:
            if not test_id or test_id not in self.test_to_te_account:
                self._log('warning', f'Test ID {test_id} is not valid or not found in mapping. Skipping.')
                continue
            account_info = self.test_to_te_account[test_id]
            for (user, account_group) in account_info:
                if self._forward_event(event, user, account_group, test_id):
                    results.append(test_id)
        self._log('info', f'Sent event {event.get("event_id")} from episode {event.get("itsi_group_id")} for tests {results}')
        return results
    
    def _forward_event(self, event, user, account_group, test_id):
        self._log('debug', f'Forwarding event {event.get("event_id")} for test_id {test_id} to account {user}/{account_group}')
        event_with_test_id = event.copy()
        event_with_test_id['thousandeyes_test_id'] = test_id
        client = ThousandEyesClient(self.session_key, user, self.logger)
        try:
            client.forward_splunk_event(event_with_test_id, account_group)
            self._log('debug', f'Successfully sent event for test_id {test_id} to account {user}/{account_group}')
            return True
        except InsufficientPermissionsError:
            self._log('error', f'Insufficient permissions for account {user}/{account_group} to send event with {test_id}.')
        except Exception as e:
            self._log('error', f'Failed to send event for test_id {test_id}: {e}')
        return False

        
    def _get_test_to_te_account(self):
        self._log('debug', 'Fetching test metrics stream configuration')
        try:
           _, response_content = rest.simpleRequest(
                    f"/servicesNS/nobody/{THOUSANDEYES_TA_NAME}/data/inputs/test_metrics_stream",
                    sessionKey=self.session_key,
                    method="GET",
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True,
                )
           return self._get_testid_to_user_account_group(response_content)
           
        except Exception as e:
            self._log('error', f"Failed to get test metrics stream configuration: {e}")
            raise e
        
    def _get_testid_to_user_account_group(self, response_content):
        """
        Returns a dict: testid (str) -> set(thousandeyes_user, thousandeyes_acc_group_number)
        """
        mapping = {}
        data = json.loads(response_content)
        for entry in data.get("entry", []):
            content = entry.get("content", {})
            cea_tests = content.get("cea_tests", "")
            user = content.get("thousandeyes_user")
            acc_group = content.get("thousandeyes_acc_group")
            acc_group_number = None
            if acc_group:
                match = re.search(r"\(([^)]+)\)", acc_group)
                if match:
                    acc_group_number = match.group(1)
            if not user or not acc_group_number:
                self._log('error', f"Invalid account configuration for user {user} and account group {acc_group}. Skipping.")
                continue
            self._add_tests_to_mapping(mapping, cea_tests, user, acc_group_number)
        return mapping


    def _add_tests_to_mapping(self, mapping, cea_tests, user, acc_group_number):
        """
        Adds test ids from cea_tests to the mapping dict for the given user and account group.
        """
        for test in cea_tests.split("~"):
            test = test.strip()
            if not test:
                continue
            test_id = self._extract_test_id(test)
            if test_id:
                if test_id not in mapping:
                    mapping[test_id] = set()
                mapping[test_id].add((user, acc_group_number))
            else:
                self._log('error', f"Failed to parse test {test} for user {user} and account group {acc_group_number}. Skipping.")

    def _extract_test_id(self, test_str):
        """
        Extracts the test id from a test string like 'A (id-1 | foo)'
        Returns the test id as a string, or None if format is invalid.
        """
        if "(" in test_str and "|" in test_str:
            try:
                return test_str.split("(")[1].split("|")[0].strip()
            except Exception:
                self._log('error', f"Failed to parse test string: {test_str}")
                return None
        return None
    
    def _log(self, level, msg, *args, **kwargs):
        getattr(self.logger, level)(f"ITSIEventSender - {msg}", *args, **kwargs)
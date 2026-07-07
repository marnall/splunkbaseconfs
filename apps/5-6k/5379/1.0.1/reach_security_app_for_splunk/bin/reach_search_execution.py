# Standard library imports
import sys
import os
import io
from datetime import datetime, timedelta
import time
import json
import csv
import gzip
import shutil
import hashlib
import re

# Local imports
from reach_threadpool import ThreadPool
import splunklib.results as results
import splunklib.client as client
import reach_search_execution_helper

# Default threads is set to 8 because of default search concurrency limit of splunk
DEFAULT_NUM_THREADS = 8


class SearchExecution:
    """ Class to execute searches and store results. """

    def __init__(
        self, session_key, current_day, base_result_path, settings_content, logger, start_day=None
    ):
        """
        Init method of SearchExecution class.
        :param session_key: current session key of Splunk
        :param current_day: current day of the time range
        :param base_result_path: path to store the results
        :param settings_content: content of reach_security_app_for_splunk_settings.conf file
        :param logger: logging object
        :param start_day: start day of the time range
        """
        self.session_key = session_key
        self.logger = logger
        self.base_result_path = base_result_path
        self.date_format = '%Y-%m-%dT%H:%M:%S'
        self.current_day = current_day
        self.settings_content = settings_content
        self.result_header = self.settings_content.get(
            'result_fields', '').split(",")
        # Result file path
        self.result_path = os.path.sep.join(
            [self.base_result_path, "result_{}".format(int(time.time()))])
        # Find start date
        self.start_day = start_day if start_day else self.__find_start_day()
        # Get the earliest and latest time for which data is available
        self.__get_earliest_latest_time()

    def __find_start_day(self):
        """
        Find start day based on starts_from parameter.
        """
        starts_from = int(self.settings_content.get('starts_from', 90))
        current_day = datetime.strptime(self.current_day, self.date_format)
        starts_from = current_day - timedelta(days=starts_from)
        start_day = datetime.strftime(starts_from, self.date_format)
        self.logger.debug(
            "Reach Debug: Start day is set to {}".format(start_day))
        return start_day

    def __get_time_range(self, current_day, start_day):
        """
        Get the time range between two dates.
        :param current_day: end day of the time range
        :param start_day: start day of the time range
        :return list of times between start and end day
        """
        beg_day = datetime.strptime(start_day, self.date_format)
        end_day = datetime.strptime(current_day, self.date_format)
        # Increment day by 1 and keep only date
        beg_day = datetime.strptime((beg_day + timedelta(days=1)).strftime(
            self.date_format).split('T')[0] + "T00:00:00", self.date_format)
        # Decrement day by 1 and keep only date
        end_day = datetime.strptime((end_day - timedelta(days=1)).strftime(
            self.date_format).split('T')[0] + "T00:00:00", self.date_format)

        return [start_day] + [(beg_day + timedelta(days=x)).strftime(self.date_format)
                              for x in range((end_day - beg_day).days + 2)]

    def __find_days_to_exclude(self):
        """
        Finds already available files.
        :return: list of days for which data already exist
        """
        days_to_exclude = []
        if not os.path.exists(self.result_path):
            return days_to_exclude
        try:
            for res_file in os.listdir(self.result_path):
                res_time = res_file.split('.')[0].split('_')[-1].split('T')
                res_time = res_time[0] + 'T' + res_time[1].replace('-', ':')
                days_to_exclude.append(res_time)
        except Exception as e:
            self.logger.warn(
                "Reach Warning: Not able to get days from the list of available files,"
                " Going with default configuration. Error: " + str(e))

        return days_to_exclude

    def __get_earliest_latest_time(self):
        """
        Executes search to find the earliest and latest time in which data is available.
        """
        port = reach_search_execution_helper.get_mgmt_port(self.session_key, self.logger)
        args = {'token': self.session_key, 'port': port}
        time_filter = {
            "earliest_time": self.start_day,
            "latest_time": self.current_day,
            "search_mode": "normal"
        }
        self.available_earliest_latest = (0, 0)
        self.logger.debug(
            "Reach Debug: Finding earliest and latest time "
            "with time filter: {}".format(time_filter))
        try:
            # Execute blocking search
            service = client.connect(**args)
            rr = results.ResultsReader(service.jobs.oneshot(
                "search `reach_configured_index` `reach_configured_sourcetypes` "
                "| stats min(_time) as min_time max(_time) as max_time "
                "| eval max_time = max_time+1 "
                "| convert timeformat={} ctime(min_time) ctime(max_time)".format(
                    self.date_format), **time_filter))

            # Parse result
            for result in rr:
                if isinstance(result, dict):
                    self.available_earliest_latest = (
                        result.get('min_time'), result.get('max_time'))
                    self.logger.debug(
                        "Reach Debug: Available earlist and latest "
                        "time are: " + str(self.available_earliest_latest))
                    self.start_day, self.current_day = self.available_earliest_latest[
                        0], self.available_earliest_latest[1]
                    break
        except Exception:
            self.logger.warn(
                "Reach Warning: Not able to find earlist and latest time of data."
                " Searches will be executed for all the days configured.")
            # Reset
            self.available_earliest_latest = None

    def __get_partial_dir(self):
        """
        Get the list of paths list of containing older files.
        :return: list of directory paths
        """
        return [os.path.sep.join([self.base_result_path, directory])
                for directory in os.listdir(self.base_result_path)
                if os.path.isdir(os.path.sep.join([self.base_result_path, directory]))]

    def __create_time_filter(self):
        """
        Create time filter to pass while executing query based on time range.
        """
        self.time_range_filter = []
        include_days = list(set(self.time_range) - set(self.__find_days_to_exclude()))
        length = len(self.time_range)
        # Iterate through valid time range
        for itr in range(length):
            if self.time_range[itr] not in include_days:
                continue
            next_day = (datetime.strptime(
                self.time_range[itr], self.date_format) + timedelta(days=1)).strftime(
                    self.date_format)
            # Update next day to current time for last frame
            if itr == length - 1:
                next_day = self.current_day \
                    if not self.available_earliest_latest else self.available_earliest_latest[1]
            # Update next day to end on the same day to keep day wise files
            elif itr == 0:
                next_day = next_day.split('T')[0] + "T00:00:00"
            time_filter = {
                "earliest_time": self.time_range[itr],
                "latest_time": next_day,
                "search_mode": "normal",
                "exec_mode": "blocking",
                "preview": True
            }
            self.time_range_filter.append(time_filter)

    def __replace_values(self, match_obj):
        """
        Replace the value of matchig group with anonymized value.
        :param match_obj: object of re lib
        :return: partial anonymized value
        """
        return match_obj.group(0).replace(
            match_obj.group(1), self.__hash_value(match_obj.group(1)))

    def __hash_value(self, value):
        """
        Hash the input string.
        :param value: string to be hashed
        :return: hashed value
        """
        return hashlib.sha256(str(value).encode()).hexdigest()

    def do_cleanup(self):
        """
        Remove all the files and folder except result file.
        """
        self.logger.debug("Reach Debug: Starting the Clean up task")
        if not os.path.exists(self.base_result_path) or not self.result_path.endswith("zip"):
            self.logger.debug(
                "Reach Debug: Result file do not exist hence no clean up")
            return
        # Iterate trough the list of available files/folders
        for files in os.listdir(self.base_result_path):
            file_path = os.path.sep.join([self.base_result_path, files])
            # Remove the file/folder if it's not result file
            if file_path != self.result_path:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)

        self.logger.debug("Reach Debug: Completed the Clean up task")

    def archive_result(self):
        """
        Archive the result folder.
        """
        self.logger.debug("Reach Debug: Archiving the result folder")
        if os.path.exists(self.result_path):
            for res_file in os.listdir(self.result_path):
                if res_file.endswith("partial"):
                    self.logger.warn(
                        "Reach Warning: Not archiving the result as partial files exist")
                    raise Exception(
                        "Not archiving the result as partial files exist")
            shutil.make_archive(self.result_path, 'zip', self.result_path)
            self.logger.debug(
                "Reach Debug: Result file archieved successfully")
            self.result_path = os.path.sep.join(
                [self.base_result_path, self.result_path.split(os.sep)[-1] + ".zip"])

    def convert_to_csv(self, result):
        """
        Convert Result to CSV from Dict.
        :param result: event returned by search execution
        :return: comma separated values of header fields
        """
        res = []
        for field in self.result_header:
            # Keep the value of the fields in double quotes
            res.append(result.get(field, ''))
        return res

    def do_partial_anonymization(self, result, field, pattern_type):
        """
        Partially anonymize the value of result field.
        :param result: event returned by search execution
        :param field: field to be partiall anonymized
        :param pattern_type: type of pattern to match with
        """
        pattern = {
            "comma_pattern": re.compile('CN=(.*?[^\\\\])(?:,|$)'),
            "mail_pattern": re.compile("(?:[,]?smtp:\/\/|^|,)([^@]+)[^,]*")
        }
        field_value = result[field]
        if not isinstance(field_value, list):
            result[field] = pattern[pattern_type].sub(
                self.__replace_values, result[field])
        else:
            temp_list = []
            for value in field_value:
                temp_list.append(pattern[pattern_type].sub(
                    self.__replace_values, value))
            result[field] = temp_list
        # Pattern didn't match need to anonymize whole value
        if field_value == result[field]:
            return False
        return True

    def anonymize_data(self, result):
        """
        Annonymize configured fields from the result.
        :param result: event returned by search execution
        :return: anonymized result
        """
        # If anonymize_fields is not set then no need to anonymize
        if not int(self.settings_content.get('anonymize_fields', 0)):
            return result
        fields_to_anonymize = self.settings_content.get(
            'fields_to_anonymize', '').split(",")

        partial_anonymized_fields = {
            "comma_pattern": ["directReports", "distinguishedName", "managedBy",
                              "managedObjects", "manager", "memberOf"],
            "mail_pattern": ["mail", "proxyAddresses", "user", "userPrincipalName",
                             "ccAddresses{}", "fromAddress{}", "headerFrom", "headerReplyTo",
                             "recipient{}", "sender", "toAddresses{}"]
        }

        # Anonymize the configured fields
        try:
            for field in fields_to_anonymize:
                if not result.get(field):
                    continue
                partial_anonymization = False
                if field in partial_anonymized_fields["comma_pattern"]:
                    partial_anonymization = self.do_partial_anonymization(
                        result, field, "comma_pattern")
                elif field in partial_anonymized_fields["mail_pattern"]:
                    partial_anonymization = self.do_partial_anonymization(
                        result, field, "mail_pattern")
                if not partial_anonymization:
                    result[field] = self.__hash_value(result[field]) if not isinstance(
                        result[field], list) else [self.__hash_value(value)
                                                   for value in result[field]]
        except Exception as e:
            self.logger.error(
                "Reach Error: Error while anonymizing the event. Error: " + str(e))
            raise

        return result

    def write_event(self, reader, file_object, offset):
        """
        Write the event to file.
        :param reader: object of ResultsReader
        :param file_object: object of file to write
        :return: number of events
        """
        # Write CSV header
        w = csv.writer(file_object)
        if offset == 0:
            w.writerow(self.result_header)
        count = 0
        for result in reader:
            if isinstance(result, dict):
                count += 1
                # Anonymize data
                result = self.anonymize_data(result)
                # Convert to CSV from ordered dict
                result = self.convert_to_csv(result)
                # Write result
                w.writerow(result)
        return count

    def read_results(self, blockingsearch_result, time_filter, result_count):
        """
        Read and Store the results of exported search.
        :param blockingsearch_result: object of executed search
        :param time_filter: time range filter to execute search
        """
        # Create a result path with 'partial' suffix
        result_file = os.path.sep.join([self.result_path, "result_{}.csv.partial".format(
            time_filter['earliest_time'].replace(':', '-'))])

        self.logger.debug(
            "Reach Debug: Writing the results for time filter: {}".format(time_filter))
        # Create result file with only header in case of error while searching
        if not blockingsearch_result:
            self.logger.debug(
                "Reach Debug: Creating empty result file for time filter: {}".format(time_filter))
            with open(result_file, 'ab') as f_res:
                with gzip.GzipFile(filename=result_file.replace(".partial", ""),
                                   mode="ab",
                                   fileobj=f_res) as g_res:
                    if sys.version_info >= (3, 0):
                        with io.TextIOWrapper(g_res,
                                              encoding='utf-8-sig',
                                              newline='') as t_res:
                            w = csv.writer(t_res)
                            w.writerow(self.result_header)
                    else:
                        w = csv.writer(g_res)
                        w.writerow(self.result_header)
            return

        r_count = 50000
        offset = 0
        count = 0
        while offset < int(result_count):
            # Read the results
            reader = results.ResultsReader(blockingsearch_result.preview(
                **{'count': r_count, 'offset': offset}))
            # Write results into gzip file

            with open(result_file, 'ab') as f_res:
                with gzip.GzipFile(filename=result_file.replace(".partial", ""),
                                   mode="ab",
                                   fileobj=f_res) as g_res:
                    if sys.version_info >= (3, 0):
                        with io.TextIOWrapper(g_res, encoding='utf-8-sig', newline='') as t_res:
                            count += self.write_event(reader, t_res, offset)
                    else:
                        count += self.write_event(reader, g_res, offset)
            offset += r_count

        self.logger.debug(
            "Reach Debug: Number of events fetched for time filter:"
            " {} is {}.".format(time_filter, count))
        # Remove 'partial' suffix
        os.rename(result_file, result_file.replace('partial', 'gz'))
        self.logger.debug(
            "Reach Debug: Completed writing the results for time filter:"
            " {}".format(time_filter))

    def execute_search_util(self, time_filter):
        """
        Execute and Read results for the given time filter.
        :param time_filter: time range filter to execute search
        """
        try:
            # Execute search
            port = reach_search_execution_helper.get_mgmt_port(self.session_key, self.logger)
            self.logger.debug(
                "Reach Debug: Starting the search execution for time filter:"
                " {}".format(time_filter))
            service = client.connect(**{'token': self.session_key, 'port': port})
            blockingsearch_result = service.jobs.create(self.searchquery_export, **time_filter)
            self.logger.debug("Reach Debug: Result count for executed search is {}".format(
                blockingsearch_result["resultCount"]))
        except Exception as e:
            self.logger.error(
                "Reach Error: Error occurred while executing search for time filter: {},"
                " Error: {}".format(time_filter, e))
            blockingsearch_result = None

        self.logger.debug(
            "Reach Debug: Completed the search execution for time filter: {}".format(time_filter))
        try:
            # Read the results
            self.read_results(blockingsearch_result, time_filter,
                              blockingsearch_result["resultCount"])
        except Exception as e:
            self.logger.error(
                "Reach Error: Error occurred while reading and writing the results for time"
                " filter: {}, Error: {}".format(time_filter, e))

    def execute_search(self):
        """
        To Start the query exution and result collection.
        """
        # Return If data isn't available
        if self.available_earliest_latest == (0, 0):
            self.logger.debug("Reach Debug: Data isn't available")
            return True

        # Get list of time range filter
        try:
            self.__create_time_filter()
        except Exception as e:
            self.logger.error(
                "Reach Error: Error while creating time range filter. Error: " + str(e))
            raise e

        # Create result directory if not already exist
        if not os.path.exists(self.result_path):
            os.makedirs(self.result_path)

        self.searchquery_export = 'search `reach_configured_index` `reach_configured_sourcetypes`'\
            ' | eval product_name=case(like(sourcetype,"%ActiveDirectory%"), "Active Directory",'\
            ' like(sourcetype,"%pan%"), "PAN-OS", like(sourcetype,"%proofpoint_tap_siem%"),'\
            ' "Proofpoint TAP") | table {}'.format(
                json.dumps(self.result_header)[1:-1])

        # Crate pool of threads
        min_threads = min(DEFAULT_NUM_THREADS, len(self.time_range_filter))
        self.logger.debug(
            "Reach Debug: Number of threads is set to {}".format(min_threads))
        pool = ThreadPool(min_threads, self.logger)

        # Execute tasks for each filter
        pool.map(self.execute_search_util, self.time_range_filter)

        # Wait for threads to complete
        pool.wait_completion()
        self.logger.debug("Reach Debug: Completed the search execution.")

        # Compress the result folder
        try:
            self.archive_result()
        except Exception as e:
            self.logger.error(
                "Reach Error: Error while archiving the result folder. Error: " + str(e))
            raise e

        # Remove the folder
        try:
            self.do_cleanup()
        except Exception:
            self.logger.warn(
                "Reach Warning: Not able to clean the folders after archiving.")

        return self.result_path

    def remove_older_files(self):
        """
        Remove the older files/folder if exist.
        """
        self.time_range = self.__get_time_range(
            self.current_day, self.start_day)
        # Return if directory does not exist
        if not os.path.exists(self.base_result_path):
            return

        # Get the path of older directory
        old_result_path = self.__get_partial_dir()
        # Return if directory does not exist
        if not old_result_path:
            return
        # There will always be atmost 1 directory
        old_result_path = old_result_path[0]
        # Iterate over all the files of directory
        dir_list = os.listdir(old_result_path)
        for res_file in dir_list:
            if res_file.endswith('partial'):
                self.logger.debug(
                    "Reach Debug: Removing the older partial file name: " + str(res_file))
                os.remove(os.path.sep.join([old_result_path, res_file]))
                continue
            # Remove the file if it's Older (not in the valid time range)
            res_time = res_file.split('.')[0].split('_')[-1].split('T')
            res_time = res_time[0] + 'T' + res_time[1].replace('-', ':')
            if not any([True for valid_time in self.time_range if valid_time in res_time]):
                self.logger.debug(
                    "Reach Debug: Removing the older file name: " + str(res_file))
                os.remove(os.path.sep.join([old_result_path, res_file]))

        # Rename the older folder name with new name
        os.rename(old_result_path, self.result_path)

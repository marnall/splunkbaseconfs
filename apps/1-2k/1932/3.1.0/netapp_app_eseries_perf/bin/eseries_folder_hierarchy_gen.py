"""This file contains logic of folder hierarchy generation."""

import sys
import collections
import csv
import nses_utils as utils
import logger_manager as log
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

_LOGGER = log.setup_logging("netapp_app_eseries_perf_folder_lookup")
csv_file_path = splunk_lib_util.make_splunkhome_path(
    ["etc", "apps", "netapp_app_eseries_perf", "lookups", "array_folder_hierarchy.csv"])


def hierarchy(res_list, folder_id):
    """Check hierarchy."""
    if folder_id not in res_list:
        return folder_id
    elif res_list[folder_id][0] == "__root__":
        return res_list[folder_id][1]
    else:
        return hierarchy(res_list, res_list[folder_id][0]) + "/" + res_list[folder_id][1]


if __name__ == "__main__":
    session_key = sys.stdin.readline().strip()
    try:
        results = utils.execute_search(
            'search `get_nesa_index` sourcetype="eseries:webproxy" earliest="-60m" latest="now" '
            '| rename name as folderName | dedup folderId | table folderId folderName parentFolderId',
            session_key)
        result_dict = collections.defaultdict(list)
        csv_dict = []

        if results is not None:
            for i, data in enumerate(results):
                result_dict[str(data['folderId'])] = [str(data['parentFolderId']), str(data['folderName']), '']

            for key in result_dict:
                if result_dict[key][0] == "__root__":
                    csv_dict.append((key, result_dict[key][1]))
                else:
                    csv_dict.append((key, hierarchy(result_dict, result_dict[key][0]) + "/" + result_dict[key][1]))

            csv_file = open(csv_file_path, 'wt')
            try:
                writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
                writer.writerow(('folderId', 'fullPath'))
                for line in csv_dict:
                    writer.writerow(line)
            except Exception:
                _LOGGER.exception(
                    "NetApp SANtricity Performance App for Splunk Enterprise Error:"
                    " Unable to generate folder_hierarchy lookup. Please contact administrator.")
            finally:
                csv_file.close()

    except Exception:
        _LOGGER.exception(
            "NetApp SANtricity Performance App for Splunk Enterprise Error:"
            " Unable to generate folder_hierarchy lookup. Please contact administrator.")
        sys.exit(3)

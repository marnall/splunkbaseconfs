import ta_analyst1_declare  # noqa: F401
import splunk.admin as admin
import splunk.rest as rest
import base64
import json
import sys
import traceback
from analyst1_logging import get_logger


class CstmHitStats(admin.MConfigHandler):
    """Update Savedsearches, conf data."""

    default_cron_sched_create_csv = "0 */{} * * *"
    default_description_create_csv = "Push Hit Stats to Analyst1 with {}"
    default_basic_search_query = "earliest=`analyst1_get_earlist_time` {base_search}" + \
    "| eval indicator='{indicator_field}', dim01=\"analyst1_\"+$index$+\"-\"+\"{indicator_field}\"," + \
    "dim02=\"{name}\" {dimension3}, time=strftime(_time, \"%Y-%m-%d\") " + \
    "| stats count by time, indicator, dim01, dim02{stats_dimension3} " + \
    "| sort 0 time, indicator | outputlookup $name$.csv.gz"


    default_summary_search_query = "earliest=`analyst1_get_earlist_time` {base_search}" + \
    "| dedup {indicator_field} | eval indicator='{indicator_field}', dim01=\"analyst1_\"+$index$+\"-\"+\"{indicator_field}\"," + \
    "dim02=\"{name}\" {dimension3}, time=strftime(_time, \"%Y-%m-%d\"), count='{count_field}' " + \
    "| table time, indicator, dim01, dim02{stats_dimension3}, count " + \
    "| sort 0 time, indicator | outputlookup $name$.csv.gz"


    default_saved_search_structure = {
        "name": {},
        "search": {},
        "cron_schedule": {},
        "actions": "push_hit_stats",
        "action.push_hit_stats.param.output_name": {},
        "alert_type": "number of events",
        "alert_threshold": 0,
        "alert_comparator": "greater than",
        "is_scheduled": 1,
        "description": {},
    }

    def setup(self):
        """To setup the variables to access in list."""
        self.supportedArgs.addOptArg("structure")

    def create_settings_conf_file(self, conf_content):
        """
        Create stanza in ta_analyst1_hit_stats.conf file.

        :param conf_content: content to post with stanza_name in name key
        """
        # Make POST request
        try:
            self.app_name = ta_analyst1_declare.ta_name
            self.conf_endpoint = (
                "/servicesNS/nobody/{}/configs/"
                "conf-ta_analyst1_hit_stats/".format(self.app_name)
            )
            _, _ = rest.simpleRequest(
                self.conf_endpoint,
                method="POST",
                sessionKey=self.getSessionKey(),
                postargs=conf_content,
                raiseAllErrors=True,
            )
        except Exception:
            self.logger.error(
                "message=unknown_error | Unknown error occured while saving Hit Stats Output Configuration: {}".format(
                    traceback.format_exc()
                )
            )
            sys.exit()
        else:
            self.logger.info(
                "message=create_hit_stats | Created Hit Stats stanza in ta_analyst1_hit_stats: {}".format(
                    conf_content.get("name")
                )
            )

    def delete_settings_conf_file(self, stanza_name):
        """
        Delete stanza in ta_analyst1_hit_stats.conf file.

        :param stanza_name: content to delete with stanza_name
        """
        # Make DELETE request
        try:
            self.app_name = ta_analyst1_declare.ta_name
            self.conf_endpoint = (
                "/servicesNS/nobody/{}/configs/"
                "conf-ta_analyst1_hit_stats/{}".format(self.app_name, stanza_name)
            )
            _, _ = rest.simpleRequest(
                self.conf_endpoint,
                method="DELETE",
                sessionKey=self.getSessionKey(),
                raiseAllErrors=True,
            )
        except Exception:
            self.logger.error(
                "message=unknown_error | Unknown error occured while deleting Hit Stats Output "
                "Configuration: {}".format(
                    traceback.format_exc()
                )
            )
            sys.exit()
        else:
            self.logger.info(
                "message=delete_hit_stats | Deleted Hit Stats stanza in ta_analyst1_hit_stats: {}".format(
                    stanza_name
                )
            )

    def create_savedsearches_conf_file(self, conf_content):
        """
        Create stanza in savedsearches.conf file.

        :param conf_content: content to post with stanza_name in name key
        """
        # Make POST request
        try:
            self.app_name = ta_analyst1_declare.ta_name
            self.conf_endpoint = "/servicesNS/nobody/{}/saved/searches/".format(
                self.app_name
            )
            _, _ = rest.simpleRequest(
                self.conf_endpoint,
                method="POST",
                sessionKey=self.getSessionKey(),
                postargs=conf_content,
                raiseAllErrors=True,
            )
        except Exception:
            self.logger.error(
                "message=unknown_error | Unknown error occured while saving Hit Stats Output Savedsearch: {}".format(
                    traceback.format_exc()
                )
            )
            sys.exit()
        else:
            self.logger.info(
                "message=create_hit_stats | Created Hit Stats Savedsearch: {}".format(
                    conf_content.get("name")
                )
            )

    def delete_savedsearches_conf_file(self, stanza_name):
        """
        Delete stanza in savedsearches.conf file.

        :param stanza_name: content to delete with stanza_name
        """
        # Make DELETE request
        try:
            self.app_name = ta_analyst1_declare.ta_name
            self.conf_endpoint = "/servicesNS/nobody/{}/saved/searches/{}".format(
                self.app_name, stanza_name
            )
            _, _ = rest.simpleRequest(
                self.conf_endpoint,
                method="DELETE",
                sessionKey=self.getSessionKey(),
                raiseAllErrors=True,
            )
        except Exception:
            self.logger.error(
                "message=unknown_error | Unknown error occured while deleting Hit Stats Output Savedsearch: {}".format(
                    traceback.format_exc()
                )
            )
            sys.exit()
        else:
            self.logger.info(
                "message=delete_hit_stats | Deleted Hit Stats Savedsearch: {}".format(
                    stanza_name
                )
            )

    def handleList(self, conf_info):
        """Get data.

        But we don't have any get call so just pass the method.
        """
        pass

    def handleRemove(self, conf_info):
        """Delete hit stats configuration.

        Delete from ta_analyst1_hit_stats.conf and savedsearches.conf
        """
        try:
            name = self.callerArgs.data.get("structure")
            data = base64.b64decode(name[0]).decode()
            data = json.loads(data)

            self.logger = get_logger("ta_analyst1_hit_stats")

            self.delete_settings_conf_file(data.get("name"))
            self.delete_savedsearches_conf_file(data.get("name"))
        except Exception as e:
            self.logger.error(
                "message=unknown_error | Unknown error occured while deleting Hit Stats"
                " Output Configuration: {}".format(
                    traceback.format_exc()
                )
            )
            raise Exception(e)

    def handleEdit(self, conf_info):
        """Get the data from dashboard fields and create.

        create in ta_analyst1_hit_stats.conf and savedsearches.conf.
        """
        try:
            name = self.callerArgs.data.get("structure")
            data = base64.b64decode(name[0]).decode()
            data = json.loads(data)

            self.logger = get_logger("ta_analyst1_hit_stats")

            self.create_settings_conf_file(data)
            dimension3 = data.get("dimension3", "")
            if dimension3 == "":
                stats_dimension3 = ""
                dimension3 = ""
            else:
                stats_dimension3 = ", {}".format("dim03")
                dimension3 = (
                    ", dim03=if(isnotnull('{dimension3}'),'{dimension3}',\"\")".format(
                        dimension3=dimension3
                    )
                )

            if data.get("mode") == "Basic":
                self.default_saved_search_structure["name"] = data.get("name")
                self.default_saved_search_structure[
                    "action.push_hit_stats.param.output_name"
                ] = data.get("name")
                self.default_saved_search_structure[
                    "search"
                ] = self.default_basic_search_query.format(
                    base_search=data.get("base_search"),
                    indicator_field=data.get("indicator_field"),
                    name=data.get("name"),
                    dimension3=dimension3,
                    stats_dimension3=stats_dimension3,
                )
                self.default_saved_search_structure[
                    "description"
                ] = self.default_description_create_csv.format(data.get("name"))
                self.default_saved_search_structure[
                    "cron_schedule"
                ] = self.default_cron_sched_create_csv.format(data.get("frequency"))
                self.create_savedsearches_conf_file(self.default_saved_search_structure)
            elif data.get("mode") == "Summary":
                self.default_saved_search_structure["name"] = data.get("name")
                self.default_saved_search_structure[
                    "action.push_hit_stats.param.output_name"
                ] = data.get("name")
                self.default_saved_search_structure[
                    "search"
                ] = self.default_summary_search_query.format(
                    base_search=data.get("base_search"),
                    indicator_field=data.get("indicator_field"),
                    name=data.get("name"),
                    dimension3=dimension3,
                    stats_dimension3=stats_dimension3,
                    count_field=data.get("count_field"),
                )
                self.default_saved_search_structure[
                    "description"
                ] = self.default_description_create_csv.format(data.get("name"))
                self.default_saved_search_structure[
                    "cron_schedule"
                ] = self.default_cron_sched_create_csv.format(data.get("frequency"))
                self.create_savedsearches_conf_file(self.default_saved_search_structure)
            else:
                self.logger.error(
                    "message=invalid_mode | Invalid mode given, it should be either Basic or Summary."
                )
                sys.exit()
        except Exception as e:
            self.logger.error(
                "message=unknown_error | Unknown error occured while saving Hit Stats Output Configuration: {}".format(
                    traceback.format_exc()
                )
            )
            raise Exception(e)


if __name__ == "__main__":
    """Driving function."""
    admin.init(CstmHitStats, admin.CONTEXT_NONE)

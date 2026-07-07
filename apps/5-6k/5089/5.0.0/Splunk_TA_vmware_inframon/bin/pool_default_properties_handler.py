# importing core python packages
import json
import sys

# splunk sdk imports
import splunk.admin as admin
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing rest_utility
from rest_utility import setup_logger, RestError

# defining constants
file_path = make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin', 'pool_default_properties.json'])
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
logger = setup_logger(log_name="pool_configuration.log",
                      logger_name="pool_configuration")


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
                This is used for adding optional and required arguments for particular requests."""
        pass

    def handleList(self, conf_info):
        """When GET request is done on the endpoint pool_default_properties, this method is called,
        It returns the details of task, default fields and additional fields."""
        try:
            fp = open(file_path)
            json_dict = json.load(fp)
            task_dict = json_dict.pop("default_task", {})

            additional_fields_dict = json_dict["additional_fields"]
            additional_field_response = {}
            for entity, fields in additional_fields_dict.items():
                additional_field_response.update({entity: list(fields.keys())})

            default_field_dict = json_dict["default_fields"]
            default_field_response = {}

            for entity, fields in default_field_dict.items():
                default_field_response.update({entity: list(fields.keys())})

            conf_info["data"]["tasks"] = json.dumps(task_dict)
            conf_info["data"]["default_fields"] = json.dumps(default_field_response)
            conf_info["data"]["additional_fields"] = json.dumps(additional_field_response)

            fp.close()
        except ValueError as e:
            logger.error("Non valid JSON content in pool_default_properties.json.")
            logger.exception(e)
            raise RestError(500, "Non valid JSON content in pool_default_properties.json.")
        except IOError as e:
            logger.error("Failed to find pool_default_properties.json.")
            logger.exception(e)
            raise RestError(500, "Failed to find pool_default_properties.json.")
        except Exception as e:
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)

from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import logging
import sys


SPLUNK_DIR = Path(environ['SPLUNK_HOME']).absolute()
APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(
    SPLUNK_DIR /
    'etc' /
    'apps' /
    APP_NAME
)
BIN_DIR = Path(APP_DIR / 'bin')
LOCAL_DIR = Path(APP_DIR / 'local')
CONFIG_FILE = Path(LOCAL_DIR / 'security_stack_config.json')


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_security_stack_config_get_config_rest_endpoint'
)


class GetSecurityStackConfig(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        try:
            if CONFIG_FILE.is_file():
                with open(str(CONFIG_FILE), 'r') as config_file:
                    payload = {
                        'config': json.load(config_file),
                        'status': 200,
                        'error': None,
                        'message': 'success'
                    }

                logger.info(f'status="success", message="Successfully loaded security_stack_config.json, preparing response."')

            else:
                with open(str(CONFIG_FILE), 'w+') as config_file:
                    json.dump(
                        get_ssc_template(),
                        config_file,
                        indent=2,
                        default=str
                    )

                with open(str(CONFIG_FILE), 'r') as config_file:
                    config = json.load(config_file)

                payload = {
                    'config': config,
                    'status': 200,
                    'error': None,
                    'message': 'success'
                }

        except Exception as e:
            payload = {
                'error': str(e),
                'message': f'An error occurred while loading the security stack config file: {str(e)}',
                'config': None,
                'status': 500
            }

            logger.error(f'status="ERROR", message="An error occurred while loading the security stack config file: {str(e)}"')

            
        self.log_stop_message()


        return {
            'payload': payload,
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Security Stack Config: get_config REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Security Stack Config: get_config REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


def get_ssc_template():
    return {
        "default_system": {
            "endpoint_security": {
                "antimalware_solutions": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "application_controls": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "file_integrity_monitoring": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "mobile_device_management": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "patch_management_solution": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "secure_baseline_config": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "vdi": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "session_recording": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "network_security": {
                "network_firewall": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "ids_ips": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "remote_access_vpn": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "wips_wids": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "content_filtering": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "network_baseline_mgmt": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "ntp_mgmt": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "vulnerability_scanning": {
                "vulnerability_scanning": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "mail_and_collaboration": {
                "antispam": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "dlp": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "email": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "phishing_awareness": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "secure_file_sharing": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "core_technology_solutions": {
                "itam": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "cmdb": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "change_control": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "bcdr": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "crypto": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "cert_mgmt": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "threat_hunting_and_other_elevated_security": {
                "log_mgmt": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "soar": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "pen_testing": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "sandbox": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "irp": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "threat_intel_feed": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "forensic_solution": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "risk_assessment": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "identity_and_access_management": {
                "iam": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "pam": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "mfa": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "data_protection": {
                "data_classification": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "data_destruction": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "devops": {
                "app_security_testing": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "physical_facilities": {
                "pac": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "visitor_mgmt": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            },
            "other_software_applications": {
                "hris_hrms": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                },
                "lms": {
                    "deployed": "",
                    "tool_in_place": {
                        "tool": [],
                        "other_tool_name": ""
                    },
                    "comments": ""
                }
            }
        }
    }

'''
    Author: John Southerland josouthe@cisco.com +1.214.734.8099 (AppDynamics Field Architect)
    Sep 3 2024: First version, input config application multiple select drop down https://splunk.github.io/addonfactory-ucc-generator/advanced/dependent_dropdown/
'''
import os
import splunk
import splunk.admin
bin_dir = os.path.dirname(os.path.abspath(__file__))
import import_declare_test
from solnlib import log

logger = log.Logs().get_logger("appdynamics_list_databases")


class ConfigHandler(splunk.admin.MConfigHandler):
    def setup(self):
        self.supportedArgs.addReqArg("global_account")

    def handleList(self, confInfo):  # pylint: disable=invalid-name
        from controller_service import ControllerService
        logger.debug("Running helper to get list of applications")

        '''
        for attr in dir(self.callerArgs):
            logger.debug(f"callerArgs.{attr}: {getattr(self.callerArgs, attr)}")'''
        for attr in dir(confInfo):
            logger.debug(f"confInfo.{attr}: {getattr(confInfo, attr)}")

        opt_global_account_name = getattr(self.callerArgs, "data").get('global_account')[0]
        logger.debug(f"Global Account: {opt_global_account_name}")

        controller = ControllerService(
            global_account_name=opt_global_account_name,
            session_key=self.getSessionKey(),
            duration=5,
            throw_exceptions=True,
            logger=logger,
        )

        def get_section_as_list(apps):
            # This, this is why i hate python
            if not isinstance(apps, list):
                apps = [apps]  # Force it into a list if it's a single item
            return apps

        if not controller.testToken():
            confInfo.addErrorMsg(f"Could not get authentication token, check {controller.get_client_id()} is valid")
            raise Exception(f"Could not get authentication token, check {controller.get_client_id()} is valid")

        try:
            application = controller.get_database_application()
        except Exception as e:
            confInfo.addErrorMsg(f"Could not get database application, check {controller.get_client_id()} has permissions needed")
            raise Exception(f"Could not get database application, check {controller.get_client_id()} has permissions needed")

        try:
            databases = controller.get_databases()
        except Exception as e:
            confInfo.addErrorMsg(f"Could not get database listing, check {controller.get_client_id()} has permissions needed")
            raise Exception(f"Could not get database listing, check {controller.get_client_id()} has permissions needed")

        for db in get_section_as_list(databases):
            logger.debug(f"database: {db}")
            confInfo[f"{db['name']}|{db['id']}|{application['id']}"].append('label', f"{db['name']}")

        confInfo.update()
        logger.debug("finished running application list")


def main():
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == "__main__":
    main()

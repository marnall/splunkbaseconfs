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

logger = log.Logs().get_logger("appdynamics_status_list_options")


class ConfigHandler(splunk.admin.MConfigHandler):
    def setup(self):
        self.supportedArgs.addReqArg("global_account")

    def handleList(self, confInfo):  # pylint: disable=invalid-name
        from controller_service import ControllerService
        import concurrent.futures
        logger.debug("Running helper to get list of permissions on an api key")

        opt_global_account_name = getattr(self.callerArgs, "data").get('global_account')[0]
        logger.debug(f"Global Account: {opt_global_account_name}")

        controller = ControllerService(
            global_account_name=opt_global_account_name,
            session_key=self.getSessionKey(),
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

        def task_apm_app_list(controller, confInfo):
            try:
                controller.get_apm_app_list()
                confInfo["Application Status"].append('label', "Application Status")
                confInfo["Business Transactions"].append('label', "Business Transactions")
                confInfo["Tier Node Status"].append('label', "Tier Node Status")
                confInfo["Remote Services Status"].append('label', "Remote Services Status")
                logger.debug("apm app list check good")
            except Exception as e:
                confInfo.addWarnMsg(f"Could not get list of applications, check {controller.get_client_id()} has the permissions needed")

        def task_database_summary(controller, confInfo):
            try:
                controller.get_database_summary(just_one=True)
                confInfo["Database Status"].append('label', "Database Status")
                logger.debug("database summary check good")
            except Exception as e:
                confInfo.addWarnMsg(f"Could not get database status, check {controller.get_client_id()} has the permissions needed")

        def task_server_summary(controller, confInfo):
            try:
                controller.get_server_summary()
                confInfo["Server Status"].append('label', "Server Status")
                logger.debug("server summary check good")
            except Exception as e:
                confInfo.addWarnMsg(f"Could not get server status, check {controller.get_client_id()} has the permissions needed")

        def task_app_security_summary(controller, confInfo):
            try:
                # Retrieve the list once for use in the security summary
                apm_app_list = controller.get_apm_app_list()
                controller.get_application_security_summary(apm_app_list, just_one=True)
                confInfo["Application Security Status"].append('label', "Application Security Status")
                logger.debug("application security summary check good")
            except Exception as e:
                confInfo.addWarnMsg(f"Could not get application security status, check {controller.get_client_id()} has the permissions needed")

        def task_web_user_experience(controller, confInfo):
            try:
                controller.get_dem_web_summary()
                confInfo["Web User Experience"].append('label', "Web User Experience")
                logger.debug("web user experience check good")
            except Exception as e:
                confInfo.addWarnMsg(f"Could not get Web User Experience status, check {controller.get_client_id()} has the permissions needed")

        def task_mobile_user_experience(controller, confInfo):
            try:
                controller.get_dem_mobile_summary()
                confInfo["Mobile User Experience"].append('label', "Mobile User Experience")
                logger.debug("mobile user experience check good")
            except Exception as e:
                confInfo.addWarnMsg(f"Could not get Mobile User Experience status, check {controller.get_client_id()} has the permissions needed")

        # List the tasks as callables with their arguments.
        tasks = [
            (task_apm_app_list, (controller, confInfo)),
            (task_database_summary, (controller, confInfo)),
            (task_server_summary, (controller, confInfo)),
            (task_app_security_summary, (controller, confInfo)),
            (task_web_user_experience, (controller, confInfo)),
            (task_mobile_user_experience, (controller, confInfo))
        ]

        # Use ThreadPoolExecutor to execute tasks concurrently.
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            # Submit all tasks and store their Future objects.
            futures = [executor.submit(task, *args) for task, args in tasks]

            # Optionally, wait for all tasks to complete.
            for future in concurrent.futures.as_completed(futures):
                try:
                    # .result() will re-raise any exception caught in the task,
                    # but since we already catch exceptions in each task,
                    # this is just a precaution.
                    future.result()
                except Exception as e:
                    logger.error("Unexpected error in task: %s", e)


        '''for attr in dir(confInfo):
            logger.debug(f"confInfo.{attr}: {getattr(confInfo, attr)}")'''

        confInfo.update()
        logger.debug("finished running status list options")


def main():
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == "__main__":
    main()

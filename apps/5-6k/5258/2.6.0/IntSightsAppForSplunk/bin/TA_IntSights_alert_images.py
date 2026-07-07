import ta_intsights_declare     # noqa: F401
import splunk.admin as admin
import splunk.appbuilder as appbuilder
from splunktaucclib.rest_handler import util
from intsights_utils import get_credentials, get_proxy_info, build_url
import uuid
import base64
import requests
import intsights_utils as int_utils
import constants as const
from log_manager import setup_logging
import os


ALERT_IMAGES_ENDPOINT = "/public/v1/apps/splunk/alerts/alert-image/{}"
util.remove_http_proxy_env_vars()
logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0])


class AlertImages(admin.MConfigHandler):
    """Get the Image data."""

    def setup(self):
        """To setup the variables to access in list."""
        self.supportedArgs.addOptArg('image_id')

    def handleList(self, conf_info):
        """Get the image data from API."""
        splunk_session_key = self.getSessionKey()
        account_details = get_credentials("account", splunk_session_key)
        api_key = account_details.get("api_key", "")
        account_id = account_details.get("account_id", "")
        proxies = get_proxy_info(splunk_session_key)
        try:
            # Verifying credentials
            int_utils.verify_authentication(account_details, proxies)
        except Exception as e:
            message = "Error ocurred while authentication : {}".format(e)
            for template in appbuilder.getTemplates():
                conf_info[template].append('image', message)
            logger.error(message)
            raise Exception(message)
            return

        server_address = account_details.get("server_address", "")
        verify_cert = const.VERIFY_SSL
        if not all([api_key, account_id, server_address]):
            message = "IntSights account is not configured!"
            logger.error(message)
            raise ValueError(message)

        alert_id = self.callerArgs.data.get("image_id")
        if alert_id and isinstance(alert_id, list):
            alert_id = alert_id[0]
        encoded_cred = base64.b64encode("{}:{}".format(account_id,
                                        api_key).encode()).decode()
        header = {
            "Authorization": "Basic {}".format(encoded_cred),
            "Accept": "image/jpeg"
        }

        sync_id = str(uuid.uuid4())
        payload = {'syncId': sync_id}
        api_url = ALERT_IMAGES_ENDPOINT.format(alert_id)
        try:
            url = build_url(server_address, api_url)
            # Converting jpeg image data into base64
            img_content = base64.b64encode(
                requests.get(url, verify=verify_cert, headers=header, proxies=proxies, params=payload).content
            )
            img_content = img_content.decode(encoding="utf-8")
            for template in appbuilder.getTemplates():
                conf_info[template].append('image', img_content)
            return img_content

        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            for template in appbuilder.getTemplates():
                conf_info[template].append('image', message)
            logger.error(message)
            raise Exception(message)


if __name__ == "__main__":
    """Driving function."""
    admin.init(AlertImages, admin.CONTEXT_NONE)

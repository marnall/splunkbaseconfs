import splunk.admin as admin
import splunk.rest as rest
import json


class NewAlert(admin.MConfigHandler):
    """On click of Create New Alert in OOTB Alerts dashboard, this code will execute."""

    def setup(self):
        """To setup the variables to access in list."""
        self.supportedArgs.addOptArg("final_data")

    def handleList(self, conf_info):
        """This method is useful to get data but we don't have any get call so just pass the method."""
        pass

    def handleEdit(self, conf_info):
        """Get the new updated alert data from API."""
        try:
            data = self.callerArgs.data.get("final_data")
            session_key = self.getSessionKey()
            data = json.loads(data[0])
            new_search = data["search"].replace('\\"', '"')
            data["search"] = new_search
            path = "/servicesNS/nobody/TeamCymruFeedAppForSplunk/saved/searches/"
            try:
                rest.simpleRequest(
                    path,
                    sessionKey=session_key,
                    postargs=data,
                    method="POST",
                    raiseAllErrors=True,
                )
            except Exception as e:
                raise Exception(e)
        except Exception as e:
            raise Exception(e)


if __name__ == "__main__":
    """Driving function."""
    admin.init(NewAlert, admin.CONTEXT_NONE)

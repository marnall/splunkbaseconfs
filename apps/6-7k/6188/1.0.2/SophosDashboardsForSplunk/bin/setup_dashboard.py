import splunk.admin as admin
import splunk.rest as rest
import os
import xml.etree.ElementTree as ET
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class SetupAppDashboards(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    # Static variables
    XG_FIREWALL_DASHBOARD = 'xg_firewall_data'
    CENTRAL_DASHBOARD = 'central_data'

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in [self.CENTRAL_DASHBOARD, self.XG_FIREWALL_DASHBOARD]:
                self.supportedArgs.addOptArg(arg)
    
    '''
    Read the initial values of the parameters from the custom file
            app_defaults.conf, and write them to the setup screen.
    '''

    def handleList(self, confInfo):
        confDict = self.readConf('app_defaults')
        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in [self.CENTRAL_DASHBOARD, self.XG_FIREWALL_DASHBOARD]:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    confInfo[stanza].append(key, val)
    
    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them in conf file
    '''
    def handleEdit(self, confInfo):
        self.callerArgs.data[self.CENTRAL_DASHBOARD][0] = '1' if int(self.callerArgs.data[self.CENTRAL_DASHBOARD][0]) == 1 else '0'
        self.callerArgs.data[self.XG_FIREWALL_DASHBOARD][0] = '1' if int(self.callerArgs.data[self.XG_FIREWALL_DASHBOARD][0]) == 1 else '0'
        
        session_key = self.getSessionKey()

        # Reorganizing navigation based on user selection
        nav_path_default = make_splunkhome_path(['etc', 'apps', 'SophosDashboardsForSplunk', 'default', 'data', 'ui', 'nav'])

        tree = ET.parse(os.path.join(nav_path_default, 'default.xml'))
        root = tree.getroot()

        # Remove collection
        for view in root.findall('view'):
            name = view.get('name')
            if self.callerArgs.data[self.XG_FIREWALL_DASHBOARD][0] == '0' and name in ["sophosxg_firewall_overview","sophosxg_firewall_top_10","sophosxg_traffic","sophosxg_vpn"]:
                root.remove(view)

        # Convert the XML tree to string
        nav = ET.tostring(root).decode()
        nav_data_to_post = {'eai:data': nav}
        try:
            # Post the updated navigation to default.xml
            rest.simpleRequest(
                "/servicesNS/nobody/SophosDashboardsForSplunk/data/ui/nav/default",
                sessionKey=session_key,
                postargs=nav_data_to_post,
                method="POST",
                raiseAllErrors=True
            )
        except Exception as e:
            raise Exception(e)

        self.writeConf('app_defaults', 'setup_dashboard', self.callerArgs.data)

        # Refresh the local endpoint so that dashboards and is_configured take effect
        try:
            rest.simpleRequest(
                    "/servicesNS/nobody/system/apps/local/SophosDashboardsForSplunk/_reload",
                    sessionKey=session_key,
                    postargs=None,
                    method="POST",
                    timeout=180,
                    raiseAllErrors=True,
                )
        except Exception as e:
            raise Exception(e)
        

if __name__ == "__main__":
    """Driving function."""
    admin.init(SetupAppDashboards, admin.CONTEXT_NONE)

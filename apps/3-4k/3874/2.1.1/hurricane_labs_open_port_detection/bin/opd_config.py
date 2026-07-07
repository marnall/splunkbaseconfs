import splunk.admin as admin
import splunk.rest

# import your required python modules


'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

'''


class OPDConfig(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['connect_shodan']:
                self.supportedArgs.addOptArg(arg)

    '''
    Read the initial values of the parameters from the custom file
        myappsetup.conf, and write them to the setup page.

    If the app has never been set up,
        uses .../app_name/default/myappsetup.conf.

    If app has been set up, looks at
        .../local/myappsetup.conf first, then looks at
    .../default/myappsetup.conf only if there is no value for a field in
        .../local/myappsetup.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.
    '''

    def handleList(self, confInfo):
        s = self.getSessionKey()
        confDict = self.readConfCtx("opd")
        if None != confDict:
            for key, val in confDict['opd'].items():
                confInfo['config'].append(key, val)
        # confInfo["config"]["connect_shodan"] = 0

    '''
    After user clicks Save on setup page, take updated parameters,
    normalize them, and save them somewhere
    '''

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        '''
        Since we are using a conf file to store parameters,
        write them to the [setupentity] stanza
        in app_name/local/myappsetup.conf
        '''

        # if it is currently set to 0 in config but user has checked checkbox on config page to enable
        if args['connect_shodan'][0] == "1":

            # Adding OPD Shodan
            updated_nav = """<nav search_view="search" color="#60496c">
                             <view name="opd" default="true" />
                             <view name="opd_shodan" />
                             <view name="setup" /></nav>"""

            # Enable Lookup populator
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/saved/searches/OPD%20Shodan%20Lookup%20Populator/enable',
                method='POST', sessionKey=self.getSessionKey())

            # Enable Shodan Search
            '''
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/saved/searches/OPD%20Shodan/enable',
                method='POST', sessionKey=self.getSessionKey())
            '''
            # Run Lookup Populator
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/saved/searches/OPD%20Shodan%20Lookup%20Populator/dispatch',
                method='POST', sessionKey=self.getSessionKey())
            '''
            # Run Shodan Search
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/saved/searches/OPD%20Shodan/dispatch',
                method='POST', sessionKey=self.getSessionKey())
            '''
            # Add Navigation Item for Shodan Dashboard
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/data/ui/nav/default',
                method='POST', postargs={'eai:data': updated_nav}, sessionKey=self.getSessionKey())


        elif args['connect_shodan'][0] == "0":

            # Adding OPD Shodan
            updated_nav = """<nav search_view="search" color="#60496c">
                            <view name="opd" default="true" />
                            <view name="setup" />
                            </nav>"""

            # Disable Lookup Populator
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/saved/searches/OPD%20Shodan%20Lookup%20Populator/disable',
                method='POST', sessionKey=self.getSessionKey())
            '''
            # Disable Shodan Search
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/saved/searches/OPD%20Shodan/disable',
                method='POST', sessionKey=self.getSessionKey())
            '''

            # Remove Navigation Item for Shodan Dashboard
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/hurricane_labs_open_port_detection/data/ui/nav/default',
                method='POST', postargs={'eai:data': updated_nav}, sessionKey=self.getSessionKey())

        if 'connect_shodan' in args:
            if args['connect_shodan'] in ['0', '1']:
                self.writeConf('opd', 'opd', {'connect_shodan': args['connect_shodan']})


# initialize the handler
admin.init(OPDConfig, admin.CONTEXT_NONE)

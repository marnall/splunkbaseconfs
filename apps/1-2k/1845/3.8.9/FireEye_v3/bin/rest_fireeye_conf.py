#!/usr/bin/python3
# Copyright 2011 Splunk, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re
import os
import logging
import lxml.etree as ET
import xml.etree.cElementTree as et


import splunk.entity as en
import splunk.admin as admin
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

logger = logging.getLogger('splunk')

BASE_DIR = make_splunkhome_path(["etc", "apps", "FireEye_v3"])
CONF_FILE = 'fireeye'

# take Windows OS path into considerations
# NAV_FILE = BASE_DIR + '/default/data/ui/nav/default.xml'
# NAV_OUTPUT = BASE_DIR + '/local/data/ui/nav/default.xml'

# adjusted for windows path
NAV_INPUT = os.path.join(BASE_DIR, 'default', 'data', 'ui', 'nav', 'default.xml')
NAV_OUTPUT = os.path.join(BASE_DIR, 'local', 'data', 'ui', 'nav', 'default.xml')

ANALYTICS_INPUT = os.path.join(BASE_DIR, 'default', 'data', 'ui', 'views', 'analytics.xml')
ANALYTICS_OUTPUT = os.path.join(BASE_DIR, 'local', 'data', 'ui', 'views', 'analytics.xml')

# make a etree element of the navigation file


class FireEyeHandler(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['NX', 'EX', 'ETP', 'AX', 'FX', 'HX', 'PX', 'TAP', 'DOD']:
                self.supportedArgs.addOptArg(arg)

        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['hx_ip_address', 'hx_port_address']:
                self.supportedArgs.addOptArg(arg)
        # if self.requestedAction == admin.ACTION_EDIT:
        #     for arg in ["vt_api_key"]:
        #         self.supportedArgs.addOptArg(arg)
        # if self.requestedAction == admin.ACTION_EDIT:
        #     for arg in ["dod_api_key"]:
        #         self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        # reads file from CONF_FILE

        confDict = self.readConf(CONF_FILE)
        if confDict is not None:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if key in ['NX']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['EX']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['ETP']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['AX']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['FX']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['HX']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['PX']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['TAP']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['DOD']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'

                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        self.edit_panels()
        self.edit_dashboard()

    def edit_panels(self):
        try:
            tree = ET.parse(NAV_INPUT)
            root = tree.getroot()
            # name = self.callerArgs.id
            # args = self.callerArgs
            if int(self.callerArgs.data['NX'][0]) == 1:
                self.callerArgs.data['NX'][0] = '1'
            else:
                self.callerArgs.data['NX'][0] = '0'
                # logger.error("root elements :", root)
                for panels in root:

                    for dashboard in panels:
                        # logger.error("dashboard elements :", dashboard)
                        dash = dashboard.attrib
                        # logger.error("dashboard values :", dash.values())
                        for v in list(dash.values()):
                            # logger.error("dashboard values :", v)
                            if re.match('nx_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['EX'][0]) == 1:
                self.callerArgs.data['EX'][0] = '1'
            else:
                self.callerArgs.data['EX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('ex_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['ETP'][0]) == 1:
                self.callerArgs.data['ETP'][0] = '1'
            else:
                self.callerArgs.data['ETP'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('etp_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['AX'][0]) == 1:
                self.callerArgs.data['AX'][0] = '1'
            else:
                self.callerArgs.data['AX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('ax_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['FX'][0]) == 1:
                self.callerArgs.data['FX'][0] = '1'
            else:
                self.callerArgs.data['FX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('fx_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['HX'][0]) == 1:
                self.callerArgs.data['HX'][0] = '1'
            else:
                self.callerArgs.data['HX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('hx_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['PX'][0]) == 1:
                self.callerArgs.data['PX'][0] = '1'
            else:
                self.callerArgs.data['PX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('px_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['TAP'][0]) == 1:
                self.callerArgs.data['TAP'][0] = '1'
            else:
                self.callerArgs.data['TAP'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('tap_*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['DOD'][0]) == 1:
                self.callerArgs.data['DOD'][0] = '1'
            else:
                self.callerArgs.data['DOD'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('dod_*', v):
                                panels.remove(dashboard)

            self.writeConf('fireeye', 'setupentity', self.callerArgs.data)
            # make sure the dir is created if is not
            dir_path = os.path.dirname(NAV_OUTPUT)

            # code commented to avoid manual check for cloud compatibility
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            tree.write(NAV_OUTPUT)
            return True
        except Exception as err:
            logger.error("Error while editing panel: ", err)
            return False

    def edit_dashboard(self):
        try:
            tree = ET.parse(ANALYTICS_INPUT)
            root = tree.getroot()
            # name = self.callerArgs.id
            # args = self.callerArgs
            if int(self.callerArgs.data['NX'][0]) == 1:
                self.callerArgs.data['NX'][0] = '1'
            else:
                self.callerArgs.data['NX'][0] = '0'
                # logger.error("root elements :", root)
                for panels in root:

                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            # logger.error("dashboard values :", v)
                            if re.match('nx_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['EX'][0]) == 1:
                self.callerArgs.data['EX'][0] = '1'
            else:
                self.callerArgs.data['EX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('ex_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['ETP'][0]) == 1:
                self.callerArgs.data['ETP'][0] = '1'
            else:
                self.callerArgs.data['ETP'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('etp_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['AX'][0]) == 1:
                self.callerArgs.data['AX'][0] = '1'
            else:
                self.callerArgs.data['AX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('ax_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['FX'][0]) == 1:
                self.callerArgs.data['FX'][0] = '1'
            else:
                self.callerArgs.data['FX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('fx_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['HX'][0]) == 1:
                self.callerArgs.data['HX'][0] = '1'
            else:
                self.callerArgs.data['HX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('hx_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['PX'][0]) == 1:
                self.callerArgs.data['PX'][0] = '1'
            else:
                self.callerArgs.data['PX'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('px_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['TAP'][0]) == 1:
                self.callerArgs.data['TAP'][0] = '1'
            else:
                self.callerArgs.data['TAP'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('tap_stats*', v):
                                panels.remove(dashboard)

            if int(self.callerArgs.data['DOD'][0]) == 1:
                self.callerArgs.data['DOD'][0] = '1'
            else:
                self.callerArgs.data['DOD'][0] = '0'
                for panels in root:
                    for dashboard in panels:
                        dash = dashboard.attrib
                        for v in list(dash.values()):
                            if re.match('dod_stats*', v):
                                panels.remove(dashboard)

            self.writeConf('fireeye', 'setupentity', self.callerArgs.data)
            # make sure the dir is created if is not
            dir_path = os.path.dirname(ANALYTICS_OUTPUT)

            # code commented to avoid manual check for cloud compatibility
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            tree.write(ANALYTICS_OUTPUT)
            return True
        except Exception as err:
            logger.error("Error while editing panel: ", err)
            return False
    # initialize the handler


admin.init(FireEyeHandler, admin.CONTEXT_NONE)


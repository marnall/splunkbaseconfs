from __future__ import absolute_import
import logging
import os
import sys
import json
import csv

import cherrypy
import shutil

import splunk
import splunk.auth as auth
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.bundle as bundle
from splunk.models.saved_search import SavedSearch 
import splunk.util
import splunk.saved
import splunk.search

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import jsonresponse
import six

dir = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'bin')
if not dir in sys.path:
    sys.path.append(dir)

LEGACY_SETUP = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'default', 'setup.xml')

from unix.models.app import App
from unix.models.macro import Macro
from unix.models.unix_setup import UnixConfigured
from unix.models.unix import Unix 

logger = logging.getLogger('splunk')

## the macros to be displayed by the setup page
MACROS = [
          'os_index',
          'cpu_sourcetype',
          'df_sourcetype',
          'hardware_sourcetype',
          'interfaces_sourcetype',
          'iostat_sourcetype',
          'lastlog_sourcetype',
          'lsof_sourcetype',
          'memory_sourcetype',
          'netstat_sourcetype',
          'open_ports_sourcetype',
          'package_sourcetype',
          'protocol_sourcetype',
          'ps_sourcetype',
          'rlog_sourcetype',
          'syslog_sourcetype',
          'time_sourcetype',
          'top_sourcetype',
          'users_with_login_privs_sourcetype',
          'who_sourcetype'
         ]

'''Unix Setup Controller'''
class UnixSetup(controllers.BaseController):

    def parse_dynamic(self, tokenized_string):

        try:
            seq = tokenized_string.split(' OR ')
            # convert to set to deduplicate
            set_seq = set(seq)
            # convert back to list to sort
            tokenlist = list(set_seq)
            tokenlist.sort()
        except Exception as ex:
            tokenlist = []

        return tokenlist

    def render_json(self, response_data, set_mime="text/json"):
        cherrypy.response.headers["Content-Type"] = set_mime
        if isinstance(response_data, jsonresponse.JsonResponse):
            response = response_data.toJson().replace("</", "<\\/")
        else:
            response = json.dumps(response_data).replace("</", "<\\/")
        return " " * 256  + "\n" + response

    @route('/:app/:action=show')
    @expose_page(must_login=True, methods=['GET'])
    def show(self, app, action, **kwargs):
        
        form_content  = {}
        user = cherrypy.session['user']['name']

        for key in MACROS:
            try:
                form_content[key] = self.parse_dynamic(Macro.get(Macro.build_id(key, app, user)).definition)
            except:
                form_content[key] = self.parse_dynamic(Macro(app, user, key).definition)
    
        return self.render_json(form_content)

    @route('/:app/:action=save')
    @expose_page(must_login=True, methods=['POST'])
    def save(self, app, action, **params):
        ''' save the posted unix setup content '''

        error_key = None
        form_content = {}
        user = cherrypy.session['user']['name']
        host_app = cherrypy.request.path_info.split('/')[3]
        this_app = App.get(App.build_id(host_app, host_app, user))
        ftr = 0 if (this_app.is_configured) else 1
        redirect_params = dict(ftr=ftr)

        # pass 1: load all user-supplied values as models
        for key, value in six.iteritems(params):
            
            if key and key in MACROS:
                definition = (' OR ').join(value.split(","))
                try:
                    form_content[key] = Macro.get(Macro.build_id(key, app, user))
                    logger.info("Unixsave in try")
                except:
                    form_content[key] = Macro(app, user, key)
                    logger.info("Unixsave in except")
                form_content[key].definition = definition
                form_content[key].metadata.sharing = 'app'

        # pass 2: try to save(), and if we fail we return the user-supplied values
        for key in form_content.keys():

            try:
                if not form_content[key].passive_save():
                    logger.error('Error saving setup values')
                    cherrypy.response.status = 500

            except splunk.AuthorizationFailed:
                cherrypy.response.status = 403

            except Exception as ex:
                logger.exception(ex)
                logger.error('Failed to save eventtype %s' % key)
                cherrypy.response.status = 500
        
        this_app.is_configured = True
        # comment out this line to work around SPL-109444. Also, the removal of the call has no actual impact.
        # this_app.share_app()
        this_app.passive_save()

        # save build version to unix_setup.conf
        unixConfigured = UnixConfigured.get(UnixConfigured.build_id('install', host_app, 'nobody'))
        # Because UnixConfigured resource is 'configs/conf-unix_setup', no way to define required and optional fields there.
        # So call SplunkRESTManager._put_args directly, instead of unixConfigured.save(), to bypass required and optional fields check.
        newModel = UnixConfigured.manager()._put_args(UnixConfigured.build_id('install', host_app, 'nobody'), {'configured_version': this_app.version})
        logger.info('Save configured version from %s to %s successful' % (unixConfigured.configured_version, this_app.version))
        cherrypy.response.status = 200

    def insertDictItem(self, k, currentLevel):
        if k not in currentLevel:
            newLevel = {}
            currentLevel[k] = newLevel
        
        return currentLevel[k]

    def insertListItem(self, item, k, currentLevel):
        if k not in currentLevel:
            currentLevel[k] = []
        
        currentLevel[k].append(item)
        return currentLevel[k]

    def build_tree(self, raw, tree, order):
        for row in raw:
            # every row starts by inserting from the top-level of the tree
            currentLevel = tree
            for i, m in enumerate(order):
                item = row[m].strip()
                
                # Our leaves are represented by a list of hosts
                # these get appended to the hosts key of the last level
                if(i == len(order)-1):
                    self.insertListItem(item, 'hosts', currentLevel)
                else:
                    currentLevel = self.insertDictItem(item, currentLevel)

    def tree_to_csv(self, flat, node, csvOrder, hierarchy=[], slot=0):
        if(isinstance(node, six.string_types)):
            mappedSlot = csvOrder[slot]
            hierarchy[mappedSlot] = node

            # this makes a copy of hierarchy
            flat.append(list(hierarchy))

        elif(isinstance(node, dict)):
            if('hosts' in node and len(node) == 1):
                self.tree_to_csv(flat, node.get('hosts'), csvOrder, hierarchy, slot)
            else:
                for k, item in six.iteritems(node):
                    mappedSlot = csvOrder[slot]
                    hierarchy[mappedSlot] = k
                    self.tree_to_csv(flat, item, csvOrder, hierarchy, slot+1)
        else: 
            for item in node:
                self.tree_to_csv(flat, item, csvOrder, hierarchy, slot)

    def getOrder(self, keys, csvHeaders):
        order = []
        for key in keys:
            for i, header in enumerate(csvHeaders):
                if key == header.strip():
                    order.append(i)

        return order

    @route('/:app/:action=get_categories')
    @expose_page(must_login=True, methods=['GET'])
    def load_categories(self, app, action, **params):
        host_app = cherrypy.request.path_info.split('/')[3]

        csvData = []
        lookupCSV = os.path.join(util.get_apps_dir(), 'splunk_app_for_nix', 'lookups', 'dropdowns.csv')

        # Opening in different modes to handle incorrect parsing issue on windows
        if six.PY3:
            csvfile = open(lookupCSV, 'rt', newline='')
        else:
            csvfile = open(lookupCSV, 'rb')
        
        reader = csv.reader(csvfile)
        for row in reader:
            csvData.append(row)

        csvfile.close()

        csvHeaders = csvData[0] # this must contain all the column names
        keyOrder = ['unix_category', 'unix_group', 'host']
        order = self.getOrder(keyOrder, csvHeaders)
        csvData = csvData[1:len(csvData)]

        tree = {}
        self.build_tree(csvData, tree, order)

        return self.render_json(tree)

    @route('/:app/:action=get_hosts')
    @expose_page(must_login=True, methods=['GET'])
    def get_hosts(self, app, action, **params):
        saved_search = SavedSearch('', cherrypy.session['user']['name'], 'newsearch')
        job = splunk.search.dispatch('| metadata type=hosts `metadata_index`', namespace='splunk_app_for_nix')

        splunk.search.waitForJob(job)

        hostData = []
        for item in job.results:
            hostData.append(six.text_type(item['host']))

        return self.render_json(hostData)

    @route('/:app/:action=save_categories')
    @expose_page(must_login=True, methods=['POST'])
    def save_categories(self, app, action, **params):
        user = cherrypy.session['user']['name']
        host_app = cherrypy.request.path_info.split('/')[3]
        this_app = App.get(App.build_id(host_app, host_app, user))

        for param in params:
            data = json.loads(param)

        csvData = []
        csvOrder = [1,2,0]

        self.tree_to_csv(csvData, data, csvOrder, [0,0,0])
        csvHeader = ["host", "unix_category", "unix_group"]
        csvData.insert(0, csvHeader)

        dropdownsCsv = os.path.join(util.get_apps_dir(), 'splunk_app_for_nix', 'lookups', 'dropdowns.csv')

        # Opening in different modes to handle incorrect parsing issue on windows
        if six.PY3:
            csvfile = open(dropdownsCsv, 'wt', newline='')
        else:
            csvfile = open(dropdownsCsv, 'wb')

        writer = csv.writer(csvfile)
        writer.writerows(csvData)

        csvfile.close()

        session_key = cherrypy.session.get('sessionKey')
        success, errcode, reason = self._force_lookup_replication('splunk_app_for_nix', 'dropdowns.csv', session_key)
        logger.info('force lookup replication: %s, %s, %s' % (success, errcode, reason))

    @route('/:app_name/:action=check_setup')
    @expose_page(must_login=True, methods=['GET'])
    def check_setup(self, app_name, action, **kwargs):
        ''' 
        be careful to account for tricky conditions where some users can't 
        interact with our custom REST endpoint by falling back to bundle
        '''

        conf_name = 'unix'
        legacy_mode = False
        sessionKey = cherrypy.session.get('sessionKey') 
        user = cherrypy.session['user']['name']
        
        if os.path.exists(LEGACY_SETUP):
            shutil.move(LEGACY_SETUP, LEGACY_SETUP + '.bak')
            logger.info('disabled legacy setup.xml for %s' % app_name)

        # if the current app doesn't exist... 
        app = App.get(App.build_id(app_name, app_name, user))

        try:
            a = Unix.get(Unix.build_id(user, app_name, user))
        except:
            a = Unix(app_name, user, user)

        if kwargs.get('set_ignore'):
            try:
                a.has_ignored = True
                a.save()
            except:
                # assumption: 99% of exceptions here will be 403
                # we could version check, but this seems better
                to_set = {user: {'has_ignored': 1}}
                self.setConf(to_set, conf_name, namespace=app_name, 
                             sessionKey=sessionKey, owner=user)
                legacy_mode = True
            return self.render_json({'has_ignored': True, 
                                     'errors': ['legacy_mode=%s' % legacy_mode]})

        if a.id and a.has_ignored:
            return self.render_json({'has_ignored': True, 'errors': []})
        else:
            conf = self.getConf(conf_name, sessionKey=sessionKey, 
                                namespace=app_name, owner=user)
            if conf and conf[user] and util.normalizeBoolean(conf[user]['has_ignored']):
                return self.render_json({'has_ignored': True, 
                                         'errors': ['using legacy method']})
          
        if app.is_configured:
            return self.render_json({'is_configured': True, 'errors': []})
        else:
            if self.is_app_admin(app, user):
                return self.render_json({'is_configured': False, 'is_admin': True, 
                                         'errors': []})
            return self.render_json({'is_configured': False, 'is_admin': False, 
                                         'errors': []})

    def getConf(self, filename, sessionKey=None, namespace=None, owner=None):
        ''' wrapper to bundle.getConf, still necessary for compatibility'''

        try:
            return bundle.getConf(filename, 
                                  sessionKey=sessionKey, 
                                  namespace=namespace,
                                  owner=owner)
        except:
            return False

    def setConf(self, confDict, filename, namespace=None, sessionKey=None, owner=None ):
        ''' wrapper to bundle.getConf, still necessary for compatibility'''

        try:
            conf = bundle.getConf(filename, sessionKey=sessionKey, 
                                  namespace=namespace, owner=owner)
        except:
            conf = bundle.createConf(filename, sessionKey=sessionKey, 
                                     namespace=namespace, owner=owner)

        for item in confDict.keys():
            try:
                for k, v in six.iteritems(confDict[item]):
                    conf[item][k] = v 
            except AttributeError:
                pass 

    def is_app_admin(self, app, user):
        ''' 
        used to determine app administrator membership
        necessary because splunkd auth does not advertise inherited roles
        '''
        
        sub_roles = []
        admin_list = app.entity['eai:acl']['perms']['write'] 

        if '*' in admin_list:
            return True
        for role in auth.getUser(name=user)['roles']:
            if role in admin_list: 
                return True
            sub_roles.append(role)
        for role in sub_roles:
            for irole in auth.getRole(name=role)['imported_roles']:
                if irole in admin_list: 
                    return True
        return False

    def _force_lookup_replication(self, app, filename, sessionKey, base_uri=None):
        '''Force replication of a lookup table in a Search Head Cluster.'''

        # Permit override of base URI in order to target a remote server.
        endpoint = '/services/replication/configuration/lookup-update-notify'
        if base_uri:
            repl_uri = base_uri + endpoint
        else:
            repl_uri = endpoint

        payload = {'app': app, 'filename': os.path.basename(filename), 'user': 'nobody'}
        response, content = splunk.rest.simpleRequest(
            repl_uri,
            method='POST',
            postargs=payload,
            sessionKey=sessionKey,
            raiseAllErrors=False)

        content = content.decode('utf-8')

        if response.status == 400:
            if 'No local ConfRepo registered' in content:
                # search head clustering not enabled
                return (True, response.status, content)
            elif 'Could not find lookup_table_file' in content:
                return (False, response.status, content)
            else:
                # Previously unforeseen 400 error.
                return (False, response.status, content)
        elif response.status != 200:
            return (False, response.status, content)
        return (True, response.status, content)


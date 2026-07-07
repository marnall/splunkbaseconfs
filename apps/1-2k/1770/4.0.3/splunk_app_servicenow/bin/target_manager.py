__author__ = 'strong'

import splunk.entity as entity
import splunk.admin as admin
import util,time
import splunklib.client as client

logger = util.getLogger()

CONF_TARGET = 'addon_target'
CONF_WEB = 'configs/conf-web'

TARGET_PROPERTIES = ['port', 'scheme', 'username', 'password']

TARGET_APP = 'Splunk_TA_snow'
TARGET_OWNER = 'nobody'
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class TargetManager(object):
    def __init__(self, app=None, owner=None, session_key=None):
        self._app = app
        self._owner = 'nobody'  # so that conf file will be saved in app
        self._sessionKey = session_key
        splunkd_host_port = self._get_entity(CONF_WEB, 'settings').get('mgmtHostPort', '127.0.0.1:8089')
        host_and_port = splunkd_host_port.split(':')
        self.local_splunk_host = host_and_port[0]
        self.local_splunk_port = host_and_port[1]
        logger.info('app %s, owner %s, host %s, port %s' % (
            self._app, self._owner, self.local_splunk_host, self.local_splunk_port))
        self._service = client.Service(host=self.local_splunk_host, port=self.local_splunk_port, app=self._app,
                                       owner=self._owner, token=self._sessionKey)
        if "Splunk_TA_snow" not in self._service.apps:
            raise admin.InternalException("Splunk ServiceNow Add-on is not found on server")
        if CONF_TARGET not in self._service.confs:
            self._service.confs.create(CONF_TARGET)

    def add_target(self, host, target_props):
        target_props['host'] = host
        if not self._validate(target_props):
            raise Exception('%s not found on target host %s' % (TARGET_APP, host))
        username = target_props['username']
        password = target_props['password']
        # save credential first
        sp = self._new_credential(host=host, username=username, password=password)
        target_props['credential'] = sp.name
        target_props['create_time'] = time.strftime(TIME_FORMAT, time.localtime())
        # remove username/password as they're saved in storage/passwords
        for key in ['username', 'password']:
            del target_props[key]
        logger.info('new target props %s ' % target_props)
        if host in self._service.confs[CONF_TARGET]:
            new_target = self._service.confs[CONF_TARGET][host]
            new_target.update(**target_props)
        else:
            new_target = self._service.confs[CONF_TARGET].create(host, **target_props)
        return new_target

    def remove_target(self, host):
        if host in self._service.confs[CONF_TARGET]:
            target = self._service.confs[CONF_TARGET][host]
            # remove storagePassword first
            if target['credential'] in self._service.storage_passwords:
                p = self._service.storage_passwords[target['credential']]
                self._service.storage_passwords.delete(p.name)
            self._service.confs[CONF_TARGET].delete(host)

    def list_targets(self):
        ret = []
        targets = self._service.confs[CONF_TARGET]
        logger.info('list targets %s' % targets)
        for p in targets:
            ret.append((p.name, self._build_target_content(p.content)))
        local_props = self._get_local_props()
        self._validate(local_props)
        ret.append((self.local_splunk_host, local_props))
        return ret

    def get_target(self, target):
        props = None
        logger.info('getTarget %s' % target)
        logger.info('_local_splunkd_host %s' % self.local_splunk_host)
        if target == self.local_splunk_host:
            return self._get_local_props()
        if target in self._service.confs[CONF_TARGET]:
            t = self._service.confs[CONF_TARGET][target]
            props = self._build_target_content(t.content)
            # populate host field
            props['host'] = target
        return props

    def _build_target_content(self, content):
        props = content.copy()
        # unless someone manually remove it, otherwise credential field will always there
        if 'credential' in props and props['credential'] in self._service.storage_passwords:
            p = self._service.storage_passwords[props['credential']]
            logger.info('credentialProps %s ' % p)
            props['username'] = p['username']
            props['password'] = p['clear_password']
            del props['credential']
        logger.info('props %s' % props)
        return props

    def _get_entity(self, path, name):
        return entity.getEntity(path, name, sessionKey=self._sessionKey, namespace=self._app, owner=self._owner)

    def _new_credential(self, host=None, username=None, password=None):
        # we use realm to test whether the credential exist
        realm = "%s:%s" % (host, username)
        sps = self._service.storage_passwords.list(search='realm=%s' % realm)
        if len(sps) > 0:
            sp = sps[0]
            sp.update(password=password)
        else:
            sp = self._service.storage_passwords.create(password, username, realm=realm)
        return sp

    def _get_local_props(self):
        return dict(host=self.local_splunk_host, port=self.local_splunk_port, owner=self._owner, token=self._sessionKey,
                    scheme='https')

    def _validate(self, props):
        c = client.Service(**props)
        # check whether it installed aws add-on
        if props['host'] is not self.local_splunk_host:
            c.login()
        if TARGET_APP not in c.apps:
            return False
        return True
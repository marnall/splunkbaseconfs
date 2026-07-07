from fortiosclient import client
from fortiosclient import exception

class FortiGateActions():

    def __init__(self, logger, api, user, password):
        self.api = client.FortiosApiClient(api, user, password)
        self.logger = logger

    def _get_first_policy(self, vd):
        message = {"vdom": vd}
        first_policy = self.api.request("GET_FIREWALL_POLICY", **message)
        return first_policy['results'][0]['policyid']

    def _move_policy(self, vd, newid, oldid):
        message = {
            "vdom": vd,
            "before": oldid,
            "id": newid
        }
        self.api.request("MOVE_FIREWALL_POLICY", **message)

    def _add_fw_addr(self, vd, ip, intf):
        addr_name = "fgt_ar_" + ip
        message = {
            "vdom": vd,
            "subnet": ip + "/32",
            "associated-interface": intf,
            "name": addr_name
        }
        try:
            fw_addr = self.api.request("GET_FIREWALL_ADDRESS", name=addr_name,
                                       vdom=vd)
        except Exception:
            fw_addr = None
        if fw_addr and fw_addr.get('http_status', 200):
            self.logger.info('firewall address already exists')
        else:
            try:
                fw_addr = self.api.request("ADD_FIREWALL_ADDRESS", **message)
                self.logger.info(
                    'added firewall address, response is {0}'.format(fw_addr))
            except exception.Failed_dependency:
                pass
        return fw_addr

    def _add_fw_policy(self, vd, ip, intf, users=None, block_type='src'):
        if block_type == 'src':
            addr_key = 'srcaddr'
            intf_key = 'srcintf'
        else:
            addr_key = 'dstaddr'
            intf_key = 'dstintf'
        message = {
            "name": 'blk_' + block_type + '_' + ip,
            "vdom": vd,
            addr_key: 'fgt_ar_' + ip,
            intf_key: intf,
            "comments": 'fgt_ar',
            "action": 'deny'
        }
        if users:
            message['users'] = users
        self.logger.debug('firewall policy message is %s' % message)
        fw_policy = self.api.request("ADD_FIREWALL_POLICY", **message)
        self.logger.info('added firewall policy, the response is {0}'.format(
            fw_policy))
        return fw_policy

    def block_src(self, vd, src_ip, src_intf, user=None):
        fw_addr = self._add_fw_addr(vd, src_ip,src_intf)
        if not fw_addr:
            raise Exception('Creating fw addr failed for {0}'.format(src_ip))
        u_list = []
        if user:
            u_list.append(user)
        fw_policy = self._add_fw_policy(vd, src_ip, src_intf, u_list)
        newid = (fw_policy.get('results', {}).get('mkey', None) or
                  fw_policy.get('mkey', None))
        if newid:
            firstid = self._get_first_policy(vd)
            self._move_policy(vd, newid, firstid)
        return fw_policy.get('status', 'Failed')

    def block_dst_ip(self, vd, dst_ip, dst_intf, user=None):
        fw_addr = self._add_fw_addr(vd, dst_ip, dst_intf)
        if not fw_addr:
            raise Exception('Creating fw addr failed for {0}'.format(dst_ip))
        fw_policy = self._add_fw_policy(vd, dst_ip, dst_intf, block_type='dst')
        newid = (fw_policy.get('results', {}).get('mkey', None) or
                  fw_policy.get('mkey', None))
        if newid:
            firstid = self._get_first_policy(vd)
            self._move_policy(vd, newid, firstid)
        return fw_policy.get('status', 'Failed')

    def block_user(self, vd, ugroup, usr):
        message = {
            "vdom": vd,
            "name": ugroup
        }
        try:
            result = self.api.request("GET_USER_GROUP", **message)
            self.logger.info('Getting user group info %s', result)
        except exception.ResourceNotFound:
            self.logger.info('Can not get specified user group')
            raise
        members = result["results"][0]["member"]
        for m in members:
            if m["name"] == usr:
                members.remove(m)
        m_list = []
        for m in members:
            m_list.append(m["name"])
        message = {
            "vdom": vd,
            "name": ugroup,
            "member": m_list
        }
        try:
            self.logger.info('Setting user group members %s', m_list)
            self.api.request("SET_USER_GROUP", **message)
        except Exception as e:
            self.logger.info('Failed to delete user {0} from group {1}'.format(
                usr, ugroup))
            raise e

    def logout(self):
        return self.api.request("LOGOUT")

###############################################################################
#
# Copyright (C) 2013-2014 Cisco and/or its affiliates. All rights reserved.
#
# THE PRODUCT AND DOCUMENTATION ARE PROVIDED AS IS WITHOUT WARRANTY OF ANY
# KIND, AND CISCO DISCLAIMS ALL WARRANTIES AND REPRESENTATIONS, EXPRESS OR
# IMPLIED, WITH RESPECT TO THE PRODUCT, DOCUMENTATION AND RELATED MATERIALS
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE; WARRANTIES ARISING FROM A COURSE OF
# DEALING, USAGE OR TRADE PRACTICE; AND WARRANTIES CONCERNING THE
# NON-INFRINGEMENT OF THIRD PARTY RIGHTS.
#
# IN NO EVENT SHALL CISCO BE LIABLE FOR ANY DAMAGES RESULTING FROM LOSS OF
# DATA, LOST PROFITS, LOSS OF USE OF EQUIPMENT OR LOST CONTRACTS OR FOR ANY
# SPECIAL, INDIRECT, INCIDENTAL, PUNITIVE, EXEMPLARY OR CONSEQUENTIAL
# DAMAGES IN ANY WAY ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THE PRODUCT OR DOCUMENTATION OR RELATING TO THIS
# AGREEMENT, HOWEVER CAUSED, EVEN IF IT HAS BEEN MADE AWARE OF THE
# POSSIBILITY OF SUCH DAMAGES.  CISCO'S ENTIRE LIABILITY TO LICENSEE,
# REGARDLESS OF THE FORM OF ANY CLAIM OR ACTION OR THEORY OF LIABILITY
# (INCLUDING CONTRACT, TORT, OR WARRANTY), SHALL BE LIMITED TO THE LICENSE
# FEES PAID BY LICENSEE TO USE THE PRODUCT.
#
###############################################################################
#
#  Change Log
#
#   1.0   - cogrady - ORIGINAL RELEASE WITH INTRODUCTION OF SPLUNK APP
#   1.0.5 - cogrady - Add support for the debug option
#   2.0   - cogrady - Always set changed flag when saving config, add flow
#                       setting
#   2.2.0 - cogrady - Add support for the extra data option
#
###############################################################################


###############################################################################
# Import modules
###############################################################################

import splunk.admin as admin
import splunk.entity as en


###############################################################################
# Class - eStreamerConfig
###############################################################################

class eStreamerConfig(admin.MConfigHandler):

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['server', 'ipv6', 'port', 'pkcs12_file', 'pkcs12_password', 'log_extra_data', 'log_packets', 'log_flows', 'log_metadata', 'watch', 'debug', 'client_disabled', 'changed']:
        self.supportedArgs.addOptArg(arg)
  
  def handleList(self, confInfo):
    confDict = self.readConf('estreamer')
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          confInfo[stanza].append(key, val)
        confInfo[stanza].append('changed', '1')
  
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    
    if self.callerArgs.data['server'][0] in [None, '']:
      self.callerArgs.data['server'][0] = ''
    
    if self.callerArgs.data['ipv6'][0] in [None, '']:
      self.callerArgs.data['ipv6'][0] = '0'
    
    if self.callerArgs.data['port'][0] in [None, '']:
      self.callerArgs.data['port'][0] = '8302'
    
    if self.callerArgs.data['pkcs12_file'][0] in [None, '']:
      self.callerArgs.data['pkcs12_file'][0] = ''
    
    if self.callerArgs.data['pkcs12_password'][0] in [None, '']:
      self.callerArgs.data['pkcs12_password'][0] = ''
    
    if self.callerArgs.data['log_extra_data'][0] in [None, '']:
      self.callerArgs.data['log_extra_data'][0] = '0'
    
    if self.callerArgs.data['log_packets'][0] in [None, '']:
      self.callerArgs.data['log_packets'][0] = '0'
    
    if self.callerArgs.data['log_flows'][0] in [None, '']:
      self.callerArgs.data['log_flows'][0] = '0'
    
    if self.callerArgs.data['log_metadata'][0] in [None, '']:
      self.callerArgs.data['log_metadata'][0] = '0'
    
    if self.callerArgs.data['watch'][0] in [None, '']:
      self.callerArgs.data['watch'][0] = '0'
    
    if self.callerArgs.data['debug'][0] in [None, '']:
      self.callerArgs.data['debug'][0] = '0'
    
    if self.callerArgs.data['client_disabled'][0] in [None, '']:
      self.callerArgs.data['client_disabled'][0] = '1'

    self.callerArgs.data['changed'][0] = '1'
    
    self.writeConf('estreamer', 'estreamer', self.callerArgs.data)

# initialize the handler
admin.init(eStreamerConfig, admin.CONTEXT_NONE)

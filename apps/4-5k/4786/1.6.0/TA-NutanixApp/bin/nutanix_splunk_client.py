"""
Splunk Modular input handler

Copyright (c) 2019 Nutanix Inc. All rights reserved.

Author: ganesh.girase@nutanix.com
"""

from splunklib.modularinput import *

class NutanixSplunkClient(Script):
  """
  Class to handle splunk modular input scripts
  """
  # Define class level variables
  MASK  = "************"
  def encrypt_password(self, service, username, password, realm, logger): 
    """
    Encrypt password for current session.
    Args:
      service: Splunk Service object.
      username: Nutanix cluster username.
      password: Nutanix cluster password.
      realm: Password lock key
      logger: Event writer object
    Returns:
      None
    """
    try:
      # If the credential already exists, delte it.
      for record in service.storage_passwords:
        if record.username == username and record.realm == realm:
          service.storage_passwords.delete(username, realm)
          break
      # Create the credential.
      service.storage_passwords.create(password, username, realm)
      logger.log('INFO', "Password encrypted for %s/%s" %(username, realm))
    except Exception as e:
      raise Exception, "Error occurred while encrypting password: %s" %str(e)

  def mask_password(self, service, username, input_module, logger):
    """
    Mask password for current session.
    Args:
      service: Splunk Service object.
      username: Nutanix cluster username.
      input_module: Input module entry from conf file.
      logger: Event writer object
    Returns:
      None
    """
    try:
      kind, input_name = input_module.split("://")
      logger.log('INFO', "Mask pass: [%s], [%s]" %(username, input_module))
      item = service.inputs.__getitem__((input_name, kind))
      logger.log('INFO',"Masking password for %s/%s" %(kind, input_name))
      kwargs = { "username": username, "password": self.MASK }
      item.update(**kwargs).refresh()
    except Exception as e:
      raise Exception("Error while masking password: %s" % str(e))

  def get_password(self, service, username, realm, ew):
    """
    Retrieve the password from
    the current session storage/passwords endpoint.
    Args:
      service: Splunk Service object.
      username: Nutanix cluster username.
      realm: Password unlock key
      logger: Event writer object
    Returns:
      None
    """
    try:
      ew.log("INFO", "Searching password for %s/%s" %(username, realm))
      for record in service.storage_passwords:
        if record.username == username and record.realm == realm:
          return record.content.clear_password
      else:
        raise Exception("Cannot find password for %s/%s" %(username, realm))
    except Exception as e:
      raise Exception("Error while retrieving password: %s" % str(e))

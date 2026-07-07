"""
Splunk Modular input handler

Copyright (c) 2019 Nutanix Inc. All rights reserved.

Author: ganesh.girase@nutanix.com
"""
import ta_nutanix_declare
from splunklib.modularinput import *

class NutanixSplunkClient(Script):
  """
  Class to handle splunk modular input scripts
  """
  # Define class level variables
  MASK  = "************"
  def save_password(self, service, username, password, realm, logger): 
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
      logger.info("Password encrypted for {}/{}".format(username, realm))
    except Exception as e:
      logger.error("Error occurred while encrypting password: {}".format(str(e)))

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
      logger.info("Mask pass: [{}], [{}]" .format(username, input_module))
      item = service.inputs.__getitem__((input_name, kind))
      logger.info("Masking password for {}/{}" .format(kind, input_name))
      kwargs = { "username": username, "password": self.MASK }
      item.update(**kwargs).refresh()
    except Exception as e:
      logger.error("Error while masking password: {}".format(str(e)))

  def get_password(self, service, username, realm, logger):
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
      logger.info("Searching password for {}/{}".format(username, realm))
      for record in service.storage_passwords:
        if record.username == username and record.realm == realm:
          return record.content.clear_password
      else:
        logger.error("Cannot find password for {}/{}".format(username, realm))
    except Exception as e:
      logger.error("Error while retrieving password: {}".format(str(e)))

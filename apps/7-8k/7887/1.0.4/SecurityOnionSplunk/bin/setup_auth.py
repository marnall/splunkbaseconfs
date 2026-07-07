#!/usr/bin/env python3

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import os
import subprocess
import sys
import configparser
from pathlib import Path

def decrypt_credential(x):
  splunk_home = os.environ.get('SPLUNK_HOME')
  if not splunk_home:
    raise EnvironmentError("SPLUNK_HOME environment variable is not set")
  splunk_bin = Path(splunk_home) / "bin" / "splunk"

  try:
    result = subprocess.run(
      [str(splunk_bin), "show-decrypted", "--value", x],
      capture_output=True,
      text=True,
      check=True
    )
    secret_decrypted = result.stdout.strip()
  except subprocess.CalledProcessError as e:
    raise RuntimeError(f"Failed to decrypt secret")
  return secret_decrypted

def get_credentials():
  splunk_home = os.environ.get('SPLUNK_HOME')
  if not splunk_home:
      raise EnvironmentError("SPLUNK_HOME environment variable is not set")
  passwords_conf_path = Path(splunk_home) / "etc" / "apps" / "SecurityOnionSplunk" / "local" / "passwords.conf"
  if not passwords_conf_path.exists():
      raise FileNotFoundError(f"passwords.conf not found at: {passwords_conf_path}")
  config = configparser.ConfigParser()
  config.read(passwords_conf_path)
  try:
      client_id_encrypted = config['credential:SecurityOnionSplunk_realm:client_id:']['password']
      client_secret_encrypted = config['credential:SecurityOnionSplunk_realm:client_secret:']['password']
      urlbase_encrypted = config['credential:SecurityOnionSplunk_realm:urlbase:']['password']
  except KeyError as e:
      raise RuntimeError(f"Required credential section not found in passwords.conf: {e}")

  client_id_decrypted = decrypt_credential(client_id_encrypted)
  client_secret_decrypted = decrypt_credential(client_secret_encrypted)
  urlbase_decrypted = decrypt_credential(urlbase_encrypted)
  return {
      'client_id': client_id_decrypted,
      'client_secret': client_secret_decrypted,
      'urlbase': urlbase_decrypted
  }
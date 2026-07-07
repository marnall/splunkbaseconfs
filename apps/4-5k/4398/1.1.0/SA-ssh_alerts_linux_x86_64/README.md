# Splunk Add-on for SSH Alert Actions Linux 64bit

Version: 1.1.0

## Introduction

This add-on allows Splunk to act as a wrapper for the Python library paramiko, 
which adds alert actions like remote ssh commands and SFTP transfer

## Installation

Normal app installation can be followed from https://docs.splunk.com/Documentation/AddOns/released/Overview/AboutSplunkadd-ons. Essentially download app and install from Web UI or extract file in $SPLUNK\_HOME/etc/apps folder.

## Usage

To add a SSH action to an alert, go to the `Alerts` tab in the `Search` app and find applicable alert. Click `Edit`, and select `Edit Actions`. Click `+ Add Actions` and select either of the SSH actions available. Fill out the attributes for the connection and action. Note that username and passwords get stored in cleartext in savedsearches.conf so it is recommended to used authorized keys instead. The add-on has the option to save this for you automatically by turning on "Auto Add Host to KnownHosts" or by manually from the search head editing the ~/.ssh/known_hosts (make a connection first and the OS will offer to save it as well).

When using SSH Command alert action, it is recommended to use sudo and read the documentation for sudo at https://www.sudo.ws/man/1.8.27/sudoers.man.html. An example command placed either in /etc/sudoers or in a new file like so /etc/sudoers.d/10_splunk may look like this:

>splunk ALL=(root) NOPASSWD: /bin/systemctl restart ntpd

Then the ssh command to call it in the Splunk alert would be:

>sudo systemctl restart ntpd

# Included External Library Declaration

# Binary File Declaration

_cffi_backend.so
_padding.so
_openssl.so
_bcrypt.so
_sodium.so
_padding.abi3.so
_openssl.abi3.so
_rust.abi3.so
_bcrypt.abi3.so
_cffi_backend.cpython-37m-x86_64-linux-gnu.so
_sodium.abi3.so



## Release Notes

Updated for Python 3 compatability. Fixed so that sftp_alert will not include columns starting with `__mv_`

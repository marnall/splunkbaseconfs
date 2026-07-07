#!/bin/sh
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
#   2.1.1 - cogrady - ORIGINAL RELEASE
#
###############################################################################

# Functions
getAnswer ()
{
  local query="$1"
  local default="$2"
  echo -n "$1 [$2] "
  read reply
  if [ "x$reply" = "x" ]; then
    reply=$default
  fi
  echo
}

# Main

# Get the Splunk base path if no $SPLUNK_HOME exists
if [ "x$SPLUNK_HOME" = "x" ]; then
  echo "What is the Splunk base path? [/opt/splunk] "
  read path
  if [ "x$path" = "x" ]; then
    SPLUNK_HOME=/opt/splunk
  else
    SPLUNK_HOME=path
  fi
fi

# Validate the path
if [ ! -d $SPLUNK_HOME ]; then
  echo "Splunk directory ($SPLUNK_HOME) does not appear to exist"
  exit 1
fi
if [ ! -x $SPLUNK_HOME/bin/splunk ]; then
  echo "Splunk directory ($SPLUNK_HOME) does not appear to be the Splunk base path"
  exit 1
fi

# Validate the app is installed
if [ ! -d $SPLUNK_HOME/etc/apps/eStreamer/ ]; then
  echo "eStreamer for Splunk does not appear to be installed"
  exit 1
else
  APP_PATH=$SPLUNK_HOME/etc/apps/eStreamer
fi

# Set some vars based on above paths
APP_CONFIG=$APP_PATH/local/app.conf
DEFAULT_CONFIG=$APP_PATH/default/estreamer.conf
LOCAL_CONFIG=$APP_PATH/local/estreamer.conf

# Read the configs
OLD_IFS=$IFS
IFS=" = "
while read -r name value; do
  if [ ! "x$value" = "x" ]; then
    eval $name=$value
  fi
done < $DEFAULT_CONFIG
while read -r name value; do
  if [ ! "x$value" = "x" ]; then
    eval $name=$value
  fi
done < $LOCAL_CONFIG
IFS=$OLD_IFS

# Stat asking about the details

echo
getAnswer "Defense Center Hostname or IP Address" $server
server=$reply

getAnswer "Defense Center eStreamer Port" $port
port=$reply

getAnswer "Use IPv6 for eStreamer communication (0 = no, 1 = yes)" $ipv6
ipv6=$reply

old_file=$pkcs12_file
getAnswer "PKCS12 certificate filename and path" $pkcs12_file
pkcs12_file=$reply
while [ ! -f $pkcs12_file ]; do
  echo "ERROR: Unable to locate certificate at that location"
  echo
  getAnswer "PKCS12 certificate filename and path" $old_file
  pkcs12_file=$reply
done

getAnswer "PKCS12 certificate password"
pkcs12_password=$reply

getAnswer "Log packet data (0 = no, 1 = yes)" $log_packets
log_packets=$reply

getAnswer "Log flows (0 = no, 1 = yes)" $log_flows
log_flows=$reply

getAnswer "Log metadata (0 = no, 1 = yes)" $log_metadata
log_metadata=$reply

getAnswer "eStreamer client lives and dies with Splunk (0 = no, 1 = yes)" $watch
watch=$reply

getAnswer "Enable debug logging in eStreamer client (0 = no, 1 = yes)" $debug
debug=$reply

getAnswer "Disable the eStreamer client (0 = no, 1 = yes)" $client_disabled
client_disabled=$reply

echo
echo " Client Disabled:   $client_disabled"
echo
echo " Defense Center Config"
echo "  Server:           $server"
echo "  Port:             $port"
echo "  Use IPv6:         $ipv6"
echo "  PKCS12 File:      $pkcs12_file"
echo "  PKCS12 Password:  $pkcs12_password"
echo
echo " Logging Config"
echo "  Log Packets:      $log_packets"
echo "  Log Flows:        $log_flows"
echo "  Log Metadata:     $log_metadata"
echo
echo " Additional Config"
echo "  Run w/ Splunk:    $watch"
echo "  Debugging:        $debug"
echo

getAnswer "Do you want to save this config?" "Y"
if [ "x$reply" = "xY" ]; then
  echo "[estreamer]" > $LOCAL_CONFIG
  echo "client_disabled = $client_disabled" >> $LOCAL_CONFIG
  echo "server = $server" >> $LOCAL_CONFIG
  echo "port = $port" >> $LOCAL_CONFIG
  echo "ipv6 = $ipv6" >> $LOCAL_CONFIG
  echo "pkcs12_file = $pkcs12_file" >> $LOCAL_CONFIG
  echo "pkcs12_password = $pkcs12_password" >> $LOCAL_CONFIG
  echo "log_packets = $log_packets" >> $LOCAL_CONFIG
  echo "log_flows = $log_flows" >> $LOCAL_CONFIG
  echo "log_metadata = $log_metadata" >> $LOCAL_CONFIG
  echo "watch = $watch" >> $LOCAL_CONFIG
  echo "debug = $debug" >> $LOCAL_CONFIG
  echo "changed = 1" >> $LOCAL_CONFIG

  # Mark the app as configured
  echo "[install]" > $APP_CONFIG
  echo "is_configured = 1" >> $APP_CONFIG

  echo "Configuration saved."
else
  echo "Configuration NOT saved."
fi
echo

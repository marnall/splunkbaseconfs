#!/bin/sh
#
#Sun Oct  8 11:15:17 UTC 2017 @BobbyM & @Bruce - updated btool to cater for frequent configuration changes and also to run as a different user.
#
# Requirements:
# - Run btool if associated .conf files change.
# - Run btool at least once every 24 hours even if the configuration hasn't changed.
# - Maintain backward compatibility with the original 'btool.sh' script to avoid breaking existing searches and dashboards.
 
new_cksum_total=0
old_cksum_total=0
config=${1}
splunk_basedir=${2}
splunk_user=${3}
 
# Show usage options
usage() {
  echo "Usage: $0 <conf> <splunk_home> [<splunk_user>]"
  echo "Example: $0 props /opt/splunk splunk"
  exit 1
}
 
# Display usage if no arguments are specified.
if [ -z "${1}" ] ; then
  usage
fi

#Check if specified Splunk Basedir exists. If it does not, exit quietly
if [ ! -d "${splunk_basedir}" ] ; then
  exit
fi

#If a third argument has been supplied telling us to urun btool as a different user, run commands as this specified user using su. Otherwise, just run commands as you usually would with the current user
if [ ! -z "${splunk_user}" ] ; then
  #A user has been specified. Wrap key commands with su.
  btool_cmd (){
  /bin/su - ${splunk_user} -c "${splunk_basedir}/bin/splunk cmd btool ${config} list --debug"
  }
  btool_app_cmd (){
  /bin/su - ${splunk_user} -c "${splunk_basedir}/bin/splunk cmd btool app list --app=$1 --debug"
  }
  create_btool_dir (){
  /bin/su - ${splunk_user} -c "mkdir -p ${splunk_basedir}/var/run/splunk/btool"
  }
  write_cksum (){
  /bin/su - ${splunk_user} -c "echo ${1} > ${splunk_basedir}/var/run/splunk/btool/${config}.checksum"
  }
else
  #A user has NOT been specified. Just run commands as the user currently running this script.
  btool_cmd (){
  ${splunk_basedir}/bin/splunk cmd btool ${config} list --debug
  }
  btool_app_cmd (){
  ${splunk_basedir}/bin/splunk cmd btool app list --app=$1 --debug
  }
  create_btool_dir (){
  mkdir -p ${splunk_basedir}/var/run/splunk/btool
  }
  write_cksum (){
  echo ${1} > ${splunk_basedir}/var/run/splunk/btool/${config}.checksum
  }
fi

# Calculate checksum value for specified config file
for cksum_conf in `/usr/bin/find "${splunk_basedir}/etc" -name "${config}.conf" -type f -exec cksum {} \;|awk '{print $1}'` ; do
  new_cksum_total=$((new_cksum_total + cksum_conf))
done
 
  # Create the checksum directory if it does not exist and subsequently save the checksum value there.
if [ ! -d "${splunk_basedir}/var/run/splunk/btool" ] ; then
  create_btool_dir
  write_cksum ${new_cksum_total}
else
  # Collect the old checksum for comparison to the new checksum but only if it exists or if it's less than 24 hours old.
  if [ -f ${splunk_basedir}/var/run/splunk/btool/${config}.checksum ] ; then
    old_cksum_total="`/usr/bin/find ${splunk_basedir}/var/run/splunk/btool/ -name "${config}.checksum" -mtime -1 -exec cat {} \;`"
  fi
fi
 
# Run btool if the checksums differ. They will differ if .conf files change and/or if it's the first time the script is run.
if [ "${new_cksum_total}" != "${old_cksum_total}" ] ; then
  if [ "${config}" != "app" ]; then
    btool_cmd
    write_cksum ${new_cksum_total}
  else
    if [ -d ${splunk_basedir}/etc/apps ]; then
      find ${splunk_basedir}/etc/apps/ -name "app.conf" | awk -F'/' '{print $6}' | sort | uniq | while read APP
      do
        btool_app_cmd $APP
      done
    fi

    if [ -d ${splunk_basedir}/etc/slave-apps ]; then
      find ${splunk_basedir}/etc/slave-apps/ -name "app.conf" | awk -F'/' '{print $6}' | sort | uniq | while read APP
      do
        btool_app_cmd $APP
      done
    fi

    if [ -d ${splunk_basedir}/etc/deployment-apps ]; then
      find ${splunk_basedir}/etc/deployment-apps/ -name "app.conf" | awk -F'/' '{print $6}' | sort | uniq | while read APP
      do
        btool_app_cmd $APP
      done
    fi

    write_cksum ${new_cksum_total}
  fi 
fi


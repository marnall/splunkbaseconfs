#/bin/bash
# Called once a week by default to delete the log file
# Go setup logrotate then come back and delete this

rm /var/log/facter.log

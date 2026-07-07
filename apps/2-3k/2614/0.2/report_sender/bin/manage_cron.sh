#/bin/bash


cd `dirname $0`
echo `whoami` >> cron.log
echo "$1" "$2" >> cron.log

case $1 in
    remove)
        echo removing >> cron.log
        crontab -l | sed "s/.* # $2$//" | crontab - 2&1>> cron.log;;
    add)
        echo adding >> cron.log
        cmd=${2//%/\\%}
        echo cmd >> cron.log
        echo "$cmd" >> cron.log
        (crontab -l; echo "$cmd") | crontab - 2&1>> cron.log;;
esac

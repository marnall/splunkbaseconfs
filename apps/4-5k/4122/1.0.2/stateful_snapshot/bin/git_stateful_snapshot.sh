#i/bin/bash
#########################
# Name: git_stateful_snapshot.sh
# Project Title: Stateful Snapshot App for Splunk
# By: Benya Chongolnee and Burch Simon
# Date: July 2018
# Purpose: This Splunk application can be used to backup certail folders and files on the Splunk environment using local GIT
#########################

#initializing
git_path=$SPLUNK_HOME/etc  #adjust this accordingly

if [ -d "${git_path}/.git" ];
    then
        #Create a function that will create new events within the Splunk UI
        newEvent (){
            echo `date`
            echo "log_level = $1"
            echo "status = $2"
            echo "username = $3"
            echo "commit_message = $4"
            echo "component = GIT"
        }

        #########################
        # Git (start)
        #########################
        cd ${git_path}
        name=`git config user.name`
        newEvent INFO start ${name} "Automatic GIT commit by git_stateful_snapshot.sh (Stateful Snapshot App for Splunk)"


        #########################
        # Git add / Git commit
        #########################
        newEvent INFO addcommit ${name} "Automatic GIT commit by git_stateful_snapshot.sh (Stateful Snapshot App for Splunk)"
        git add -u .
        git add .
        git_commit_output=`git commit -m "Automatic GIT commit by git_stateful_snapshot.sh (Stateful Snapshot App for Splunk)"`
        echo "commit_output=\"${git_commit_output}\""

        #########################
        # Ending
        #########################
        newEvent INFO end $name "Automatic GIT commit by git_stateful_snapshot.sh (Stateful Snapshot App for Splunk)"
fi

if [ ! -d "${git_path}/.git" ];
    then
        newEvent ERROR - - -
        echo "local git has not yet been created in ${git_path}"
fi

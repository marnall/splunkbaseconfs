#i/bin/bash
#########################
# Name: stateful_snapshot.sh
# Project Title: Stateful Snapshot App for Splunk
# By: Benya Chongolnee & Burch Simon
# Date: July 2018
# Purpose: This Splunk application can be used to backup certain folders and files on the Splunk environment
#########################
#Initializing Variables
time=`date '+%Y_%m_%d__%H_%M_%S'`
collect_folders="etc,kvstore" #adjust this accordingly (http://docs.splunk.com/Documentation/Splunk/7.1.2/Troubleshooting/Generateadiag)
maxsize=1000000000 #default is at 1GB, change this number accordingly
maxage=365 #default is at 1 year, change this number accordingly
backupDir=${HOME} #default backup directory is the home directory

#Create a function that will create new events within the Splunk UI
newEvent (){
    echo   `date`
    echo "log_level = INFO"
    echo "status = $1"
    echo "message = $2"
    echo "file_name = $3"
    echo "component = DIAG"
}

#########################
# GENERATE A DIAGNOSTIC FILE
#########################
#start the diag command
OUTPUT="$(${SPLUNK_HOME}/bin/splunk diag --collect=${collect_folders})"
PATHNAME=`echo ${OUTPUT} | perl -n -e'/created:\s(.+)/ && print $1' | awk '{n=split($0,a,"/"); print a[n]}'`
newEvent start - ${backupDir}/${PATHNAME}

#end the diag command
newEvent end - ${backupDir}/${PATHNAME}
echo "diag_output=\"${OUTPUT}\""
ORIGINAL=`echo ${OUTPUT} | perl -n -e'/created:\s(.+)/ && print $1'`
mv ${ORIGINAL} ${backupDir}

echo "Splunk diagnosis file from ${SPLUNK_HOME}/${PATHNAME} has been moved to ${backupDir}/${PATHNAME}"

#########################
# DELETE FILES
#########################
## delete oldest diag file after ${maxsize}
while [ `du -c ${backupDir}/diag-* | cut -f1 | tail -1` -gt ${maxsize} ];
do OLDESTFILE=`ls -dr ${backupDir}/diag-* | tail -n1`;
        rm -f -r ${OLDESTFILE};
        newEvent remove splunk_exceeds_storage_size ${backupDir}/${PATHNAME}
echo "Removed ${OLDESTFILE} because the folder exceeds ${maxsize}";
done;

##delete diag files past ${maxage} days
while [ `find ${backupDir}/diag-* -mtime +${maxage} | wc -l` -gt 0 ]
do OLDESTFILE=`find ${backupDir}/diag-* -mtime +${maxage} | head -1`;
    rm -f -r ${OLDESTFILE};
    newEvent remove splunk_exceeds_age ${backupDir}/${PATHNAME}
echo "Removed ${OLDESTFILE} because the file is older than ${maxage} days"
done;

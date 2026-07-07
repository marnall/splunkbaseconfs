[remove_files_directories://<name>]
working_directory = This will be the directory, where the script will run from and where the objects will be removed from. Use absolute path, e.g. "/data/directory/".
pattern = Use RegEx to describe the pattern of files/directories to remove from the working directory.
retention_policy = Turn this on if you'd like to remove files/directories based on their age.
retention_period = Provide the age of files/directories to be deleted in seconds, e.g. "86400" for 24 hours. Also, make sure you have enabled the "Retention Policy" option first.
timestamp_location = "Last Modified" will get timestamp from the "last modified" attribute in the filesystem. Use "Bucket" only with Splunk frozen buckets.
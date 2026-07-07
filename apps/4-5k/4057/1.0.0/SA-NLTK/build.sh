find . -name "*.pyc" -type f -delete
cd bin
mv nltk_data /tmp
mkdir nltk_data
/opt/splunk/bin/splunk package app SA-NLTK
rmdir nltk_data
cd /tmp
mv nltk_data /opt/splunk/etc/apps/SA-NLTK/bin

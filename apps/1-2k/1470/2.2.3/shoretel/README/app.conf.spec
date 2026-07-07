
#This is part of a convention we use,  where a checklist.conf stanza can 
# check,  whether 
# a) the current Splunk version matches the required Splunk version we ship 
# in the dependency:splunk key in app.conf
# b) whether the current Sideview Utils versions matches the required version
# we specify in the dependency;app:sideview_utils key in app.conf

[dependency:splunk]
requiredVersion = <version string>

[dependency:app:<appname>]
requiredVersion = <version string>

# this was part of an experiment to have the app_setup (ftr+migration) script 
# know when the version or build or type had changed since the last restart.
#[install]
#lastVersionInfo = <version build and type string>


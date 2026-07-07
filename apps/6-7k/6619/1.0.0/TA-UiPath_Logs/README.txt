# UiPath nlog configuration: change the layout so that we receive a clean json payload:
 * <target type="File" name="WorkflowLogFiles" fileName="${WorkflowLoggingDirectory}/${shortdate}_Execution.log" layout="${message}" keepFileOpen="true" openFileCacheTimeout="5"

# Splunk Inputs:
 * On your Universal Forwarder or Deployment Server create a local/inputs.conf and configure the log paths as needed
# Binary File Declaration

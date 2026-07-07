@ECHO OFF

powershell.exe -executionPolicy RemoteSigned -command ". '%SPLUNK_HOME%\etc\apps\TA_MS_ExchangeForwardingRules_for_splunk\bin\powershell\on_premises_exchange_mailbox_forward_rules.ps1'"
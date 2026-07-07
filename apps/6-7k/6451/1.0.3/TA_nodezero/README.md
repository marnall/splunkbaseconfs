Copyright 2022 Horizon3.ai

# Version Support #
8.2 (Python3)

# What does this TA do? #
This TA allows you to pull pentest data from the NodeZero portal into Splunk

# Who is this app for? #
- Anyone who wants to pull NodeZero pentest data into Splunk

# How does the app work? #
- This app works with the https://api.horizon3ai.com GraphQL API
- At a given interval (default = 24 hrs), the modular input will query NodeZero's GraphQL API and ingest the data into the index of your choosing

# Steps to use: #
1. Get an API key for the NodeZero API
2. On the 'Configuration' tab, click the "Add" button on the "Accounts" sub-tab  
    a. `Name` is a _simple_ name that gets used by the `Inputs` page  
    b. `Description` is for any notes/details about the API Key/Account  
    c. `API Key` is an encrypted field for saving the NodeZero API Key
3. On the 'Inputs' tab, click "Create New Input"  
    a. `Name` (required) is a _simple_ name that gets used by the modular input  
    b. `Description` (optional) is for any notes about the modular input  
    c. `API Account` (required) is a dropdown single select to choose the account for which you wish to pull data  
    d. `Polling Interval` (optional) Default is 86400 seconds (daily). How frequently you want to poll for new data
4. Once the input is saved, it immediately begins attempting to pull data from the NodeZero API
5. For troubleshooting information, view `ExecProcessor` logs and the TA_nodezero logs:
    ```
    index=_internal (sourcetype=splunkd nodezero component=ExecProcessor) OR sourcetype="TA_nodezero-*"
    ```
    *Note*: Don't forget the asterisk on the end of `sourcetype=TA_nodezero*`.

# Release Notes #

## v 1.0.0 ##
- Initial Release!  Basic modular input data fetching capability for each pentest's:
  - Summary data
  - Host Summary data
  - Weaknesses
  - Action Logs


# Possible Issues #

# Privacy and Legal #
- Sensitive information (API Key) is stored using Splunk's built-in password management capabilities
- This app cannot be redistributed in any way outside of Splunkbase.
- This app cannot be modified or reverse engineered to alter how the app behaves or interacts with the NodeZero API.


# For support #
- Send email to info@horizon3.ai
- Chat via our Chatlio integration on the NodeZero portal
- Support is not guaranteed and will be provided on a best effort basis.
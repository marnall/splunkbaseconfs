# ReversingLabs TitaniumScale Dashboard for Splunk

The ReversingLabs TitaniumScale Dashboard application for Splunk is a custom security and threat intelligence visualization solution that interprets extensive sets of ReversingLabs TitaniumScale file analysis reports on the Splunk platform.

The Splunk platform receives JSON reports over HTTP or HTTPS from the TitaniumScale product and enables detailed search and interpretation of analyzed files through this application. 

By providing visualization of potentially harmful and malicious files, this application can prevent potential malware from harming the user environment by detecting it and making it visible to threat analysts.

## About TitaniumScale
ReversingLabs TitaniumScale provides advanced static file analysis methods and file visibility for exposing potential attacks before they strike.

“TitaniumScale helps enterprises form a comprehensive assessment of millions of files from web traffic, email, file transfers, endpoints or storage. The solution uses unique ReversingLabs File Decomposition technology to extract detailed metadata, add global reputation context and classify threats.”

### Features
The ReversingLabs TitaniumScale Dashboard app for Splunk can be used for:
- Breaking down analyzed files by type
- Displaying file type statistics
- Summarizing files by threat level
- Displaying threat type statistics
- Searching file reports by:
    - File names or hash values
    - Threat names
    - File types
    - Import hashes
    - YARA matches
    - Certificates

### Prerequisites
- To use this application you need to have a **ReversingLabs TitaniumScale** product set up to send appropriate file analysis reports to the Splunk platform. For more details on this step, please see the "Installation" tab.
- You can apply for a TitaniumScale demo through the ReversingLabs web interface: https://www.reversinglabs.com/products/enterprise-scale-file-anlaysis-software

### Optional
- Certain tabs enable you to pivot from sample hashes to ReversingLabs A1000 by clicking on them.
- To successfully do so, you need to provide an A1000 URL in the text input box at the top of the dashboard without a trailing slash symbol ("/").

### Installation
- Download the .tgz app archive and install it using the “Install app from file” function of the Splunk Apps section.
### Setup
- To be able to use this app after you install it, a new HTTP Event Collector that points to the "tiscale" index needs to be created as a data input. To do so, follow these steps **after installing the app package**:
  - Go to Settings -> Data inputs -> HTTP Event Collector
  - Click on New Token
  - Give this new token a name of your choosing and click Next
  - Make sure that "tiscale" is set as the Default index. If not, select it and also put it into Selected item(s).
  - Click on Review and proceed towards ending the event collector setup.
### Upgrade
- Download the latest version of the application and perform the same procedure as when installing it. This will provide an option to upgrade the existing version.
### Uninstallation
- `$SPLUNK_HOME/bin/splunk remove app reversinglabs <username>:<password>`

### Links
##### TitaniumScale: 
https://www.reversinglabs.com/products/enterprise-scale-file-visibility.html
##### ReversingLabs:
https://www.reversinglabs.com/
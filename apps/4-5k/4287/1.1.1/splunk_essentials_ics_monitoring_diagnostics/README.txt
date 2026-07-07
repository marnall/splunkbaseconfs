# Table of Contents

1. App Description
2. Installation and Tested Environments

# App Description

The Splunk Industrial Control Systems (ICS) Essentials for Monitoring and Diagnostics provides common use cases relevant to ICS environments to enhance or augment current vendor tools. While many general IT monitoring cases also apply to ICS environments, this Essential focuses primarily on specific use cases for ICS. The goal for this essential is to help ICS teams understand the potential use cases around Splunk for Industrial IoT.

Industrial control systems are complex real-time systems which are responsible for monitoring and controlling assets such as as oil and gas pipelines, manufacturing lines, mining operations, logistics, and other industrial processes. These systems are primarily focused on uptime and availability, reducing risk to human life, while maximizing production for an operator.

# Installation and Tested Environments

Please note this application is not designed to be used in a production environment.

## In a single-instance deployment
* If you have internet access from your Splunk server, download and install the app by clicking '''Browse More Apps''' from the Manage Apps page in Splunk platform. 
* If your Splunk server is not connected to the internet, download the app from Splunkbase and install it using the Manage Apps page in Splunk platform. 
Note: If you download the app as a tgz file, Google Chrome could automatically decompress it as a tar file. If that happens to you, use a different browser to download the app file.

## In a distributed deployment
Install the app only on a search head. This app is safe to install in large size clusters, as it will not have an impact on indexers (unless you choose to enable many searches). The app includes many lookups with demo data that shouldn't be replicated to the indexers, but also includes a distsearch.conf file to prevent that replication, so that you needn't worry.

## In a Search Head Cluster deployment
SSE installs into a SHC like any other SHC app, the only area where there is some minimal risk in a SHC setup is when using the Lookup Cache acceleration technique under the First Time Seen detection with very large lookups (See First Time Seen Detection -> Considerations for implementing the large scale version in this doc). This wouldn't be used by default, and even when used would be safe for virtually all scenarios as Search Head Clustering has a robust replication mechanism that works well for larger files. The docs below detail that most SSE lookups using this technique would be a few MB in size, and it's difficult to conceive of a lookup more than 1 GB. I have hunted and the only issue with SHC replication I've found was with a 54 GB KV Store, so you should feel very comfortable using SSE including this technique.

## After installation
Unless you save or enable searches included with the app, there is no increase in indexed data, searches or others.
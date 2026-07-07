DGA App for Splunk - Operationalize Machine Learning to detect malicious domain names
Copyright (C) 2005-2017 Splunk Inc. All rights reserved.

Contributor: Philipp Drieger, philipp@splunk.com

This app shows how to Operationalize Machine Learning using MLTK to detect malicious domain names. Malware like botnets use domain generation algorithms (DGAs) to create URLs that host malicious websites or command and control servers. Static matching does not always help, so machine learning models can add value and allow to increase detection rates.

For details about how this app works in detail please look for upcoming informations in the next app update and checkout the whitepaper available:
https://www.splunk.com/en_us/form/operationalizing-machine-learning-to-detect-malicious-domain.html

Prerequesites for this app:

Obligatory dependencies:
- Splunk Machine Learning Toolkit: https://splunkbase.splunk.com/app/2890/
- URL Toolbox App: https://splunkbase.splunk.com/app/2734/

Optional dependencies for visualizations:
- 3D Scatterplot: https://splunkbase.splunk.com/app/3138/
- Parallel coordinates: https://splunkbase.splunk.com/app/3137/

Go check the setup dashboard for more detailed setup steps.

Third party references:
The datasets that ship with the app are composed of 2 sources:
1. DGA domain names were generated with scripts from Johannes Bader DGA reversing scripts available from https://github.com/baderj/domain_generation_algorithms 
2. Legit domain names were taken from Cisco Umbrella 1 Million (https://umbrella.cisco.com/blog/2016/12/14/cisco-umbrella-1-million/)
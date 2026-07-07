# Hispasec Add-on for Splunk

The Hispasec Add-on for Splunk allows an Splunk admin to ingest Hispasec Notifications API data to be used in use cases that allows to follow notifications about detections and OSINT available information by Hispasec. The Hispasec Add-on for Splunk was developed purely in Python3.

## Release notes

- Version 1.0.5: Apr 10, 2025 Updated Splunk Lib to latest version. Updated other Python libs to latest versions. Added server.conf file to enable cluster replication.
- Version 1.0.4: Mar 22, 2023 Removed from code 2 lines that exposes sensitive data.
- Version 1.0.3: Mar 21, 2023 Adds static assets (icons) that was not included in 1.0.2 version.
- Version 1.0.2: Mar 20, 2023 The application was redesigned to modify the way of obtaining the data from the API, the way of writing the events in the destination index, and maintaining the original JSON structure from the Endpoint. In addition, the way to configure the data origin was redesigned, allowing the inclusion of a custom API endpoint if it exists, as well as allowing the inclusion of a single API token
- Version 1.0.1: Oct 19, 2022 Fixes major issues with first release 1.0.0 that not works in Splunk Enterprise
- Version 1.0.0: Oct 18, 2022 Hispasec Add-on for Splunk is the Tecnical Add-on (TA) developed for ingest or map security data collected from Hispasec services, using their API. Hispasec Add-on for Splunk provides common information model (CIM) knowledge, to use with other Splunk Enterprise apps such as Splunk Enterprise Security

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)

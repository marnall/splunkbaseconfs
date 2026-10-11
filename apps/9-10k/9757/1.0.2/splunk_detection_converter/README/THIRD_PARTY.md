# Third-party code

- Splunk Python SDK 2.1.0 (`lib/splunklib`): Apache 2.0.
- Splunk Security Content EventBasedDetection schema, commit `a02c60b2c7f132dda85c7e65b898317d1e9b97a9` (`lib/detection_yaml_converter/schemas/ng-a02c60b2.json`): Apache 2.0, unmodified.
- PyYAML 6.0.3 (`lib/yaml`): MIT, pure Python files only.
- JSZip 3.10.1 (`appserver/static/vendor/jszip.browser.min.js`): MIT. The optional Node `stream` import in module 16 is disabled for Splunk's browser loader.

Full licence notices are alongside this file. `Apache-2.0-LICENSE.txt` covers both Apache components. The installed app downloads no libraries or schemas.

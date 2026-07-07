# Fireeye Mock Server

The file `fireeye_cm_mockoon.json` is an exported [Mockoon](https://mockoon.com/) environment that can be used to spin up a mock server for testing the integration during development without a CM appliance.

## Getting Started
Given instructions refer to a local installation of [Mockoon](https://mockoon.com/).

If you're willing to deploy Mockoon in machines other than localhost, you might be interested in:
* [Mockoon CLI](https://mockoon.com/cli/)
* [Mockoon CLI Docker](https://hub.docker.com/r/mockoon/cli)

### Requirements
* Download and install [Mockoon](https://mockoon.com/download/)

### Usage

#### Desktop Application

* Launch Mockoon
* Import Mockoon's formatted file.
* Eventually re-configure the defined server port
* Start the server by clicking on the button `Play`


#### CLI Application

```
mockoon-cli start --data ./fireeye_cm_mock.json
```

For more advanced usages of Mockoon refer to its own documentation.

## References
* [Online API Editor](https://editor.swagger.io/)
* [Mockoon Templating](https://mockoon.com/docs/latest/templating/overview/)
* [Faker.js documentation](https://marak.github.io/faker.js)
* [Dummy-JSON documentation](https://github.com/webroo/dummy-json)

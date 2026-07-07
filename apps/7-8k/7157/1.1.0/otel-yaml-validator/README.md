# OTel YAML Validator

Made by Daniel Spavin [daniel@spavin.net](mailto:daniel@spavin.net)

Version 1.0.0


# About

This app lets you create and validate OTel YAML config files. 

## Create YAML config

The Create dashboard will walk you through setting up an OTel config file for a stand-alone, gateway, or kubernetes implementation.

Each step along the process will require selecting which resources you would like, and filling out any optional variables. Once you have selected your extensions, receivers, processors, and exporters, you will be able to copy the YAML contents. Click the "Copy YAML" to copy it to the clipboard.

Once you have the content, you can then validate it on the Validate dashboard.


## Validate YAML config

The validate dashboard lets you visualise the receivers, processors, and exporters configured in your pipelines. Any issues with the YAML syntax will be highlighted at the bottom of the screen. You can click on an issue to go to that line in the editor.

Clicking on a receiver, processor, or exporter in the pipeline visualisation on the right will take you to that resource's definition in the YAML file. No visualisation is displayed when there are issues with the YAML syntax.
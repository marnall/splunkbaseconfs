# GitLab Add-on for Splunk

The GitLab Add-on for Splunk provides field extraction, normalization, event types, and CIM-compatible tagging for GitLab log data.

## Supported sourcetypes

- gitlab:audit:json
- gitlab:application:json
- gitlab:production:json
- gitlab:api:json
- gitlab:shell
- gitlab:nginx:access
- gitlab:sidekiq

## CIM compatibility

The add-on provides CIM normalization for the following data models:

### Authentication

Supported sourcetypes:

- gitlab:application:json
- gitlab:shell

Examples include:

- Successful GitLab user authentication
- SSH key authenticated Git operations

### Web

Supported sourcetypes:

- gitlab:production:json
- gitlab:api:json
- gitlab:nginx:access

Normalized fields include:

- user
- src
- src_ip
- http_method
- uri_path
- uri_query
- status
- action
- http_user_agent
- response_time
- app
- vendor_product

## Additional GitLab data

The following sourcetypes are parsed and normalized but are not currently mapped to a CIM data model:

- gitlab:audit:json
- gitlab:sidekiq

## Installation

Install the add-on on the appropriate Splunk components.

### Search Head

Install the add-on on the Search Head to provide:

- field extractions
- field aliases
- calculated fields
- event types
- tags
- CIM normalization

### Universal Forwarder

Install the add-on on the Universal Forwarder running on the GitLab server if the included file monitoring inputs are used.

The inputs included with this add-on are disabled by default.

Enable only the required inputs using a local configuration or a Deployment Server.

Example:

    [monitor:///var/log/gitlab/gitlab-rails/application_json.log]
    disabled = 0
    index = gitlab
    sourcetype = gitlab:application:json

### Indexer / Heavy Forwarder

Install the add-on on the parsing tier when index-time parsing settings are required.

## Required index

The default input examples use:

    index = gitlab

Create the index before enabling the inputs, or override the index setting in local/inputs.conf.

## Compatibility

Splunk Enterprise
Splunk Enterprise Security

## Version

1.0.0

## Support

Developed and maintained by Cyberfox.

For support, contact the add-on maintainer through the Splunkbase listing.

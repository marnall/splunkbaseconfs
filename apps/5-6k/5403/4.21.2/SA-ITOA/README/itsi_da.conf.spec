# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
#
# This configuration file is DEPRECATED.
# For [entity_source_template://<string>], use inputs.conf/[itsi_csv_import://<name>] instead.
# For [service_template://<string>], use itsi_service_template.conf/[string] instead.
#
# This file contains possible settings you can use to configure an itsi_da.conf file. Use this
# file to configure an app to export entity searches and service templates for use within the
# IT Service Intelligence (ITSI) app.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how
# to configure this file.

[entity_source_template://<string>]

title = <string>
* The display name of the search.

description = <string>
* A human-readable description of this search.

saved_search = <string>
* The actual Splunk saved search that outputs a table. This will be enforced by
  client-side code.

title_field = <string>
* A single field that acts as the title for the entity.

description_fields = <comma-separated list>
* A list of fields that describe the entity.

identifier_fields = <comma-separated list>
* A list of fields that identify the entity.

informational_fields = <comma-separated list>
* A list of fields that act as additional entity metadata.

[service_template://<string>]

title = <string>
* A title for the service template.

description = <string>
* The full description of the service being created.

entity_source_templates = <comma-separated list>
* The list of entity searches that create entities that can be used with this service.
* The list is used to populate the list of entity searches in the combined
  entity-service creation workflow.

entity_rules = <string>
* A list of entity rules (rules specification) used to associate entities to service
  created from this template.
* This field is the same as the entity_rules field in itsi_service.conf.spec.

recommended_kpis = <comma-separated list>
* A list of KPIs that are automatically added when a service is created with this template.

informational_kpis = <comma-separated list>
* A list of informational (no threshold) KPIs that are automatically added when a
  service is created with this template.

optional_kpis = <comma-separated list>
* A list of KPIs that are available for this service (but not added automatically).

Extreme Vigilance 1.57.4
Copyright (C) 2023 BlueVoyant Inc.  All Rights Reserved.

For the latest documentation see: https://scianta.gitbook.io/scianta-for-splunk/

For any support issues, please contact contact@bluevoyant.com or
visit our contact page: https://www.bluevoyant.com/contact-us

The following OSS products are used in this application.  Please see the
following links for each product and associated licenses:

    bootstrap-slider.js
        https://github.com/seiyria/bootstrap-slider
    d3.v3.js
        https://github.com/d3/d3
    nv.d3.js
        https://github.com/novus/nvd3
    owl.carousel.js
        https://github.com/OwlCarousel2/OwlCarousel2
    spin.js
        http:spin.js.org

The Extreme Vigilance writes/reads files in the following $(SPLUNK_HOME)/etc/apps/bv_xv/scm directory:

    $(SPLUNK_HOME)/etc/apps/bv_xv/scm/backups
       Location for Cognitive Models that have been exported.
    $(SPLUNK_HOME)/etc/apps/bv_xv/scm/db
       Location of the Mongo Database Files (for default Mongo installation).
    $(SPLUNK_HOME)/etc/apps/bv_xv/scm/models
       Location of the Cognitive Model files supporting UI.
    $(SPLUNK_HOME)/etc/apps/bv_xv/scm/temp
       Location temporary files being written and immediately removed.
    $(SPLUNK_HOME)/var/spool/splunk/...stash_scm_signals/
       Location where signals are written to be read into index by File Input.

The Extreme Vigilance utilizes files the following lookup files in $(SPLUNK_HOME/etc/apps/bv_xv/lookups:
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/APPLICATION.context.csv
       Definition of Application Level Contexts that will be imported into data store.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/bv_actors-default.csv
       Initial installation you can seed a default set of actors by editing this file.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/bv_actors.csv
       Resource file extracted from default that you can seed with actors on installation.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/app_types.csv
       Definition of Applications Supported
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/asset_types.csv
       Definition of supported Asset Types.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/bv_assets-default.csv
       Initial installation you can seed a default set of assets by editing this file.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/bv_assets.csv
       Resource file extracted from default that you can seed with assets on installation.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/categories-default.csv
       Initial installation of bv_xv seeds categories.csv with this file.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/categories.csv
       Definition of supported actor categories.
    $(SPLUNK_HOME/etc/apps/bv_xv/config/resource-mapping-default.json
       Initial installation seeds resource-mapping.json with this file.
    $(SPLUNK_HOME/etc/apps/bv_xv/config/resource-mapping.json
       Definition of resource mappings.
    $(SPLUNK_HOME/etc/apps/bv_xv/config/scm-framework-default.properties
       Initial installation of bv_xv seeds scm-framework.properties with this file.
    $(SPLUNK_HOME/etc/apps/bv_xv/configlookups/scm-framework.properties
       Definition of properties used by bv_xv.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/scm-synonyms.csv.
       Definition of hedge synonyms for Extreme Search supported by bv_xv.
    $(SPLUNK_HOME/etc/apps/bv_xv/lookups/signal_types.csv
       Definition of signal types supported by bv_xv

The following 3rd party software is used by the backend:

Zip: https://github.com/kuba--/zip
XML: tinyxml
JSON: Rapidjson
HTTP: libcurl
Mongo Database: libmongoc and libbson

# Binary File Declaration
Source Code for binaries delivered in separate files for cloud certification.

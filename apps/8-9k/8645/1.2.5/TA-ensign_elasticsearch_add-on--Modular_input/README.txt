Ensign ElasticSearch Data Integrator
=====================================

Version : 1.2.3
Author  : Muhammad Rafdi Aufar Ahmad (Ensign Infosecurity Indonesia)
Build   : 1776910772


DESCRIPTION
-----------
This Splunk add-on provides modular input capabilities for ingesting data
from Elasticsearch clusters into Splunk. Built on the Splunk UCC Framework
(Add-on Builder), it offers a full GUI-driven configuration experience via
Splunk Web.

IMPORTANT: This add-on is designed exclusively for and tested against the
Elasticsearch 8.x REST API. It is NOT compatible with Elasticsearch 7.x
or earlier versions due to breaking API changes introduced in version 8.

Key features:
  - Multi-cluster Elasticsearch profile management via Splunk UI
  - Multi-node cluster support with node sniffing/auto-discovery
  - Configurable time-based data fetching with ES Scroll API pagination
  - DSL Query-focused data retrieval with custom term filters
  - SSL/TLS certificate verification support
  - Crash-resilient scroll recovery with dedicated checkpoint directory
  - KVStore checkpoint storage with smart bidirectional fallback (v1.2.3)
  - Document-level deduplication guard (rolling 50,000 IDs per stanza)
  - Global proxy support with Splunk-native credential encryption
  - Custom sourcetype override per input stanza
  - Custom SPL diagnostic commands: escheck_connection, escheck_config,
    escheck_indexes (v1.2.3)
  - Comprehensive internal log parsing for taensignelasticsearchaddon:log
  - Minimum polling interval enforcement (15 seconds)
  - Adjustable log level (DEBUG/INFO/WARN/ERROR)


COMPATIBILITY
-------------
  - Elasticsearch: 8.x only (uses Elasticsearch 8 REST API)
  - Splunk Enterprise: 8.2+ or 9.x
  - Python: 3.x (bundled with Splunk)
  - Network: HTTPS access to target Elasticsearch cluster(s)


INSTALLATION
------------
  1. Install the add-on via Splunk Web:
     Settings > Install app from file > Upload the .tar.gz package

  2. Or extract directly to:
     $SPLUNK_HOME/etc/apps/TA-ensign_elasticsearch_add-on--Modular_input/

  3. Restart Splunk

  4. Configure ES Cluster profiles in:
     Settings > Ensign ElasticSearch Data Integrator > Configuration > ES Clusters

  5. Create data inputs in:
     Settings > Data inputs > Elasticsearch Source

  6. (Optional) Configure checkpoint storage backend:
     Settings > Ensign ElasticSearch Data Integrator > Configuration > Checkpoint


CUSTOM SPL COMMANDS (v1.2.3)
-----------------------------
  | escheck_connection cluster_name="<name>"
    Test connectivity to a configured Elasticsearch cluster.

  | escheck_config cluster_name="<name>"
    Display cluster configuration and live health status.

  | escheck_indexes cluster_name="<name>"
    List all Elasticsearch indices with health and statistics.

  NOTE: These commands can only be run from within this add-on's context.


SUPPORT
-------
  Muhammad Rafdi Aufar Ahmad
  Ensign Infosecurity Indonesia
  rafdi_ahmad@ensigninfosecurity.com
  https://www.ensigninfosecurity.com


BINARY FILE DECLARATION
-----------------------
This add-on contains the following pre-compiled binary files which do not
require source code:

  bin/ta_ensign_elasticsearch_add_on_modular_input/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so
    PyYAML C extension - MIT License - Copyright Kirill Simonov

  bin/ta_ensign_elasticsearch_add_on_modular_input/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so
    MarkupSafe C extension - BSD License - Copyright Pallets Projects

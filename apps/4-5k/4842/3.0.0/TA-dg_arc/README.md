Version 3.0.0

JSON Flattened Export Format FIELDALIAS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Added FIELDALIAS support to facilitate dashboard migration from JSON Flattened format used in ARC REST API v1 to the structure used in REST API v2.
This enhancement ensures smoother compatibility and transition between API versions, especially for dashboards relying on legacy field mappings.

Support for JSON Export Format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can now export data using the JSON format option, where each event is represented as a single
row. This eliminates duplication and helps reduce Splunk license usage.

Note: Switching to the JSON format may impact existing dashboards that rely on the previous
multi-row or flattened structure. Dashboards may require updates to SPL queries or field
extractions to remain functional.

Added the ability to configure the REST API Call Interval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
REST API Call Interval allows you to control the delay between fetches. This helps optimize ARC REST API resource usage and manage event throttling.

Introduced Multi-threaded Processing Support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Introduced a new Thread Count setting to enable multi-threaded event processing. This improves
performance and scalability on systems with multiple CPU cores.

Enhanced logging for data ingestion from ARC to improve observability and performance tracking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Added detailed timestamps for processing and receiving stages.
These metrics are now surfaced in the Data Flow Diagnostic dashboard, enabling better monitoring and troubleshooting of ingestion latency and throughput.

The report_cache parameter behaves differently for the detonate file and detonate url actions. These
differences are outlined below.

**Detonate File**

- If caching is enabled and cookbook is provided then the caching is ignored and a new detonation
  analysis process is spawned
- If caching is enabled and cookbook is not provided then the analysis report of the latest
  spawned process on Joe Sandbox for the provided file hash, is returned
- If caching is not enabled then always a new detonation analysis process is spawned

**Detonate URL**

- If caching is enabled then the analysis report of the latest spawned process on Joe Sandbox for
  the provided URL, is returned
- If caching is not enabled then always a new detonation analysis process is spawned

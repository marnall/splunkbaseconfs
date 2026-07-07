# search_similarity.conf.spec
# Settings for the search_similarity REST handler (metric index cache).

[cache]
max_index_cache_entries = <positive integer>
* Maximum number of distinct (metric, qval, index_type) indexes cached in each
  persistent handler process. Least-recently-used entries are dropped when this
  limit is exceeded. Memory use still scales with corpus size and index type.
* Valid range: 1 - 100000. Values outside this range fall back to the default
  with a warning in the handler log.
* Default: 1000
* After changing this setting, restart splunkd (or wait for the persistent
  worker to restart) so the handler process reloads configuration.

import configparser
import json
import logging
import os
import sys
from collections import OrderedDict

from splunk.persistconn.application import PersistentServerConnectionApplication


def get_app_root():
    """
    Determines the root directory of the current Splunk app based on the file's location.

    Returns:
        str: Absolute path to the app's root directory (e.g., $SPLUNK_HOME/etc/apps/<app_name>).
    """
    # Ensure SPLUNK_HOME is defined
    splunk_home = os.environ.get("SPLUNK_HOME")
    if not splunk_home:
        raise EnvironmentError("SPLUNK_HOME environment variable is not set.")

    # Resolve the current script's directory
    current_file_path = os.path.abspath(__file__)

    # The apps directory is $SPLUNK_HOME/etc/apps
    apps_dir = os.path.join(splunk_home, "etc", "apps")

    if not current_file_path.startswith(apps_dir):
        raise RuntimeError(
            f"The current file path ({current_file_path}) is not under the expected apps directory ({apps_dir})."
        )

    # Derive the app's root directory
    app_relative_path = current_file_path[len(apps_dir) + 1 :]
    app_name = app_relative_path.split(os.sep)[0]
    return os.path.join(apps_dir, app_name)


# Set up app_root using the dynamic SPLUNK_HOME-based path
app_root = get_app_root()
bin_dir = os.path.join(app_root, "bin")

if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

from lib_path import prepend_bin_dir, prepend_vendor_lib

prepend_vendor_lib(app_root)
prepend_bin_dir(bin_dir)


# Configure logging using centralized utility with graceful fallback
try:
    from utils.logging import setup_logger
except ImportError:
    # Fallback if logging_utils is not available (shouldn't happen in normal usage)
    def setup_logger(name="search_similarity_handler", **kwargs):
        """Minimal fallback logger setup"""
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

# Initialize the logger
logger = setup_logger("search_similarity_handler")
LOG_PREFIX = "[search_similarity_handler] "

from urllib.parse import parse_qs

DEFAULT_MAX_INDEX_CACHE_ENTRIES = 1000
MIN_INDEX_CACHE_ENTRIES = 1
MAX_INDEX_CACHE_ENTRIES_CAP = 100000


def _load_max_index_cache_entries(app_root):
    """
    Read [cache]/max_index_cache_entries from merged default + local
    search_similarity.conf. Local overrides default.
    """
    default_path = os.path.join(app_root, "default", "search_similarity.conf")
    local_path = os.path.join(app_root, "local", "search_similarity.conf")
    parser = configparser.ConfigParser(interpolation=None)
    if os.path.isfile(default_path):
        parser.read(default_path, encoding="utf-8")
    if os.path.isfile(local_path):
        parser.read(local_path, encoding="utf-8")

    sources = []
    if os.path.isfile(default_path):
        sources.append("default/search_similarity.conf")
    if os.path.isfile(local_path):
        sources.append("local/search_similarity.conf")
    source_desc = " + ".join(sources) if sources else "built-in default (no conf file)"

    if not parser.has_section("cache") or not parser.has_option(
        "cache", "max_index_cache_entries"
    ):
        return DEFAULT_MAX_INDEX_CACHE_ENTRIES, source_desc

    raw = parser.get("cache", "max_index_cache_entries").strip()
    try:
        v = int(raw)
    except ValueError:
        logger.warning(
            LOG_PREFIX + "Invalid max_index_cache_entries %r in search_similarity.conf; using %d",
            raw,
            DEFAULT_MAX_INDEX_CACHE_ENTRIES,
        )
        return DEFAULT_MAX_INDEX_CACHE_ENTRIES, source_desc

    if v < MIN_INDEX_CACHE_ENTRIES or v > MAX_INDEX_CACHE_ENTRIES_CAP:
        logger.warning(
            LOG_PREFIX
            + "max_index_cache_entries=%s out of range [%d, %d]; using %d",
            v,
            MIN_INDEX_CACHE_ENTRIES,
            MAX_INDEX_CACHE_ENTRIES_CAP,
            DEFAULT_MAX_INDEX_CACHE_ENTRIES,
        )
        return DEFAULT_MAX_INDEX_CACHE_ENTRIES, source_desc

    return v, source_desc

try:
    from core.parsing.normalizer import (
        normalize_search_for_similarity,
        normalize_search_for_display,
    )
    from core.sources.loaders import (
        aggregate_searches,
        ConfFileSearchSource,
        RestSearchSource,
    )
except ImportError as e:
    logger.error(
        LOG_PREFIX + f"Error: Could not import parsing/sources modules. {e}"
    )
    sys.exit(1)

try:
    from core.similarity.calculator import calculate_top_similarities
except ImportError as e:
    logger.error(
        LOG_PREFIX + f"Error: Could not import 'calculate_top_similarities'. {e}"
    )
    sys.exit(1)

# Optional: metric space indexes for fast nearest-neighbor queries
try:
    from core.similarity.spaces import create_index

    _metric_spaces_available = True
except ImportError as e:
    logger.warning(
        LOG_PREFIX + f"metric_spaces not available; will use linear scan. {e}"
    )
    _metric_spaces_available = False

# Splunk's persistconn appserver creates a new handler instance for every REST
# request (see splunk.persistconn.appserver.PersistentServerConnectionApplicationServer.load).
# scripttype=persist only keeps this Python worker process alive. Cross-request
# caches must live at module scope, not on self.
_similarity_cache = {
    "index": OrderedDict(),
    "corpus_hash": None,
    "max_entries": DEFAULT_MAX_INDEX_CACHE_ENTRIES,
    # Mtimes of the conf files seen on the most recent successful (re)load.
    # Used by _refresh_conf_if_changed to decide whether to re-parse on a
    # request. Empty dict means "first call, force a load".
    "conf_mtimes": {},
    "conf_source": "(uninitialized)",
}


def _conf_paths():
    return [
        os.path.join(app_root, "default", "search_similarity.conf"),
        os.path.join(app_root, "local", "search_similarity.conf"),
    ]


def _refresh_conf_if_changed():
    """
    Re-read search_similarity.conf when any source file's mtime has changed.

    Splunk's persistent REST workers (scripttype=persist) stay alive across
    requests, so without this check a conf change would not be visible until
    the next splunkd restart. Combined with `[triggers] reload.search_similarity
    = simple` in app.conf, this lets `splunk reload search_similarity` (and
    on-disk edits to default/local conf files) take effect on the next request
    without forcing a Splunk restart.

    Returns True if a reload happened, False if mtimes were unchanged.
    """
    current_mtimes = {}
    changed = bool(_similarity_cache["conf_mtimes"]) is False  # first call: force load
    for p in _conf_paths():
        try:
            mt = os.stat(p).st_mtime_ns
        except OSError:
            mt = None
        current_mtimes[p] = mt
        if _similarity_cache["conf_mtimes"].get(p) != mt:
            changed = True
    if not changed:
        return False

    try:
        new_value, source = _load_max_index_cache_entries(app_root)
    except configparser.Error as e:
        logger.warning(
            LOG_PREFIX
            + "Invalid search_similarity.conf; keeping previous cache settings. Error: %s",
            e,
        )
        return False
    old_value = _similarity_cache["max_entries"]
    _similarity_cache["conf_mtimes"] = current_mtimes
    _similarity_cache["conf_source"] = source
    _similarity_cache["max_entries"] = new_value
    if old_value != new_value:
        logger.info(
            LOG_PREFIX
            + "search_similarity.conf reloaded: max_index_cache_entries %d -> %d (config: %s)",
            old_value,
            new_value,
            source,
        )
        # New cap is smaller than current cache size: evict from the LRU tail
        # so we honor the new limit on the next request.
        idx_map = _similarity_cache["index"]
        while len(idx_map) > new_value:
            evicted_key, _ = idx_map.popitem(last=False)
            logger.debug(
                LOG_PREFIX
                + "Reload eviction: dropped cache_key=%r (entries_after=%d, max=%d)",
                evicted_key,
                len(idx_map),
                new_value,
            )
    return True


# Initial load at import time so the first request hits a primed cache.
_refresh_conf_if_changed()
logger.info(
    LOG_PREFIX + "Metric index LRU cache max_entries=%d (config: %s)",
    _similarity_cache["max_entries"],
    _similarity_cache["conf_source"],
)


class SearchSimilarity(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        logger.info(LOG_PREFIX + "Initializing SearchSimilarity handler")
        logger.debug(LOG_PREFIX + "pid: %s", str(os.getpid()))
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        """
        Handles incoming requests to the /search_similarity endpoint.
        """
        logger.info(LOG_PREFIX + "Handling request for /search_similarity")

        # Pick up any on-disk conf changes (cheap mtime check). See
        # _refresh_conf_if_changed for why this is necessary under
        # scripttype=persist.
        _refresh_conf_if_changed()

        # Parse the incoming data
        try:
            # Parse the input string as JSON
            request_data = json.loads(in_string)
            logger.debug(LOG_PREFIX + f"Parsed request data: {request_data}")

            # Extract the "form" field
            form_data = request_data.get("form", [])
            logger.debug(LOG_PREFIX + f"Extracted form data: {form_data}")

            # Convert "form" from a list of key-value pairs to a dictionary
            parsed_form = {key: value for key, value in form_data}
            logger.debug(LOG_PREFIX + f"Parsed form dictionary: {parsed_form}")

            # Extract parameters from the form data
            search = parsed_form.get("search")
            # Default to enhanced TF-IDF for best ranking quality
            # Falls back to length-normalized if enhanced unavailable
            metric = parsed_form.get("metric", "tfidf_enhanced")
            top_n_str = parsed_form.get("top_n", "10")
            qval = parsed_form.get("qval", None)
            use_index_str = parsed_form.get("use_index", "false")
            index_type = parsed_form.get("index_type", "vp")  # vp, bk, or linear
        except Exception as e:
            logger.error(LOG_PREFIX + f"Error parsing request data: {e}")
            return {"payload": {"error": "Invalid request format"}, "status": 400}

        # Validate the search parameter
        if not search:
            logger.error(LOG_PREFIX + "Missing required parameter: search")
            return {
                "payload": {
                    "error": "Missing required parameter: search",
                    "original_request_test": request_data,
                },
                "status": 400,
            }
        # Convert top_n to an integer
        try:
            top_n = int(top_n_str)
        except ValueError:
            logger.error(LOG_PREFIX + f"Invalid value for top_n: {top_n_str}")
            return {
                "payload": {"error": "Invalid value for top_n. Must be an integer."},
                "status": 400,
            }

        # Parse use_index flag
        use_index = use_index_str.lower() in ("true", "1", "yes")

        # Normalize the incoming search to match stored-search normalization (remove params, collapse whitespace)
        try:
            normalized_search = normalize_search_for_similarity(search)
        except Exception as e:
            logger.warning(
                LOG_PREFIX
                + f"Failed to normalize incoming search. Using raw input. Error: {e}"
            )
            normalized_search = search

        # Retrieve available searches
        try:
            # Include conf file plus REST endpoint if session is available
            session_key = (
                request_data.get("session", {}).get("authtoken")
                if isinstance(request_data.get("session"), dict)
                else None
            )
            sources = [ConfFileSearchSource()]
            if session_key:
                sources.append(RestSearchSource(session_key=session_key))
            records = aggregate_searches(sources)
            # Keep raw authored queries; build normalized copies for scoring
            raw_queries = [r.query for r in records]
            norm_queries = [normalize_search_for_similarity(s) for s in raw_queries]

        except FileNotFoundError as e:
            logger.error(LOG_PREFIX + f"Error loading searches: {e}")
            return {"payload": {"error": str(e)}, "status": 500}
        except Exception as e:
            logger.error(LOG_PREFIX + f"Unexpected error while loading searches: {e}")
            return {
                "payload": {"error": "Failed to load available searches."},
                "status": 500,
            }

        # Perform similarity calculations
        try:
            # Check if we should use metric space index for faster queries
            # TF-IDF metrics require linear scan (corpus-dependent, can't be pre-indexed)
            if use_index and _metric_spaces_available and not metric.startswith("tfidf_"):
                logger.info(
                    LOG_PREFIX
                    + f"Using metric space index ({index_type}) for metric '{metric}'"
                )

                # Generate hash of corpus to detect changes
                corpus_hash = hash(tuple(norm_queries))
                cache_key = f"{metric}_{qval}_{index_type}"

                # Build or retrieve cached index (module-level: new handler each request).
                # When the corpus changes, drop all cached indexes: other cache_keys would
                # still match corpus_hash after we rebuild one metric and would otherwise
                # keep stale structures built from the previous corpus.
                idx_map = _similarity_cache["index"]
                max_entries = _similarity_cache["max_entries"]
                if _similarity_cache["corpus_hash"] != corpus_hash:
                    cleared_keys = len(idx_map)
                    prev_hash = _similarity_cache["corpus_hash"]
                    idx_map.clear()
                    _similarity_cache["corpus_hash"] = corpus_hash
                    logger.debug(
                        LOG_PREFIX
                        + "idx_map clear: dropped %d cache key(s), corpus_hash %r -> %r",
                        cleared_keys,
                        prev_hash,
                        corpus_hash,
                    )
                    logger.info(
                        LOG_PREFIX + "Corpus changed; cleared metric index cache"
                    )

                if cache_key in idx_map:
                    idx_map.move_to_end(cache_key)
                else:
                    while len(idx_map) >= max_entries:
                        evicted_key, _ = idx_map.popitem(last=False)
                        logger.debug(
                            LOG_PREFIX
                            + "LRU eviction: dropped cache_key=%r (entries_after=%d, max=%d)",
                            evicted_key,
                            len(idx_map),
                            max_entries,
                        )
                    logger.info(
                        LOG_PREFIX
                        + f"Building {index_type} index for {len(norm_queries)} queries"
                    )
                    idx_map[cache_key] = create_index(
                        index_type=index_type,
                        items=norm_queries,
                        metric=metric,
                        qval=qval,
                        pre_normalized=True,
                    )
                    index_size = idx_map[cache_key].size_human()
                    logger.info(
                        LOG_PREFIX + f"Index built successfully; size={index_size}"
                    )

                # Query the index
                idx = idx_map[cache_key]
                results = idx.query_top_n(normalized_search, top_n=top_n)

                # Results are (index, distance), convert distance to similarity if needed
                # For most metrics, distance = 1 - similarity
                if metric == "p_levenshtein":
                    # p_levenshtein returns raw edit distance, keep as-is
                    top_idx_scores = results
                else:
                    # Convert distance to similarity: similarity = 1 - distance
                    top_idx_scores = [(idx, 1.0 - dist) for idx, dist in results]

                logger.info(
                    LOG_PREFIX
                    + f"Index query completed; retrieved {len(top_idx_scores)} results"
                )
            else:
                # Use standard linear scan (always works, supports all metrics including TF-IDF)
                if use_index and not _metric_spaces_available:
                    logger.warning(
                        LOG_PREFIX
                        + "Metric space indexes requested but not available; using linear scan"
                    )
                if use_index and metric.startswith("tfidf_"):
                    logger.info(
                        LOG_PREFIX
                        + f"TF-IDF metric '{metric}' requires linear scan; index not used"
                    )

                logger.info(
                    LOG_PREFIX
                    + f"Calculating top {top_n} results using metric '{metric}'"
                )
                # Pass corpus_queries to enable TF-IDF and other corpus-based metrics
                top_idx_scores = calculate_top_similarities(
                    normalized_search,
                    norm_queries,
                    metrics=metric,
                    top_n=top_n,
                    qval=qval,
                    return_index=True,
                    corpus_queries=norm_queries,  # Enable TF-IDF by providing corpus
                )
                logger.info(
                    LOG_PREFIX + "Similarity calculations completed successfully"
                )
        except ValueError as e:
            logger.error(LOG_PREFIX + f"Error during similarity calculation: {e}")
            return {"payload": {"error": str(e)}, "status": 400}
        except Exception as e:
            logger.error(
                LOG_PREFIX + f"Unexpected error during similarity calculation: {e}",
                exc_info=True,
            )
            return {
                "payload": {
                    "error": "An unexpected error occurred during similarity calculation."
                },
                "status": 500,
            }

        # Prepare the response payload (filter queries for output to avoid escaped newlines)
        payload = {
            "search": normalize_search_for_display(search),
            "metric": metric,
            "qval": qval,
            "used_index": use_index
            and _metric_spaces_available
            and not metric.startswith("tfidf_"),
            "index_type": index_type if use_index else None,
            "corpus_size": len(records),
            "top_results": [
                {
                    "search_name": records[idx].name,
                    "title": records[idx].title,
                    "quid": records[idx].quid,
                    "query": normalize_search_for_display(raw_queries[idx]),
                    "score": round(score, 6),  # Round to 6 decimals to avoid floating-point noise
                }
                for idx, score in top_idx_scores
            ],
        }
        logger.debug(LOG_PREFIX + f"Response payload: {payload}")

        return {"payload": payload, "status": 200}

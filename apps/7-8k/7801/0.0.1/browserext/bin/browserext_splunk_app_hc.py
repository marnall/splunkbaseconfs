#!/usr/bin/env python3
import os
import sys
import json
import time
import logging
import requests
import traceback
import fcntl
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from splunklib.results import JSONResultsReader

# Splunk SDK
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
import splunklib.results as results

# Constants
SPLUNK_HOME = os.environ.get('SPLUNK_HOME', '/opt/splunk')
LOG_FILE = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', 'browserext_input.log')
STORAGE_FILE = os.path.join(SPLUNK_HOME, 'var', 'run', 'splunk', 'processed_extensions.json')
API_URL = "https://browserext-lookup.onrender.com/analyze"
API_TIMEOUT = 600  # API request timeout in seconds
THREADS = 1  # Number of concurrent API requests
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

# Hardcoded API key (replace with your actual API key)
BROWSEREXT_API_KEY = "822222222222221" # Replace with your actual API key

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filename=LOG_FILE,
    filemode='a'
)
logger = logging.getLogger("browserext_input")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

class BrowserExtRetriever:
    def __init__(self):
        """Initialize the BrowserExt data retriever."""
        self.session_key = self._get_session_key()
        self.service = self._connect_to_splunk()
        self.api_key = BROWSEREXT_API_KEY  # Use the hardcoded API key
        self.event_count = 0
        self.error_count = 0
        self.session = self._configure_requests()
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('HOSTNAME', 'unknown')

    def _get_session_key(self):
        """Get the session key from Splunk."""
        try:
            return sys.argv[1] if len(sys.argv) > 1 else None
        except Exception as e:
            logger.error(f"Error getting session key: {str(e)}")
            return None

    def _connect_to_splunk(self):
        """Connect to Splunk using session key or local credentials."""
        try:
            if self.session_key:
                return client.Service(token=self.session_key)
            return client.connect(
                host=os.environ.get('SPLUNK_HOST', 'localhost'),
                port=int(os.environ.get('SPLUNK_PORT', '8089')),
                username=os.environ.get('SPLUNK_USER', 'admin'), # Splunk user
                password=os.environ.get('SPLUNK_PASSWORD', 'changeme') # Splunk password
            )
        except Exception as e:
            logger.error(f"Error connecting to Splunk: {str(e)}")
            sys.exit(1)

    def _configure_requests(self):
        """Configure HTTP session with retry handling."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def _load_processed_extensions(self):
        """Load and auto-clean old entries."""
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, 'r') as f:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    data = json.load(f)
                    fcntl.flock(f, fcntl.LOCK_UN)

                cleaned = self._clean_old_entries(data)
                if len(data) != len(cleaned):
                    self._save_processed_extensions(cleaned)
                return cleaned
            except Exception as e:
                logger.error(f"Load error: {str(e)}")
                return {}
        return {}

    def _save_processed_extensions(self, processed):
        """Atomic save with file locking and temp file."""
        try:
            os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
            temp_file = STORAGE_FILE + ".tmp"
            
            with open(temp_file, 'w') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(processed, f)
                fcntl.flock(f, fcntl.LOCK_UN)
                
            os.replace(temp_file, STORAGE_FILE)
        except Exception as e:
            logger.error(f"Save error: {str(e)}")
            logger.debug(traceback.format_exc())

    def _clean_old_entries(self, processed):
        """Remove entries older than 7 days."""
        current_time = time.time()
        return {k: v for k, v in processed.items() 
                if (current_time - v) < SEVEN_DAYS_SECONDS}

    def has_been_processed(self, ext_id):
        """Check if extension was processed within 7 days."""
        processed = self._load_processed_extensions()
        return (time.time() - processed.get(ext_id, 0)) < SEVEN_DAYS_SECONDS

    def update_processed(self, ext_id):
        """Update processing timestamp with thread-safe locking."""
        processed = self._load_processed_extensions()
        processed[ext_id] = int(time.time())
        self._save_processed_extensions(processed)

    def fetch_extension_ids(self, days=7):
        """Fetch extension IDs from Zscaler logs."""
        try:
            query = '''
            search `zscaler` earliest=-7d@d
            | rex field="url" "\/(?<crxID>[a-z]+)_"
            | rex field="url" "_(?<crxVersion>\d+_\d+_\d+_\d+).crx"
            | eval store_name=case(
                match(url, "clients2\.googleusercontent\.com"), "Chrome",
                match(url, "edgedl\.me\.gvt1\.com"), "Edge"
            )
            | where isnotnull(store_name)
            | dedup crxID
            | rename crxID as ext_id
            | table ext_id, user, src, store_name
            '''
            job = self.service.jobs.create(query, exec_mode="normal")
            while not job.is_done():
                time.sleep(2)

            extensions = []
            for result in JSONResultsReader(job.results(output_mode='json')):
                if isinstance(result, dict) and result.get("ext_id"):
                    extensions.append({
                        "ext_id": result["ext_id"],
                        "store_name": result.get("store_name", "unknown"),
                        "user": result.get("user", "unknown")
                    })
            logger.info(f"Found {len(extensions)} extensions")
            return extensions

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []

    def analyze_extension(self, ext_id, store_name):
        """Analyze extension using BrowserExt API."""
        if not self.api_key:
            logger.error("API key missing")
            return None

        headers = {"X-API-Key": self.api_key}
        payload = {"extension_id": ext_id, "store_name": store_name.lower()}

        try:
            response = self.session.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API error for {ext_id}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.debug(f"API response: {e.response.text[:500]}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON for {ext_id}")
        return None

    def output_to_splunk(self, data):
        """Output with explicit Splunk metadata."""
        if data:
            event = {
                "time": data.get("_time", time.time()),
                "host": self.hostname,
                "sourcetype": "browserext",
                "index": "main",
                "event": {
                    **data,
                    "splunk_ingest_time": datetime.now().isoformat()
                }
            }
            print(json.dumps(event))
            self.event_count += 1

    def run(self):
        """Main execution with parallel processing."""
        if not self.api_key:
            logger.error("API key not configured. Exiting.")
            sys.exit(1)

        extensions = self.fetch_extension_ids()
        if not extensions:
            logger.info("No extensions found")
            return

        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = {
                executor.submit(
                    self.analyze_extension,
                    ext["ext_id"],
                    ext["store_name"]
                ): ext for ext in extensions
                if not self.has_been_processed(ext["ext_id"])
            }

            for future in as_completed(futures):
                ext_info = futures[future]
                try:
                    data = future.result()
                    if data:
                        final_data = {**data, **ext_info}
                        self.output_to_splunk(final_data)
                        self.update_processed(ext_info["ext_id"])
                    else:
                        self.error_count += 1
                except Exception as e:
                    logger.error(f"Processing error: {str(e)}")
                    self.error_count += 1

        logger.info(
            f"Completed: {self.event_count} processed, {self.error_count} errors"
        )

if __name__ == "__main__":
    retriever = BrowserExtRetriever()
    retriever.run()

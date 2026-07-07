import requests
import json
import re
import logging
import os
from configparser import ConfigParser

# Configure logging
log_dir = os.path.join(os.environ.get("SPLUNK_HOME", "."), "var", "log", "splunk")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "wmi_splunk_app.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,  # Use DEBUG for detailed logging
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def get_custom_config():
    """
    Retrieve the custom configuration from default and local matrics.conf files.
    """
    splunk_home = os.environ.get("SPLUNK_HOME")
    app_name = "wmi_splunk_app"  # Replace with your app's actual name if different
    if not splunk_home:
        logging.error("SPLUNK_HOME environment variable is not set.")
        return None

    default_config = os.path.join(splunk_home, "etc", "apps", app_name, "default", "matrics.conf")
    local_config = os.path.join(splunk_home, "etc", "apps", app_name, "local", "matrics.conf")

    config = ConfigParser()
    files_read = config.read([default_config, local_config])
    logging.info(f"Configuration files read: {files_read}")

    if not files_read:
        logging.error("No custom configuration files found.")
        return None

    return config

def fetch_metrics_config():
    """
    Retrieve metrics_urls and metrics_keywords from matrics.conf.
    """
    config = get_custom_config()
    if not config:
        return [], []

    try:
        # Note: Using 'metrics_url' to match the query, though 'metrics_urls' could support multiple
        metrics_urls_str = config.get("metrics_settings", "metrics_url", fallback="")
        metrics_urls = [url.strip() for url in metrics_urls_str.split(",") if url.strip()]
        metrics_keywords_str = config.get("metrics_settings", "metrics_keywords", fallback="")
        keywords = [kw.strip() for kw in metrics_keywords_str.split(",") if kw.strip()]
        return metrics_urls, keywords
    except Exception as e:
        logging.error(f"Error reading metrics configuration: {e}")
        return [], []

def fetch_metrics(url, keywords=None):
    # Note: Allowing HTTP URLs for local endpoints. For production, consider enforcing HTTPS.
    try:
        logging.info(f"Fetching metrics from URL: {url} with keywords: {keywords}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        metrics_data = response.text

        logging.debug(f"Raw metrics data fetched: {metrics_data[:500]}")
        return filter_metrics_by_keywords(metrics_data, keywords) if keywords else metrics_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {url}: {e}")
        return None

def filter_metrics_by_keywords(data, keywords):
    """
    Filters the raw metrics data for lines matching specific keyword metric names.
    """
    filtered_metrics = {}
    lines = data.splitlines()

    pattern = re.compile(r'(\w+)(\{.*?\})?\s+([\d.e+-]+)')  # Regex for Prometheus-style metrics
    for line in lines:
        match = pattern.match(line)
        if match:
            key = match.group(1)  # Metric name
            labels = match.group(2) or ""  # Optional labels
            value = match.group(3)

            full_key = key + labels
            if key in keywords:  # Exact match on metric name
                try:
                    filtered_metrics[full_key] = float(value)
                except ValueError:
                    filtered_metrics[full_key] = value  # Leave as string if conversion fails

    logging.debug(f"Filtered metrics: {filtered_metrics}")
    return filtered_metrics

def parse_metrics(data):
    """
    Parses raw metrics data into a dictionary of metric names and values.
    """
    parsed_metrics = {}
    lines = data.splitlines()

    for line in lines:
        if line.startswith("#") or not line.strip():  # Skip comments and blank lines
            continue

        parts = line.split(" ", 1)
        if len(parts) == 2:
            metric_name, metric_value = parts
            try:
                metric_value = float(metric_value)
            except ValueError:
                pass  # Leave as string if conversion fails
            parsed_metrics[metric_name] = metric_value

    logging.debug(f"Parsed metrics: {parsed_metrics}")
    return parsed_metrics

def generate_splunk_query(keywords):
    """
    Generates a Splunk query based on the provided keywords.
    """
    query_parts = [f'"{keyword}"' for keyword in keywords]
    return f'index="main" sourcetype="json" ({ " OR ".join(query_parts) })'

if __name__ == "__main__":
    # Fetch metrics URLs and keywords from matrics.conf
    metrics_urls, keywords = fetch_metrics_config()
    if not metrics_urls:
        logging.error("Metrics URLs not found. Exiting.")
        exit()
    if not keywords:
        logging.error("No keywords found. Exiting.")
        exit()

    # Check if all metrics_urls are HTTPS
    invalid_urls = [url for url in metrics_urls if urlparse(url).scheme != "https"]
    if invalid_urls:
        raise ValueError("The following URLs must be HTTPS: " + ", ".join(invalid_urls))

    for metrics_url in metrics_urls:
        raw_data = fetch_metrics(metrics_url, keywords=keywords)
        if raw_data:
            parsed_metrics = parse_metrics(raw_data) if isinstance(raw_data, str) else raw_data
            metrics_json = json.dumps(parsed_metrics, indent=4)
            logging.info("Filtered metrics by keywords:\n" + metrics_json)
            print(metrics_json)

            splunk_query = generate_splunk_query(keywords)
            logging.info(f"Generated Splunk Query: {splunk_query}")
            print(splunk_query)
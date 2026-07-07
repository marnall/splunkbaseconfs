"""
AppDynamics helpers: URL/controller and metric data shaping.
No Splunk/solnlib imports so they can be unit tested without a Splunk environment.
"""
from urllib.parse import urlparse


# --- URL / controller ---


def normalize_controller_url(controller_url):
    """Strip trailing slash from controller URL if present."""
    if controller_url and controller_url.endswith("/"):
        return controller_url[:-1]
    return controller_url


def get_account_name_from_controller_url(controller_url):
    """
    Derive OAuth account name from controller URL.
    - SaaS: hostname first component (e.g. mytenant.saas.appdynamics.com -> mytenant).
    - On-prem: "customer1".
    """
    if not controller_url:
        return "customer1"
    url = normalize_controller_url(controller_url)
    if "saas.appdynamics.com" in url:
        return urlparse(url).netloc.split(".")[0]
    return "customer1"


# --- Metric entry expansion ---


def process_metric_entry(entry):
    """
    Expand a metric API entry: if it has 'metricValues', return one record per
    metric; otherwise return a single-element list. Empty metricValues is
    treated as "no expansion" (single row).
    """
    metrics = entry.get("metricValues", None)
    if not metrics:
        return [dict(entry)]

    result = []
    base = {k: v for k, v in entry.items() if k != "metricValues"}
    for metric in metrics:
        new_entry = dict(base)
        for k, v in metric.items():
            new_entry[k] = v
        result.append(new_entry)
    return result

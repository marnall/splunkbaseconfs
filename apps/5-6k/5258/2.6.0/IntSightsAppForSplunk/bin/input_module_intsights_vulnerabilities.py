
# encoding = utf-8
from vulnerabilities_collector import VulnerabilitiesCollector

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Implement your data collection logic here."""
    try:
        ingester = VulnerabilitiesCollector(helper, ew)
        ingester.collect_events()
    except Exception as e:
        helper.log_error(e)


# encoding = utf-8
from alerts_collector import AlertsCollector

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Implement your data collection logic here."""
    ingester = AlertsCollector(helper, ew)
    ingester.collect_events()

# encoding = utf-8

from inputs import collect_entries_from_endpoint
from services import RansomwareOperationsEndpoint


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    collect_entries_from_endpoint(helper, ew, RansomwareOperationsEndpoint)
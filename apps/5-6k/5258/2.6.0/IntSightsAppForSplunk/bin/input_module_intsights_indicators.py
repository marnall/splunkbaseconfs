
# encoding = utf-8
import time
from datetime import datetime, timedelta
from indicators_collector import IndicatorsCollector

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    start_date = definition.parameters.get('start_date')
    try:
        if start_date:
            stripped_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%f")
            if int((datetime.utcnow() - stripped_date).total_seconds()) < 0:
                raise ValueError("Provided Start Date is from future. Please provide valid Start Date.")
            elif ((stripped_date - (datetime.utcnow() - timedelta(days=180))).total_seconds()) < 0:
                raise ValueError("Provided Start Date is 6 month before. Please provide the Start Date within 6 months")
    except ValueError as ve:
        raise Exception(ve)
    except Exception:
        raise Exception("Please provide the Start Date in correct format")

def collect_events(helper, ew):
    """Implement your data collection logic here."""
    ingester = IndicatorsCollector(helper, ew)
    ingester.collect_events()
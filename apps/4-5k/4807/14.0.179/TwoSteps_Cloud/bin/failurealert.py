import splunk.mining.dcutils as dcu
import splunk.Intersplunk
import json
from splunklib.client import connect
from datetime import datetime
from enum import Enum

logger = dcu.getLogger()


class AlertKind(Enum):
    FAIL = "fail"
    WARN = "warn"


def get_failure_kind(failure):
    if int(failure['rc']) != 0:
        return "fail"
    if int(failure['pc']) != 0:
        return "warn"
    return "clear"

def get_failure_reason(failure):
    if "reason" in failure:
        return failure["reason"]
    return "None"

def bytime(r):
    return r['time']

def is_nominal(rrs):
    if not is_warning(rrs) and not is_failing(rrs):
        return True
    return False

def is_failing(rrs):
    """Is this test current failing, i.e. is RC non-zero for the most recent result"""
    if len(rrs) >= 1 and int(rrs[-1]['rc']) > 0:
        return True
    return False

def was_failing(rrs):
    """Was this test failing, i.e. is RC non-zero for the next most recent result"""
    if len(rrs) > 1 and int(rrs[-2]['rc']) > 0:
        return True
    return False

def is_warning(rrs):
    """Is this test currently warning, i.e. is PC non-zero for the most recent result"""
    try:
        if len(rrs) >= 1 and int(rrs[-1]['pc']) > 0:
            return True
    except Exception:
        logger.error("is_warning() assuming no due to missing pc condition code")
    return False

def was_warning(rrs):
    """Was this test warning, i.e. is PC non-zero for the next most recent result"""
    try:
        if len(rrs) > 1 and int(rrs[-2]['pc']) > 0:
            return True
    except Exception:
        logger.error("was_warning assuming no due to missing pc condition code")
    return False

def has_changed_to_fail(rrs):
    """Test if the most recent result is a failure but the previous result was not,
        i.e. we have entered the failing state"""

    # Splunk kindly sends everything through as strings.
    if not was_failing(rrs) and is_failing(rrs):
        return True

    return False

def has_changed_to_nominal(rrs):
    """Test whether the test has transitioned into a clear (of alerts and warnings) state."""

    # Clearly not nominal if the current rc/pc indicates a failure.
    if is_failing(rrs) or is_warning(rrs):
        return False;

    # Can't change back to nominal, if we weren't previously not nominal!
    if not was_warning(rrs) and not was_failing(rrs):
        return False

    return True

def has_changed_to_warn(rrs):
    """Test if the most recent result is a warning (performance deterioration) but the previous result was not,
        i.e. we have entered the warning state"""

    # failure trumps warning. If we are failing, we're not warning..
    if is_failing(rrs):
        return False

    if not was_warning(rrs) and is_warning(rrs):
        return True

    return False


def get_alert_type(fail):
    """If the failure record has a kind field, return that (fail/warn).
    If not, assume fail because that was the only original type"""
    if "kind" in fail:
        return fail['kind']

    return 'fail'

def set_alert(rr, eue, fail_time, fail_kind, alerts, failures):
    last_fail = None
    try:
        last_fail = alerts.data.query_by_id(eue)
    # seems exception catching is the only way to do this
    except Exception as ex:
        pass

    if last_fail is None:
        logger.info("failure not found in kvstore: alerting")
        alerts.data.insert(json.dumps({"_key": eue, "time": fail_time, "kind": fail_kind.value }))
        failures.append(rr)
    else:
        logger.info('last_fail=' + str(last_fail['time']))
        if last_fail['time'] == fail_time: # I don't think we need to check the type given the time is identical.
            logger.info("failure found in kvstore: not alerting")
        else: # This would include moving from fail->warn or warn->fail as time !=
            logger.info('time was different from kvstore: alerting')
            alerts.data.update(eue, json.dumps({"time": fail_time, "kind": fail_kind.value }))
            failures.append(rr)

    return (alerts, failures)

def clear_alert(rr, eue, alerts, failures):
    last_fail = None
    try:
        last_fail = alerts.data.query_by_id(eue)
    # seems exception catching is the only way to do this
    except Exception as ex:
        pass

    if last_fail is not None: # There is an outstanding alert (fail/warn) to clear
        logger.info(f"clearing alert for {eue}")
        alerts.data.delete_by_id(eue)
        failures.append(rr)
    else:
        logger.info(f"No outstanding alert to clear for {eue}")

    return (alerts, failures)


def main():
    logger.info('running failurealert')
    # we expect data to be an array of RunResults where job_retries==0
    # furthermore, we need to receive (at least) the most recent two results
    # so the time period for the alert search needs to be > the largest
    # schedule interval defined for any EUE
    data, dummy2, settings = splunk.Intersplunk.getOrganizedResults()
    token = settings.get("sessionKey")
    # we expect the data will already be sorted by time, but there's little harm
    # in making sure...
    data.sort(key=bytime)
    service = connect(host='localhost', port=8089, token=token, app="TwoSteps", owner="nobody")

    # we'll keep the time of the latest failure per EUE in the kvstore
    # so that alerts will not be repeated, even if the alerting script is
    # called more than once in the time window of the schedule
    if "eue_alerts" not in service.kvstore:
        logger.info('creating eue_alert collection')
        service.kvstore.create("eue_alerts")

    alerts = service.kvstore["eue_alerts"]
    # failures will be rows of *new* failures to report. No rows=no failures
    # first group the row by EUE...
    eues = {}
    failures = []
    for row in data:
        eue = row["EUE"]
        if eue in eues:
            eues[eue].append(row)
        else:
            eues[eue] = [row]

    for eue, rrs in eues.items():
        logger.info('eue: ' + eue + ', num results: ' + str(len(rrs)))

        # if the status of the run result changed from success to failure
        if has_changed_to_fail(rrs):
            logger.info('new failure found for ' + eue)
            fail_time = rrs[-1]['time']
            logger.info('fail_time=' + str(fail_time))

            (alerts, failures)  = set_alert( rrs[-1], eue, fail_time, AlertKind.FAIL, alerts, failures )
        elif has_changed_to_warn(rrs):
            logger.info("Changed to warn for " + eue)
            fail_time = rrs[-1]['time']
            (alerts, failures)  = set_alert( rrs[-1], eue, fail_time, AlertKind.WARN, alerts, failures )
        elif is_nominal(rrs): # Check whether we have an alert in the kv store, if so remove it and publish a recovery
            logger.info( eue + " is nominal, checking whether should clear")
            (alerts, failures) = clear_alert( rrs[-1], eue, alerts, failures )


    logger.info('found ' + str(len(failures)) + ' new EUE state changes')
    # transform to simple output
    results = [];
    for failure in failures:
        results.append({
            "test": failure["EUE"],
            "failed_at": datetime.fromtimestamp(int(failure["time"])).strftime("%Y/%m/%d, %H:%M:%S"),
            "reason": get_failure_reason(failure),
            "kind": get_failure_kind(failure),
        })
        logger.info(json.dumps(results))

    splunk.Intersplunk.outputResults(results)

if __name__=="__main__":
    main()

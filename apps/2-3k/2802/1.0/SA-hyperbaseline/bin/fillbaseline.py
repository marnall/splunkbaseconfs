#!/usr/bin/env python

import sys
import splunklib.client as client
import math
import functools
import json
import medcouple
import time

from xml.dom import minidom
from collections import OrderedDict
from splunklib.searchcommands import \
    dispatch, ReportingCommand, Configuration, Option, validators

def convertStr(s):
    """Convert string to either int or float."""
    try:
        ret = int(s)
    except ValueError:
        #Try float.
        try:
            ret = float(s)
        except ValueError:
            ret = None
    return ret

def mean(data):
    """Return the sample arithmetic mean of data."""
    n = len(data)
    if n < 1:
        raise ValueError('mean requires at least one data point')
    return sum(data)/float(n)

def _ss(data):
    """Return sum of square deviations of sequence data."""
    c = mean(data)
    ss = sum((x-c)**2 for x in data)
    return ss

def pstdev(data):
    """Calculates the population standard deviation."""
    n = len(data)
    if n < 2:
        return None # calculation of variance isn't possible with only 1 data point
    ss = _ss(data)
    pvar = ss/n # the population variance
    return pvar**0.5

def percentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1

# median is 50th percentile.
median = functools.partial(percentile, percent=0.5)

@Configuration(clear_required_fields=True, requires_preop=True)
class FillBaselineCommand(ReportingCommand):
    """ Computes basic statistics for a given timeseries generated with timechart command. Bare in mind to set the limit and useother options of the timechart command according to your needs.
    ##Syntax
    .. code-block::
        fillbaseline config_name=<string> variable=<fieldname> [kv_store=<string>] <field-list>
    ##Description:
        Calculate basic statistics mad, max, mean, medcouple, median, min, pct25, pct75 and stdev aggregated by the field provided as variable parameter. \
        The calculated statistics are stored in a collection (default collection = hyperbaseline) and will be used by the comparetobaseline command for scoring. \
        Statistics are only calculated for numerical fields provided by field-list.
    ##Example
    ..code-block::
        index=_internal sourcetype=splunkd_ui_access| bucket span=1d _time
            | stats avg(date_hour) as avg_hour min(date_hour) as min_hour max(date_hour) as max_hour by user _time
            | fillbaseline config_name="ui_usage" value=user avg_hour min_hour max_hour
    """
    config_name = Option(
        doc='''
        **Syntax:** **config_name=***<string>*
        **Description:** Name to be referenced for storing the basic statistics in the kvstore''',
        require=True)

    value = Option(
        doc='''
        **Syntax:** **value=***<fieldname>*
        **Description:** value/column used to aggregate by and calculate the statistical metrics''',
        require=True, validate=validators.Fieldname())

    kv_store = Option(
        doc='''
        **Syntax:** **value=***<string>*
        **Description:** name of the collection the statistics will be stored in''',
        require=False, default="hyperbaseline")

    collections_data_endpoint = 'storage/collections/data/'

    def reduce(self, records):
        xml_doc = minidom.parseString(self.input_header["authString"])
        user_id = xml_doc.getElementsByTagName('userId')[0].firstChild.nodeValue
        dict = {}
        for record in records:
            if not record[self.value] in dict:
                dict[record[self.value]] = {}
            for fieldname in self.fieldnames:
                value = convertStr(record[fieldname])
                if value is None:
                    continue # skip none nummeric values
                try:
                    new_data = dict[record[self.value]][fieldname]
                except KeyError:
                    new_data = []
                new_data.append(value)
                dict[record[self.value]][fieldname] = new_data

        output_array = []
        for key, value in dict.iteritems():
            for k, v in value.iteritems():
                sorted_data = sorted(v)
                current_payload = OrderedDict()
                current_payload["_key"] = self.config_name + "#" + key + "#" + k
                current_payload["config_name"] = self.config_name
                current_payload["value"] =  key
                current_payload["field"] = k
                current_payload["min"] = min(sorted_data)
                current_payload["pct25"] = percentile(sorted_data,percent=0.25)
                current_payload["mean"] = mean(sorted_data)
                current_payload["median"] = median(sorted_data)
                current_payload["pct75"] = percentile(sorted_data,percent=0.75)
                current_payload["max"] = max(sorted_data)
                current_payload["stdev"] = pstdev(sorted_data)
                current_payload["mad"] = median(sorted([abs(x - current_payload["median"]) for x in sorted_data]))
                current_payload["medcouple"] = medcouple.medcouple_1d(sorted_data)
                current_payload["owner"] = user_id
                current_payload["_time"] = int(time.time())
                output_array.append(current_payload)
                yield current_payload

        # check if the output_array actually contains elements before pushing it into the KV store
        if output_array:
            app_service = client.Service(token=self.input_header["sessionKey"])
            request2 = app_service.request(
                self.collections_data_endpoint + self.kv_store + "/batch_save",
                method = 'post',
                headers = [('content-type', 'application/json')],
                body = json.dumps(output_array),
                owner = 'nobody',
                app = 'SA-hyperbaseline'
            )

dispatch(FillBaselineCommand, sys.argv, sys.stdin, sys.stdout, __name__)

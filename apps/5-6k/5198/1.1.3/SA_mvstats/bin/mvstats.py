# mvstats.py

# Perform calculations on a multi-value field.
# Usage:
#   | mvstats function response_time as total_response_time 
#   where "response_time" is a multi-valued numeric field.

# FUTURE FUNCTIONS: percentile [use statistics.py (Python3 only)]
# https://www.geeksforgeeks.org/python-statistics-stdev/
# import statistics

# # creating a simple data - set
# sample = [1, 2, 3, 4, 5]

# https://stackabuse.com/calculating-variance-and-standard-deviation-in-python/
# def variance(data, ddof=0):
#     n = len(data)
#     mean = sum(data) / n
#     return sum((x - mean) ** 2 for x in data) / (n - ddof)

#  def stdev(data):
#     var = variance(data)
#     std_dev = math.sqrt(var)
#     return std_dev

from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
try:
    noStatsLib = 0
    import statistics
except ImportError:
    noStatsLib = 1

splunkhome = os.environ['SPLUNK_HOME']
app_name = __file__.split(os.sep)[-3]
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', app_name, 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib import six

SupportedFunctions = [
    "sum",
    "min",
    "max",
    "avg",
    "range",
    "stdev",
    "median",
    "mode"]

# Helper function to parse values in the <input-field> field
def getNum(value):
    if value == '' or value is None or value is "NULL":
        value = None
    else:
        try:
            value = float(value)
        except ValueError:
            pass
    return value

@Configuration()
class mvstatsCommand(StreamingCommand):
    """ Perform calculations on a multi-value field.

    ##Syntax

    .. code-block::
        mvstats <function> <mv-field> as <result-field>

        <function> is one of: "sum", "min", "max", "avg", "range", "stdev", "median", or "mode"

    ##Description:

    Performs calculations on the values in a multi-value field.

    ##Example:

    ..code-block::
        ... | stats values(dest_port) as dest_port, values(count) as count 
        | mvstats sum count as total

    """

    def stream(self, records):
        self.logger.debug('mvstatsCommand: %s', self)  # logs command line

        if (len(self.fieldnames) != 4) or (self.fieldnames[2].lower() != 'as'):
            raise Exception('Usage: mvstats <function> <mv-field> as <result-field>')

        if self.fieldnames[0] not in SupportedFunctions:
            raise Exception('Expecting one of %s' % str(SupportedFunctions))
        else:
            func = self.fieldnames[0]

        validField = validators.Fieldname()
        try:
            fieldname = validField(self.fieldnames[1])
        except ValueError as e:
            raise RuntimeWarning('%s is not a valid field name' % str(self.fieldnames[1]))
        try:
            result = validField(self.fieldnames[3])
        except ValueError as e:
            raise ValueError('%s is not a valid field name' % str(self.fieldnames[3]))

        for record in records:
            return_value = ''
            field_value = record[fieldname]
            if field_value:
                if isinstance(field_value, list):
                    nums = [getNum(x) for x in field_value]
                    try:
                        if func == "sum":
                            return_value = sum(nums)
                        elif func == "min":
                            return_value = min(nums)
                        elif func == "max":
                            return_value = max(nums)
                        elif func == "avg":
                            return_value = round((sum(nums)/len(nums)),3)
                        elif func == "range":
                            return_value = round((max(nums) - min(nums)),3)
                        elif func == "stdev":
                            if noStatsLib == 1:
                                raise Exception('%s is supported only in Python3' % func)
                            else:
                                return_value = statistics.stdev(nums)
                        elif func == "median":
                            if noStatsLib == 1:
                                raise Exception('%s is supported only in Python3' % func)
                            else:
                                return_value = statistics.median(nums)
                        elif func == "mode":
                            if noStatsLib == 1:
                                raise Exception('%s is supported only in Python3' % func)
                            else:
                                return_value = statistics.mode(nums)
                        else:
                            raise Exception('Unsupported function %s' % func)
                    except:
                        return_value = "NaN"
                else:
                    if func == "range":
                        return_value = 0
                    else:
                        return_value = field_value
            record[result] = return_value
            yield record

if __name__ == "__main__":
    dispatch(mvstatsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
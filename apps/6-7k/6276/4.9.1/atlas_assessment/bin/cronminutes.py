# This will convert the cron of a scheduled search into minutes between executions
import splunk.Intersplunk
from datetime import datetime
# Grab Vendor Path from lib directory
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from lib.croniter import croniter

# this is a placeholder for the real scripty scripty


def translateCron(iter):

    iter.get_next(datetime)
    first_next = iter.get_next(datetime)
    second_next = iter.get_next(datetime)
    difference1 = (second_next - first_next).total_seconds() / 60
    running_min = difference1
    running_max = difference1
    running_sum = 0
    running_range = 100
    for _ in range(running_range):
        first_next = second_next
        second_next = iter.get_next(datetime)
        nth_difference = (second_next - first_next).total_seconds() / 60
        if nth_difference < running_min:
            running_min = nth_difference
        elif nth_difference > running_max:
            running_max = nth_difference
        running_sum += nth_difference

    running_avg = running_sum / running_range

    return (running_min, running_max, running_avg, running_min == running_max == running_avg)

def run_command():
    try:
        _messages = {}
        _keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        results, dummyresults, _settings = splunk.Intersplunk.getOrganizedResults()

        cronMin = options.get('outputField', 'cronMin')
        cronMax = options.get('outputField', 'cronMax')
        cronAvg = options.get('outputField', 'cronAvg')
        cronBool = options.get('outputField', 'cronBool')

        cronField = options.get('field', None)

        if not cronField:
            return splunk.Intersplunk.generateErrorResults("Calculation not performed; no cron expression field provided.")

        if results:
            for result in results:
                if cronField not in result:
                    continue

                cronValue = result[cronField]

                # validate syntax
                try:
                    base = datetime.now()
                    iter = croniter(cronValue, base) 
                except:
                    continue

                # translate (CHANGE 'translateCron' to name of my function)
                (result[cronMin], result[cronMax], result[cronAvg],
                result[cronBool]) = translateCron(iter)

            splunk.Intersplunk.outputResults(results)

    except Exception as e:
        import traceback
        stack = traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))


run_command()

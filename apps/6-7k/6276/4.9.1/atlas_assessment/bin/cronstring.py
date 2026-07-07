# A Splunk command for translating a cron expression into English.

import os, re, splunk.Intersplunk, logging as logger


CRON_REGEX = r"^((0*([0-9]|[1-5][0-9])|\*)(-0*([0-9]|[1-5][0-9]))?(\/\d+)?,)*(0*([0-9]|[1-5][0-9])|\*)(-0*([0-9]|[1-5][0-9]))?(\/\d+)?\s((0*([0-9]|1[0-9]|2[0-3])|\*)(-0*([0-9]|1[0-9]|2[0-3]))?(\/\d+)?,)*(0*([0-9]|1[0-9]|2[0-3])|\*)(-0*([0-9]|1[0-9]|2[0-3]))?(\/\d+)?\s((0*([1-9]|[1-2][0-9]|3[0-1])|\*)(-0*([1-9]|[1-2][0-9]|3[0-1]))?(\/\d+)?,)*(0*([1-9]|[1-2][0-9]|3[0-1])|\*)(-0*([1-9]|[1-2][0-9]|3[0-1]))?(\/\d+)?\s((0*([1-9]|1[0-2])|\*)(-0*([1-9]|1[0-2]))?(\/\d+)?,)*(0*([1-9]|1[0-2])|\*)(-0*([1-9]|1[0-2]))?(\/\d+)?\s((0*[0-7]|\*)(-0*[0-7])?(\/\d+)?,)*(0*[0-7]|\*)(-0*[0-7])?(\/\d+)?$"
MONTHS = ["","January","February","March","April","May","June","July","August","September","October","November","December"]
WEEKDAYS = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

def numSfx(number):
    if not number: return None
    number = str(number)
    end = number[-2:]
    if end=="11" or end=="12":
        return "%sth" % number
    end = number[-1]
    if end=="1":
        return "%sst" % number
    if end=="2":
        return "%snd" % number
    if end=="3":
        return "%srd" % number
    return "%sth" % number


def translateCronClause(clause, last, unit="", maxval=59, maparr=None):
    # Clauses are comma-delimited
    match = re.search(r"^(?:(\*)|(\d+)|(?:(\d+)\-(\d*)))(?:\/(\d+))?$", clause)
    if not match:
        return False

    # [*, single, range start, range end, step value, max range value]
    groups = list(match.groups())
    groups.append(maxval)
    raw_groups = groups

    if len(unit)>0:
        unit = " " + unit
        if unit==" day": groups = list(map(numSfx, raw_groups))
    if not groups[0] and maparr:
        groups = [maparr[int(x)] if x is not None else None for x in raw_groups]

    string=""
    end=""
    if groups[3] or groups[4]:
        string = " every"
        if groups[4] and raw_groups[4]!="1": string += " %s" % numSfx(raw_groups[4])
        string += unit
        if not groups[0]:
            string += " from"
            if unit==" day": string += " the"
            if groups[3]: string += " %s through %s" % (groups[2], groups[3])
            else: string += " %s through %s" % (groups[1], groups[5])
            if not last: end=","
    elif groups[1]:
        if unit==" weekday": string = " %ss" % groups[1]
        elif unit==" month": string = " of %s" % groups[1]
        elif unit==" day": string = " the %s" % groups[1]
        else: string = "%s %s" % (unit, groups[1])
    elif groups[0] and (unit==" minute" or unit==" month"):
        string = " every%s" % unit

    return string+end


def translateCronSegment(segment, unit="", maxval=59, maparr=None):
    # Segments are space-delimited
    split = segment.split(",")
    clauses =  []
    for i in range(len(split)):
        last = len(split)==(i+1)
        clause = translateCronClause(split[i], last, unit, maxval, maparr)
        if clause: clauses.append(clause)

    return clauses


def translateCron(segments):
    translation = "At"
    if segments[0].isdigit() and segments[1].isdigit():
        translation += " %s:%s%s" % (segments[1], "0" if len(segments[0])<2 else "", segments[0])
    else:
        translation += "%s" % " and".join(translateCronSegment(segments[0], "minute", 59))
        if segments[1]!="*": translation += " past%s" % " and".join(translateCronSegment(segments[1], "hour", 23))
    if segments[2]!="*": translation += ", on%s" % " and".join(translateCronSegment(segments[2], "day", 31))
    if segments[4]!="*": translation += " %son%s" % ("and " if segments[2]!="*" else "", " and".join(translateCronSegment(segments[4], "weekday", 6, WEEKDAYS)))
    if segments[3]!="*" and segments[2]=="*": translation += ", during%s" % " and".join(translateCronSegment(segments[3], "month", 12, MONTHS))
    elif segments[2]!="*": translation += " of%s" % " and".join(translateCronSegment(segments[3], "month", 12, MONTHS))
    translation += "."

    return translation


def run_command():
    try:
        _messages = {}
        _keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        results, dummyresults, _settings = splunk.Intersplunk.getOrganizedResults()

        outputField = options.get('outputField', 'cronstring')
        cronField = options.get('field', None)

        if not cronField:
            return splunk.Intersplunk.generateErrorResults("Calculation not performed; no cron expression field provided.")

        if results:
            for result in results:
                if cronField not in result:
                    continue

                cronValue = result[cronField]
                
                # validate syntax with regex
                match = re.search(CRON_REGEX, cronValue)
                if not match:
                    continue

                # split into segments
                segments = cronValue.split(" ")

                # translate
                result[outputField] = translateCron(segments)

            splunk.Intersplunk.outputResults(results)

    except Exception as e:
        import traceback
        stack =  traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))
        logger.error(str(e) + ". Traceback: " + str(stack))


run_command()
